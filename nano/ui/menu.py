"""Menu interactivo de seleccion de tema al arrancar."""

from __future__ import annotations

import sys

from nano.ui.temas import ORDEN_TEMAS, RESET, TEMA_POR_DEFECTO, TEMAS, Tema, ansi

_ALIAS = {str(i): clave for i, clave in enumerate(ORDEN_TEMAS, 1)}
_ALIAS.update({clave: clave for clave in ORDEN_TEMAS})


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
