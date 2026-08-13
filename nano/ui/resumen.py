"""Resumen final que se imprime al salir, en ambos modos.

Se escribe en el flujo normal de la consola (no dentro del panel) para que
quede en el historial de scroll aunque el panel desaparezca.
"""

from __future__ import annotations

from nano import config
from nano.core.estado import EstadoSesion
from nano.core.seguidor import Seguidor
from nano.ui.temas import BLANCO, RESET, Tema

_ANCHO = 66


def imprimir_resumen(estado: EstadoSesion, tema: Tema,
                     seguidor: Seguidor | None = None) -> None:
    """Vuelca contadores, errores y ranking al cerrar la sesion."""
    acento = tema.ansi_acento
    print()
    print(acento + "=" * _ANCHO)
    print(acento + "  RESUMEN DE LA SESION" + RESET)
    print(acento + "=" * _ANCHO + RESET)

    if seguidor and seguidor.nombre_archivo:
        print(f"{tema.ansi_fecha}  Archivo   {BLANCO}{seguidor.nombre_archivo}"
              f"{tema.ansi_fecha}  [{seguidor.encoding}]{RESET}")
    if estado.bot_actual:
        print(f"{tema.ansi_fecha}  Bot       {BLANCO}{estado.bot_actual}{RESET}")
    print(f"{tema.ansi_fecha}  Periodo   {BLANCO}{_periodo(estado)}"
          f"{tema.ansi_fecha}   ({estado.duracion()}){RESET}")
    print(f"{tema.ansi_fecha}  Lineas    {BLANCO}{estado.total}{RESET}")
    print()

    for nivel in config.NIVELES:
        cantidad = estado.contadores[nivel]
        if not cantidad:
            continue
        print(f"  {tema.ansi_fuerte(nivel)}{nivel:<9}{RESET}"
              f"{tema.ansi(nivel)}{cantidad:>7}{RESET}")
    if estado.sin_nivel:
        print(f"  {tema.ansi_fecha}{'otras':<9}{estado.sin_nivel:>7}{RESET}")

    _imprimir_top(estado, tema)
    _imprimir_errores(estado, tema)
    print(acento + "=" * _ANCHO + RESET)


def _periodo(estado: EstadoSesion) -> str:
    if not estado.primera_ts or not estado.ultima_ts:
        return "sin marcas de tiempo"
    formato = "%d/%m/%Y %H:%M:%S"
    return (f"{estado.primera_ts.strftime(formato)} -> "
            f"{estado.ultima_ts.strftime('%H:%M:%S')}")


def _imprimir_top(estado: EstadoSesion, tema: Tema) -> None:
    top = estado.top(config.TOP_ERRORES)
    if not top:
        return
    print()
    print(f"{tema.ansi_acento}  Errores mas repetidos{RESET}")
    for mensaje, veces in top:
        print(f"  {tema.ansi('ERROR')}x{veces:<4}{BLANCO}{mensaje}{RESET}")


def _imprimir_errores(estado: EstadoSesion, tema: Tema) -> None:
    if not estado.ultimos_errores:
        return
    print()
    print(f"{tema.ansi_acento}  Ultimos errores{RESET}")
    for entrada in estado.ultimos_errores:
        origen = f"  {tema.ansi_fecha}{entrada.origen}" if entrada.origen else ""
        print(f"  {tema.ansi('ERROR')}{entrada.hora}  {BLANCO}{entrada.mensaje}"
              f"{origen}{RESET}")
