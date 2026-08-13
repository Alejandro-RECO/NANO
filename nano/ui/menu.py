"""Menus interactivos que se muestran al arrancar: tema y log a seguir."""

from __future__ import annotations

import os
import sys

from nano.core.catalogo import (
    LogDisponible,
    MasReciente,
    Objetivo,
    listar_logs,
    objetivo_de_bot,
    objetivo_de_log,
    objetivo_desde_texto,
)
from nano.ui.temas import (
    BLANCO,
    ORDEN_TEMAS,
    RESET,
    TEMA_POR_DEFECTO,
    TEMAS,
    Tema,
    ansi,
)

_ALIAS = {str(i): clave for i, clave in enumerate(ORDEN_TEMAS, 1)}
_ALIAS.update({clave: clave for clave in ORDEN_TEMAS})

#: Intentos antes de rendirse y usar el archivo mas reciente.
_INTENTOS = 3

#: Topes de ancho de las columnas del menu de logs.
_ANCHO_BOT = 18
_ANCHO_PROCESO = 12


def elegir_tema(preseleccion: str | None = None) -> Tema:
    """Devuelve el tema activo.

    Con `--theme` no pregunta. Sin terminal interactiva tampoco pregunta:
    usa el tema por defecto, para no bloquear tareas programadas ni pipes.
    """
    if preseleccion and preseleccion.lower() in TEMAS:
        return TEMAS[preseleccion.lower()]

    if not sys.stdin.isatty():
        return TEMAS[TEMA_POR_DEFECTO]

    acento = ansi(TEMAS[TEMA_POR_DEFECTO].colores["acento"])
    print(f"\n{acento}=== NANO - Elige un tema de colores ==={RESET}\n")
    for i, clave in enumerate(ORDEN_TEMAS, 1):
        tema = TEMAS[clave]
        marca = " (por defecto)" if clave == TEMA_POR_DEFECTO else ""
        print(f"  {i}) {tema.nombre:<12}{marca}   {tema.muestra_ansi()}")
    print(f"\n  Enter = 1 ({TEMAS[TEMA_POR_DEFECTO].nombre})")

    try:
        sel = input("  Opcion: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        sel = ""

    tema = TEMAS[_ALIAS.get(sel, TEMA_POR_DEFECTO)]
    print(f"{tema.ansi_acento}  Tema seleccionado: {tema.nombre}{RESET}")
    return tema


# --- eleccion del log a seguir ----------------------------------------------

def elegir_archivo(carpeta: str | os.PathLike[str], tema: Tema, *,
                   archivo: str | None = None, bot: str | None = None,
                   forzar: bool = False) -> Objetivo:
    """Devuelve el objetivo a seguir, preguntando solo si hace falta.

    No pregunta cuando: se paso --archivo o --bot, no hay terminal
    interactiva, o solo hay un .txt en la carpeta (salvo --elegir). En todos
    esos casos se conserva el comportamiento historico.
    """
    if archivo:
        return objetivo_desde_texto(archivo)
    if bot:
        return objetivo_de_bot(bot)

    disponibles = listar_logs(carpeta)
    if not sys.stdin.isatty():
        return MasReciente()
    if len(disponibles) < 2 and not forzar:
        return MasReciente()
    if not disponibles:
        print(f"{tema.ansi_acento}  No hay ningun .txt en "
              f"{os.path.abspath(carpeta)}: se seguira el primero que aparezca."
              f"{RESET}")
        return MasReciente()

    _imprimir_listado(disponibles, tema)
    return _preguntar(disponibles, tema)


def _imprimir_listado(disponibles: list[LogDisponible], tema: Tema) -> None:
    acento, fecha = tema.ansi_acento, tema.ansi_fecha
    ancho_bot = min(_ANCHO_BOT, max(len(d.bot) for d in disponibles))
    ancho_proc = min(_ANCHO_PROCESO, max(len(d.proceso) for d in disponibles))

    print(f"\n{acento}=== NANO - Elige el log a seguir ==={RESET}\n")
    print(f"{fecha}      {'BOT':<{ancho_bot}}  {'PROCESO':<{ancho_proc}}  "
          f"ARCHIVO{RESET}")
    for i, log in enumerate(disponibles, 1):
        marca_activo = (f"{tema.ansi('INFO')}ACTIVO{RESET}" if log.activo
                        else "      ")
        por_defecto = f" {fecha}(Enter){RESET}" if i == 1 else ""
        print(f"  {acento}{i:>2}){RESET} {fecha}{_recortar(log.bot, ancho_bot):<{ancho_bot}}"
              f"  {_recortar(log.proceso, ancho_proc):<{ancho_proc}}{RESET}  "
              f"{BLANCO}{log.nombre}{RESET}  {marca_activo}{por_defecto}")

    print(f"\n{fecha}  numero       seguir ese archivo exacto")
    print("  numero + b   seguir a ese bot (el mas reciente que coincida)")
    print(f"  Enter        el mas reciente{RESET}")


def _preguntar(disponibles: list[LogDisponible], tema: Tema) -> Objetivo:
    for intento in range(_INTENTOS):
        try:
            sel = input("\n  Opcion: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            sel = ""

        if not sel:
            return _confirmar(MasReciente(), tema)

        objetivo = interpretar_opcion(sel, disponibles)
        if objetivo is not None:
            return _confirmar(objetivo, tema)

        if intento < _INTENTOS - 1:
            print(f"{tema.ansi('ERROR')}  Opcion no valida. Escribe un numero "
                  f"entre 1 y {len(disponibles)}, opcionalmente con 'b'.{RESET}")

    return _confirmar(MasReciente(), tema)


def interpretar_opcion(sel: str,
                       disponibles: list[LogDisponible]) -> Objetivo | None:
    """Traduce lo tecleado a un objetivo, o None si no se entiende.

    Se aceptan "3", "3b" y "b3": el numero elige el archivo y la 'b' pide
    seguir al bot en vez de a ese archivo concreto.
    """
    texto = sel.replace(" ", "")
    por_bot = texto.startswith("b") or texto.endswith("b")
    numero = texto.strip("b")
    if not numero.isdigit():
        return None
    indice = int(numero) - 1
    if not 0 <= indice < len(disponibles):
        return None

    return objetivo_de_log(disponibles[indice], por_bot)


def _confirmar(objetivo: Objetivo, tema: Tema) -> Objetivo:
    print(f"{tema.ansi_acento}  Siguiendo: {objetivo.resumen}{RESET}")
    return objetivo


def _recortar(texto: str, ancho: int) -> str:
    return texto if len(texto) <= ancho else texto[: ancho - 1] + "…"
