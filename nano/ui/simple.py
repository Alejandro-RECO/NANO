"""Modo simple: stream plano linea por linea, como en la primera version.

Es el modo que se usa cuando la salida no es una terminal (redirecciones,
tuberias, tareas programadas) y el que fuerza `--simple`.
"""

from __future__ import annotations

import os
from contextlib import nullcontext
from datetime import datetime
from typing import ContextManager

from nano.core.modelo import LogRecord
from nano.core.parser import FECHA_RE
from nano.ui.base import VisorBase
from nano.ui.teclado import Teclado
from nano.ui.temas import BLANCO, RESET, Tema


def formatear(rec: LogRecord, tema: Tema, con_hora: bool = False) -> str:
    """Colorea una linea por campos.

    Campos separados por '|':  fecha | NIVEL | mensaje | resto...
      - Fecha: color de fecha del tema.
      - NIVEL: color del nivel pero mas fuerte (misma gama, mas saturado).
      - Mensaje (3er campo): siempre blanco.
      - Resto de campos y separadores '|': color del nivel.
      - Lineas sin nivel reconocido: color de fecha.
    """
    col_nivel = tema.ansi(rec.nivel)
    col_fuerte = tema.ansi_fuerte(rec.nivel)
    col_fecha = tema.ansi_fecha

    prefijo = ""
    if con_hora:
        prefijo = f"{col_fecha}[{datetime.now().strftime('%H:%M:%S')}] "

    # Formato con campos separados por '|'.
    if len(rec.campos) > 1 and rec.nivel is not None:
        piezas = []
        for i, campo in enumerate(rec.campos):
            if i == 0:
                color = col_fecha          # fecha
            elif i == 1:
                color = col_fuerte         # nivel (mas fuerte)
            elif i == 2:
                color = BLANCO             # mensaje (siempre blanco)
            else:
                color = col_nivel          # resto
            piezas.append(color + campo)
        cuerpo = (col_nivel + "|").join(piezas)
        return prefijo + cuerpo + RESET

    # Formato simple (sin barras): fecha en su color, resto color del nivel.
    m_fecha = FECHA_RE.match(rec.crudo)
    if m_fecha:
        fecha = rec.crudo[: m_fecha.end()]
        resto = rec.crudo[m_fecha.end():]
        return prefijo + col_fecha + fecha + col_nivel + resto + RESET
    return prefijo + col_nivel + rec.crudo + RESET


class VisorSimple(VisorBase):
    """Imprime cada linea nueva coloreada, sin panel."""

    def _contexto(self) -> ContextManager:
        return nullcontext()

    def _al_iniciar(self) -> None:
        acento = self.tema.ansi_acento
        teclas = "  |  'p' pausar  |  'q' salir" if self._teclas_disponibles() else ""
        print(acento + "=" * 60)
        print(acento + "  NANO - Visor de logs en tiempo real")
        print(acento + f"  Carpeta vigilada: {os.path.abspath(self.opciones.carpeta)}")
        print(acento + "  Ctrl+C para salir" + teclas)
        print(acento + "=" * 60 + RESET)

    def _mostrar(self, rec: LogRecord) -> None:
        print(formatear(rec, self.tema, self.opciones.con_hora))

    def _aviso_archivo(self) -> None:
        nombre = self.seguidor.nombre_archivo
        print(f"{self.tema.ansi_acento}\n>> Siguiendo: {nombre} "
              f"[{self.seguidor.encoding}]\n{RESET}")

    def _aviso_rotacion(self) -> None:
        print(f"{self.tema.ansi_acento}-- Archivo rotado, releyendo desde el "
              f"inicio --{RESET}")

    def _aviso_pausa(self) -> None:
        estado = "PAUSADO" if self.pausado else "REANUDADO"
        print(f"{self.tema.ansi_acento}-- {estado} --{RESET}")

    def _aviso_limpieza(self) -> None:
        print(f"{self.tema.ansi_acento}-- Contadores reiniciados --{RESET}")

    @staticmethod
    def _teclas_disponibles() -> bool:
        return Teclado().disponible
