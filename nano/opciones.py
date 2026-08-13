"""Opciones de ejecucion, ya resueltas a partir de la linea de comandos."""

from __future__ import annotations

from dataclasses import dataclass

from nano import config


@dataclass(frozen=True)
class Opciones:
    """Configuracion de una ejecucion concreta del visor."""

    carpeta: str = "logs"
    filtro: str | None = None
    con_hora: bool = False
    guardar: str | None = None
    desde_el_final: bool = False
    encoding: str | None = None
    simple: bool = False
    ascii: bool = False
    max_errores: int = config.MAX_HISTORIAL
    panel_warning: bool = True
