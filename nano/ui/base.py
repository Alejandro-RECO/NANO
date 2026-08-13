"""Bucle comun a los dos modos de visualizacion.

`VisorBase` se ocupa de lo que no depende de como se pinte: leer lineas,
aplicar el filtro, actualizar el estado, guardar la salida y atender las
teclas. Las subclases solo implementan el dibujado.
"""

from __future__ import annotations

import time
from contextlib import ExitStack
from typing import ContextManager

from nano import config
from nano.core.estado import EstadoSesion
from nano.core.modelo import LogRecord
from nano.core.parser import parsear_linea
from nano.core.seguidor import Seguidor
from nano.opciones import Opciones
from nano.ui.teclado import Teclado
from nano.ui.temas import Tema

#: Teclas reconocidas en ambos modos.
TECLA_SALIR = ("q",)
TECLA_PAUSA = ("p",)
TECLA_LIMPIAR = ("c",)


class VisorBase:
    """Esqueleto de un visor. No se instancia directamente."""

    def __init__(self, seguidor: Seguidor, estado: EstadoSesion,
                 tema: Tema, opciones: Opciones) -> None:
        self.seguidor = seguidor
        self.estado = estado
        self.tema = tema
        self.opciones = opciones
        self.pausado = False
        self._salida = None

    # --- ciclo de vida -------------------------------------------------------

    def ejecutar(self) -> None:
        """Bucle principal. Termina con Ctrl+C o con la tecla 'q'."""
        with ExitStack() as pila:
            if self.opciones.guardar:
                self._salida = pila.enter_context(
                    open(self.opciones.guardar, "a", encoding="utf-8")
                )
            teclado = pila.enter_context(Teclado())
            pila.enter_context(self._contexto())
            self._al_iniciar()
            try:
                self._bucle(teclado)
            except KeyboardInterrupt:
                pass
        self._al_terminar()

    def _bucle(self, teclado: Teclado) -> None:
        while True:
            if self._atender_tecla(teclado.leer()):
                return

            if not self.pausado:
                lineas = self.seguidor.leer_nuevas()
                if self.seguidor.hubo_cambio_de_archivo:
                    self._aviso_archivo()
                if self.seguidor.hubo_rotacion:
                    self._aviso_rotacion()
                for linea in lineas:
                    self._procesar(linea)
                if self._salida and lineas:
                    self._salida.flush()

            self._refrescar()
            time.sleep(config.POLL_SEG)

    def _atender_tecla(self, tecla: str | None) -> bool:
        """Aplica la tecla pulsada. Devuelve True si hay que salir."""
        if tecla is None:
            return False
        if tecla in TECLA_SALIR:
            return True
        if tecla in TECLA_PAUSA:
            self.pausado = not self.pausado
            self._aviso_pausa()
        elif tecla in TECLA_LIMPIAR:
            self.estado.limpiar()
            self._aviso_limpieza()
        return False

    def _procesar(self, linea: str) -> None:
        """Interpreta una linea, actualiza el estado y la muestra si pasa el filtro.

        El filtro solo afecta a lo que se ve: los contadores y los paneles
        siempre reflejan el log completo.
        """
        rec = parsear_linea(linea)
        self.estado.registrar(rec)
        if not self._pasa_filtro(rec):
            return
        self._mostrar(rec)
        if self._salida:
            self._salida.write(linea if linea.endswith("\n") else linea + "\n")

    def _pasa_filtro(self, rec: LogRecord) -> bool:
        filtro = self.opciones.filtro
        return not filtro or filtro.upper() in rec.crudo.upper()

    # --- puntos de extension (los implementa cada modo) ----------------------

    def _contexto(self) -> ContextManager:
        """Contexto activo durante todo el bucle (p. ej. el Live de rich)."""
        raise NotImplementedError

    def _al_iniciar(self) -> None:
        """Se llama una vez, antes de la primera lectura."""

    def _al_terminar(self) -> None:
        """Se llama una vez, ya fuera del contexto de dibujado."""

    def _mostrar(self, rec: LogRecord) -> None:
        """Muestra una linea que paso el filtro."""
        raise NotImplementedError

    def _refrescar(self) -> None:
        """Se llama en cada vuelta del bucle, haya lineas nuevas o no."""

    def _aviso_archivo(self) -> None:
        """Avisa de que se empezo a seguir otro archivo."""

    def _aviso_rotacion(self) -> None:
        """Avisa de que el archivo se trunco o roto."""

    def _aviso_pausa(self) -> None:
        """Avisa del cambio entre pausa y reanudacion."""

    def _aviso_limpieza(self) -> None:
        """Avisa de que se reiniciaron los contadores."""
