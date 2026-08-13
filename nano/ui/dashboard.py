"""Panel de control en consola, construido con rich.

Distribucion (de arriba abajo):

    cabecera   archivo seguido, bot, HU actual, duracion, ritmo
    stream     las ultimas lineas del log, una por fila
    paneles    RESUMEN (contadores) | ULTIMOS ERRORES | ULTIMOS WARNING
    top        ranking de errores repetidos
    barra      teclas disponibles y estado de la sesion

El objetivo del panel es que un ERROR no se pierda al desplazarse la
pantalla: queda contado en el resumen, guardado en su panel y agrupado en
el ranking.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import ContextManager

from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from nano import config
from nano.core.estado import EstadoSesion, Entrada
from nano.core.modelo import LogRecord
from nano.core.seguidor import Seguidor
from nano.opciones import Opciones
from nano.ui.base import VisorBase
from nano.ui.temas import BLANCO_HEX, Tema

#: Simbolos con alternativa ASCII para consolas que no dibujan Unicode.
SIMBOLOS = {
    False: {"sep": "·", "flecha": "▸", "punto": "●", "vacio": "—", "veces": "×",
            "arriba": "↑", "abajo": "↓"},
    True: {"sep": "-", "flecha": ">", "punto": "*", "vacio": "-", "veces": "x",
           "arriba": "^", "abajo": "v"},
}

#: Anchos fijos de las columnas del stream.
ANCHO_HORA = 8
ANCHO_NIVEL = 7
ANCHO_ORIGEN = 20


@dataclass(frozen=True)
class Aviso:
    """Mensaje del propio visor intercalado en el stream (no viene del log)."""

    texto: str


class VisorDashboard(VisorBase):
    """Dibuja el panel de control y lo refresca en vivo."""

    def __init__(self, seguidor: Seguidor, estado: EstadoSesion,
                 tema: Tema, opciones: Opciones) -> None:
        super().__init__(seguidor, estado, tema, opciones)
        self.console = Console()
        self.filas: deque = deque(maxlen=config.BUFFER_STREAM)
        self._live: Live | None = None
        #: Lineas que el usuario ha subido desde el final. 0 = pegado al vivo.
        self.desplazamiento = 0

        modo_ascii = opciones.ascii or self.console.legacy_windows
        self.simbolos = SIMBOLOS[bool(modo_ascii)]
        self.caja = box.ASCII if modo_ascii else box.ROUNDED

    # --- integracion con el bucle base ---------------------------------------

    def _contexto(self) -> ContextManager:
        # auto_refresh=False: el panel se redibuja desde el bucle principal y
        # no desde un hilo de fondo de rich. Asi el dibujado no compite con
        # nada mas por la consola, que es lo que hacia aparecer el cursor
        # moviendose por la pantalla entre redibujados.
        self._live = Live(
            self._render(),
            console=self.console,
            auto_refresh=False,
            screen=True,
            transient=False,
        )
        return self._live

    def _al_iniciar(self) -> None:
        # rich ya lo hace al abrir el Live, pero se repite aqui para las
        # consolas donde esa primera secuencia se pierde y el cursor se queda
        # parpadeando encima del panel.
        self.console.show_cursor(False)

    def _al_terminar(self) -> None:
        self.console.show_cursor(True)

    def _refrescar(self) -> None:
        if self._live is not None:
            self._live.update(self._render(), refresh=True)

    def _mostrar(self, rec: LogRecord) -> None:
        self.filas.append(rec)
        # Si el usuario esta mirando hacia atras, la vista no debe saltar:
        # cada linea nueva empuja el final, asi que se compensa el desfase.
        if self.desplazamiento:
            self._desplazar(1)

    # --- navegacion por el historial -----------------------------------------

    def _tecla_extra(self, tecla: str) -> None:
        salto = max(1, self._alto_stream() - 1)
        if tecla == "arriba":
            self._desplazar(1)
        elif tecla == "abajo":
            self._desplazar(-1)
        elif tecla == "repag":
            self._desplazar(salto)
        elif tecla == "avpag":
            self._desplazar(-salto)
        elif tecla == "inicio":
            self._desplazar(len(self.filas))
        elif tecla == "fin":
            self.desplazamiento = 0
        else:
            return
        self._refrescar()

    def _desplazar(self, lineas: int) -> None:
        """Mueve la vista dentro del buffer, sin salirse de sus limites."""
        tope = max(0, len(self.filas) - self._alto_stream())
        self.desplazamiento = max(0, min(tope, self.desplazamiento + lineas))

    @property
    def en_historial(self) -> bool:
        """True si la vista esta detenida mas arriba del final del log."""
        return self.desplazamiento > 0

    def _aviso_archivo(self) -> None:
        self._avisar(f"Siguiendo: {self.seguidor.nombre_archivo} "
                     f"[{self.seguidor.encoding}]")

    def _aviso_rotacion(self) -> None:
        self._avisar("Archivo rotado: releyendo desde el inicio")

    def _aviso_pausa(self) -> None:
        self._avisar("PAUSADO" if self.pausado else "REANUDADO")

    def _aviso_limpieza(self) -> None:
        self._avisar("Contadores reiniciados")

    def _avisar(self, texto: str) -> None:
        self.filas.append(Aviso(texto))
        self._refrescar()

    # --- composicion del layout ----------------------------------------------

    def _render(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(self._cabecera(), name="cabecera", size=config.ALTO_CABECERA),
            Layout(self._stream(), name="stream", ratio=1),
            Layout(name="paneles", size=config.ALTO_PANELES),
            Layout(self._panel_top(), name="top", size=config.ALTO_TOP),
            Layout(self._barra(), name="barra", size=config.ALTO_BARRA),
        )
        columnas = [
            Layout(self._panel_resumen(), name="resumen",
                   size=config.ANCHO_RESUMEN),
            Layout(self._panel_historial("ULTIMOS ERRORES",
                                         self.estado.ultimos_errores, "ERROR"),
                   name="errores", ratio=1),
        ]
        if self.opciones.panel_warning:
            columnas.append(
                Layout(self._panel_historial("ULTIMOS WARNING",
                                             self.estado.ultimos_warnings,
                                             "WARNING"),
                       name="warnings", ratio=1)
            )
        layout["paneles"].split_row(*columnas)
        return layout

    # --- cabecera ------------------------------------------------------------

    def _cabecera(self) -> Panel:
        sep, flecha = self.simbolos["sep"], self.simbolos["flecha"]
        estado, tema = self.estado, self.tema

        rejilla = Table.grid(expand=True)
        rejilla.add_column(justify="left", ratio=1, no_wrap=True,
                           overflow="ellipsis")
        rejilla.add_column(justify="right", no_wrap=True)

        archivo = Text(self.seguidor.nombre_archivo or "esperando archivo...",
                       style=f"bold {BLANCO_HEX}")
        archivo.append(f"  {sep}  {self.seguidor.encoding}",
                       style=tema.estilo_fecha)
        bot = Text("BOT ", style=tema.estilo_fecha)
        bot.append(estado.bot_actual or "-", style=f"bold {tema.estilo_acento}")
        rejilla.add_row(archivo, bot)

        origen = Text("HU  ", style=tema.estilo_fecha)
        origen.append(_ultimo_segmento(estado.origen_actual) or "-",
                      style=tema.estilo("INFO"))

        marcadores = Text()
        marcadores.append(estado.duracion(), style=f"bold {BLANCO_HEX}")
        marcadores.append(f"  {flecha} {estado.ritmo():.1f} l/s",
                          style=tema.estilo_fecha)
        ultima = estado.ultima_ts.strftime("%H:%M:%S") if estado.ultima_ts else "--:--:--"
        marcadores.append(f"  {sep}  ult {ultima}", style=tema.estilo_fecha)
        rejilla.add_row(origen, marcadores)

        return Panel(rejilla, box=self.caja, title="[b]NANO[/b]",
                     title_align="left", border_style=tema.estilo_acento,
                     padding=(0, 1))

    # --- stream --------------------------------------------------------------

    def _stream(self) -> Panel:
        tabla = Table.grid(expand=True, padding=(0, 1))
        tabla.add_column(width=ANCHO_HORA, no_wrap=True)                # hora
        tabla.add_column(width=ANCHO_NIVEL, no_wrap=True)               # nivel
        tabla.add_column(ratio=1, no_wrap=True, overflow="ellipsis")    # mensaje
        tabla.add_column(width=ANCHO_ORIGEN, no_wrap=True,
                         overflow="ellipsis", justify="right")          # origen

        for fila in self._filas_visibles():
            if isinstance(fila, Aviso):
                tabla.add_row(
                    Text(self.simbolos["flecha"] * 2, style=self.tema.estilo_acento),
                    "",
                    Text(fila.texto, style=f"italic {self.tema.estilo_acento}"),
                    "",
                )
                continue
            tabla.add_row(*self._celdas(fila))

        if not self.en_historial:
            return Panel(tabla, box=self.caja,
                         border_style=self.tema.estilo_fecha, padding=(0, 1))

        titulo = (f"HISTORIAL  {self.simbolos['arriba']} {self.desplazamiento} "
                  f"lineas atras  {self.simbolos['sep']}  [Fin] volver al vivo")
        return Panel(tabla, box=self.caja, title=titulo, title_align="left",
                     border_style=self.tema.estilo_acento, padding=(0, 1))

    def _celdas(self, rec: LogRecord) -> tuple:
        tema = self.tema
        hora = rec.ts.strftime("%H:%M:%S") if rec.ts else ""
        nivel = rec.nivel or ""
        return (
            Text(hora, style=tema.estilo_fecha),
            Text(nivel, style=f"bold {tema.estilo_fuerte(rec.nivel)}"),
            Text(rec.mensaje or rec.crudo, style=BLANCO_HEX),
            Text(rec.origen_corto, style=tema.estilo(rec.nivel)),
        )

    def _alto_stream(self) -> int:
        """Cuantas lineas de log caben en la zona de stream."""
        fijo = (config.ALTO_CABECERA + config.ALTO_PANELES
                + config.ALTO_TOP + config.ALTO_BARRA)
        disponible = self.console.size.height - fijo - 2  # 2 = bordes del panel
        return max(config.MIN_ALTO_STREAM, disponible)

    def _filas_visibles(self) -> list:
        """Ventana de filas a mostrar, segun el desplazamiento actual."""
        cuantas = self._alto_stream()
        fin = len(self.filas) - self.desplazamiento
        inicio = max(0, fin - cuantas)
        return list(self.filas)[inicio:fin]

    # --- paneles inferiores --------------------------------------------------

    def _panel_resumen(self) -> Panel:
        estado, tema = self.estado, self.tema
        rejilla = Table.grid(expand=True)
        rejilla.add_column(justify="left", no_wrap=True)
        rejilla.add_column(justify="right", no_wrap=True)

        for nivel in config.NIVELES:
            cantidad = estado.contadores[nivel]
            destacar = "bold " if cantidad and nivel in ("ERROR", "WARNING") else ""
            rejilla.add_row(
                Text(nivel, style=f"{destacar}{tema.estilo_fuerte(nivel)}"),
                Text(f"{cantidad}", style=f"{destacar}{tema.estilo(nivel)}"),
            )
        if estado.sin_nivel:
            rejilla.add_row(Text("otras", style=tema.estilo_fecha),
                            Text(f"{estado.sin_nivel}", style=tema.estilo_fecha))
        rejilla.add_row("", "")
        rejilla.add_row(Text("total", style=tema.estilo_fecha),
                        Text(f"{estado.total}", style=f"bold {BLANCO_HEX}"))

        # El borde se tine del color de ERROR en cuanto hay alguno: es la
        # senal de alarma que se ve sin leer los numeros.
        borde = tema.estilo("ERROR") if estado.errores else tema.estilo_acento
        return Panel(rejilla, box=self.caja, title="RESUMEN", title_align="left",
                     border_style=borde, padding=(0, 1))

    def _panel_historial(self, titulo: str, entradas, nivel: str) -> Panel:
        tema = self.tema
        rejilla = Table.grid(expand=True, padding=(0, 1))
        rejilla.add_column(width=ANCHO_HORA, no_wrap=True)
        rejilla.add_column(ratio=1, no_wrap=True, overflow="ellipsis")

        recientes = list(entradas)[-self._alto_historial():]
        if not recientes:
            rejilla.add_row("", Text(f"{self.simbolos['vacio']} sin registros",
                                     style=tema.estilo_fecha))
        for entrada in reversed(recientes):  # el mas reciente arriba
            rejilla.add_row(
                Text(entrada.hora, style=tema.estilo(nivel)),
                self._texto_entrada(entrada),
            )

        return Panel(rejilla, box=self.caja, title=titulo, title_align="left",
                     border_style=tema.estilo(nivel), padding=(0, 1))

    def _texto_entrada(self, entrada: Entrada) -> Text:
        texto = Text(entrada.mensaje, style=BLANCO_HEX, no_wrap=True,
                     overflow="ellipsis")
        if entrada.origen:
            texto.append(f"  {self.simbolos['sep']} {entrada.origen}",
                         style=self.tema.estilo_fecha)
        return texto

    @staticmethod
    def _alto_historial() -> int:
        return max(1, config.ALTO_PANELES - 2)  # descontando los bordes

    def _panel_top(self) -> Panel:
        tema = self.tema
        top = self.estado.top(config.TOP_ERRORES)
        texto = Text(no_wrap=True, overflow="ellipsis")
        if not top:
            texto.append(f"{self.simbolos['vacio']} sin errores repetidos",
                         style=tema.estilo_fecha)
        for i, (mensaje, veces) in enumerate(top):
            if i:
                texto.append(f"   {self.simbolos['sep']}   ",
                             style=tema.estilo_fecha)
            texto.append(f"{self.simbolos['veces']}{veces} ",
                         style=f"bold {tema.estilo_fuerte('ERROR')}")
            texto.append(mensaje, style=BLANCO_HEX)

        return Panel(texto, box=self.caja, title="TOP ERRORES", title_align="left",
                     border_style=tema.estilo("ERROR"), padding=(0, 1))

    # --- barra de estado -----------------------------------------------------

    def _barra(self) -> Table:
        tema = self.tema
        rejilla = Table.grid(expand=True, padding=(0, 1))
        rejilla.add_column(justify="left", no_wrap=True)
        rejilla.add_column(justify="right", no_wrap=True)

        teclas = Text(no_wrap=True, overflow="ellipsis")
        for tecla, accion in (("p", "pausa"), ("c", "limpiar"), ("q", "salir")):
            teclas.append(f" {tecla} ", style=f"reverse {tema.estilo_acento}")
            teclas.append(f" {accion}   ", style=tema.estilo_fecha)
        teclas.append(f"  {self.simbolos['arriba']}{self.simbolos['abajo']} "
                      "RePag AvPag Inicio Fin ", style=tema.estilo_acento)
        teclas.append("historial", style=tema.estilo_fecha)

        rejilla.add_row(teclas, self._estado_sesion())
        return rejilla

    def _estado_sesion(self) -> Text:
        punto = self.simbolos["punto"]
        if self.en_historial:
            return Text(f"HISTORIAL {self.simbolos['arriba']}{self.desplazamiento} "
                        f"{punto}", style=f"bold {self.tema.estilo_acento}")
        if self.pausado:
            return Text(f"PAUSADO {punto}",
                        style=f"bold {self.tema.estilo_fuerte('WARNING')}")
        if self.estado.inactivo():
            minutos = int(self.estado.segundos_inactivo() // 60)
            return Text(f"SIN ACTIVIDAD hace {minutos} min {punto}",
                        style=f"bold {self.tema.estilo_fuerte('ERROR')}")
        return Text(f"EN VIVO {punto}",
                    style=f"bold {self.tema.estilo_fuerte('INFO')}")


def _ultimo_segmento(ruta: str | None) -> str:
    """Ultimo tramo de una ruta de bot, para la cabecera."""
    if not ruta:
        return ""
    return ruta.replace("/", "\\").rstrip("\\").rsplit("\\", 1)[-1]
