"""Interfaz de linea de comandos: monta las piezas y arranca el visor."""

from __future__ import annotations

import argparse
import sys

from colorama import just_fix_windows_console

from nano import __version__, config
from nano.core.estado import EstadoSesion
from nano.core.seguidor import Seguidor
from nano.opciones import Opciones
from nano.ui.menu import elegir_archivo, elegir_tema
from nano.ui.resumen import imprimir_resumen
from nano.ui.temas import ORDEN_TEMAS, RESET


def construir_parser() -> argparse.ArgumentParser:
    """Define todas las opciones de la linea de comandos."""
    parser = argparse.ArgumentParser(
        prog="nano",
        description="NANO - Visor y panel de control de logs RPA en consola.",
    )
    parser.add_argument(
        "carpeta", nargs="?", default="logs",
        help="Carpeta a vigilar (default: ./logs). Sigue el .txt mas reciente.",
    )
    parser.add_argument(
        "-a", "--archivo",
        help="Sigue este archivo y no otro (util si varias personas comparten "
             "la carpeta). Admite comodines: 'Log_WPROFABRIC6RPA_*'. "
             "Salta el menu de seleccion.",
    )
    parser.add_argument(
        "--bot",
        help="Sigue el log mas reciente cuyo nombre contenga este texto "
             "(ej: --bot WPROFABRIC6RPA). Salta el menu de seleccion.",
    )
    parser.add_argument(
        "--elegir", action="store_true",
        help="Muestra el menu de seleccion de log aunque solo haya un archivo.",
    )
    parser.add_argument(
        "-f", "--filter", dest="filtro",
        help="Muestra solo lineas que contengan este texto (ej: ERROR). "
             "No afecta a los contadores del panel.",
    )
    parser.add_argument(
        "-t", "--timestamp", action="store_true",
        help="Antepone la hora de lectura a cada linea (solo modo simple).",
    )
    parser.add_argument(
        "-s", "--save", dest="guardar",
        help="Guarda tambien la salida mostrada en este archivo.",
    )
    parser.add_argument(
        "--tail", action="store_true",
        help="Empieza al final del archivo (ignora lo ya escrito).",
    )
    parser.add_argument(
        "--theme", dest="tema", choices=list(ORDEN_TEMAS),
        help="Tema de color. Si se omite, se elige al arrancar (default: neon).",
    )
    parser.add_argument(
        "--encoding",
        help="Forzar encoding del log (ej: utf-8, cp1252). Por defecto auto.",
    )
    parser.add_argument(
        "--simple", action="store_true",
        help="Stream plano linea por linea, sin panel de control.",
    )
    parser.add_argument(
        "--ascii", action="store_true",
        help="Dibuja el panel con bordes ASCII (consolas sin soporte Unicode).",
    )
    parser.add_argument(
        "--max-errores", type=int, default=config.MAX_HISTORIAL,
        metavar="N", dest="max_errores",
        help=f"Entradas de los paneles de historial (default: {config.MAX_HISTORIAL}).",
    )
    parser.add_argument(
        "--no-panel-warning", action="store_false", dest="panel_warning",
        help="Oculta el panel de WARNING y ensancha el de errores.",
    )
    parser.add_argument("--version", action="version", version=f"NANO {__version__}")
    return parser


def opciones_desde_args(args: argparse.Namespace) -> Opciones:
    """Convierte los argumentos ya parseados en un objeto Opciones."""
    return Opciones(
        carpeta=args.carpeta,
        archivo=args.archivo,
        bot=args.bot,
        elegir=args.elegir,
        filtro=args.filtro,
        con_hora=args.timestamp,
        guardar=args.guardar,
        desde_el_final=args.tail,
        encoding=args.encoding,
        simple=args.simple or not sys.stdout.isatty(),
        ascii=args.ascii,
        max_errores=max(1, args.max_errores),
        panel_warning=args.panel_warning,
    )


def crear_visor(opciones: Opciones, tema, seguidor: Seguidor,
                estado: EstadoSesion):
    """Elige el modo de visualizacion.

    El panel necesita `rich`; si no esta instalado se avisa y se sigue en
    modo simple en lugar de fallar.
    """
    if not opciones.simple:
        try:
            from nano.ui.dashboard import VisorDashboard
        except ImportError:
            print("[NANO] 'rich' no esta instalado: se usa el modo simple. "
                  "Instalalo con: pip install -r requirements.txt",
                  file=sys.stderr)
        else:
            return VisorDashboard(seguidor, estado, tema, opciones)

    from nano.ui.simple import VisorSimple
    return VisorSimple(seguidor, estado, tema, opciones)


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada. Devuelve el codigo de salida del proceso."""
    args = construir_parser().parse_args(argv)
    opciones = opciones_desde_args(args)

    # Habilita secuencias ANSI en la consola de Windows SIN traducirlas,
    # para poder usar color verdadero de 24 bits.
    just_fix_windows_console()
    try:
        # line_buffering: al redirigir a un archivo, Python usaria buffer de
        # bloque y la salida no apareceria hasta acumular varios KB, que en un
        # visor en vivo equivale a no ver nada.
        sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                               line_buffering=True)
    except (AttributeError, ValueError):
        pass

    tema = elegir_tema(args.tema)
    objetivo = elegir_archivo(
        opciones.carpeta, tema,
        archivo=opciones.archivo,
        bot=opciones.bot,
        forzar=opciones.elegir,
    )
    seguidor = Seguidor(
        opciones.carpeta,
        desde_el_final=opciones.desde_el_final,
        encoding_forzado=opciones.encoding,
        objetivo=objetivo,
    )
    estado = EstadoSesion(max_historial=opciones.max_errores)

    visor = crear_visor(opciones, tema, seguidor, estado)
    visor.ejecutar()

    if estado.total:
        imprimir_resumen(estado, tema, seguidor)
    print(f"{tema.ansi_acento}\nSaliendo. Hasta luego!{RESET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
