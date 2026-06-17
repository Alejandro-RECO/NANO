#!/usr/bin/env python3
"""NANO - Visor de logs en consola en tiempo real.

Vigila una carpeta, sigue (tail) el archivo .txt mas reciente y muestra
las lineas nuevas con colores segun el nivel (INFO/WARN/ERROR/DEBUG),
sin necesidad de abrir y cerrar el archivo para ver actualizaciones.
"""

import argparse
import os
import sys
import time
from datetime import datetime

from colorama import Fore, Style, init as colorama_init

# Windows: msvcrt permite leer teclas sin bloquear (para pausa con 'p').
try:
    import msvcrt
except ImportError:  # No Windows
    msvcrt = None

colorama_init(autoreset=True)

# Palabra clave de nivel -> color. Orden importa (ERROR antes que ERR).
NIVELES = [
    ("ERROR", Fore.RED + Style.BRIGHT),
    ("CRITICAL", Fore.RED + Style.BRIGHT),
    ("FATAL", Fore.RED + Style.BRIGHT),
    ("WARN", Fore.YELLOW + Style.BRIGHT),
    ("WARNING", Fore.YELLOW + Style.BRIGHT),
    ("INFO", Fore.GREEN),
    ("DEBUG", Fore.CYAN + Style.DIM),
    ("TRACE", Fore.CYAN + Style.DIM),
]

POLL_SEG = 0.3  # cada cuanto revisa cambios


def color_para(linea):
    """Devuelve el color ANSI segun el nivel detectado en la linea."""
    upper = linea.upper()
    for clave, color in NIVELES:
        if clave in upper:
            return color
    return Fore.WHITE


def txt_mas_reciente(carpeta):
    """Ruta del .txt modificado mas recientemente en la carpeta, o None."""
    try:
        archivos = [
            os.path.join(carpeta, f)
            for f in os.listdir(carpeta)
            if f.lower().endswith(".txt")
        ]
    except FileNotFoundError:
        return None
    if not archivos:
        return None
    return max(archivos, key=os.path.getmtime)


def formatear(linea, args):
    """Aplica filtro, timestamp y color. Devuelve texto listo o None si se filtra."""
    if args.filter and args.filter.upper() not in linea.upper():
        return None
    texto = linea.rstrip("\n")
    if args.timestamp:
        ahora = datetime.now().strftime("%H:%M:%S")
        texto = f"{Style.DIM}[{ahora}]{Style.RESET_ALL} {texto}"
    return color_para(linea) + texto


def tecla_pausa():
    """True si el usuario presiono 'p' (toggle pausa). Solo Windows."""
    if msvcrt and msvcrt.kbhit():
        tecla = msvcrt.getch().lower()
        return tecla in (b"p", b"q")
    return False


def banner(carpeta):
    print(Fore.MAGENTA + Style.BRIGHT + "=" * 60)
    print(Fore.MAGENTA + Style.BRIGHT + "  NANO - Visor de logs en tiempo real")
    print(Fore.MAGENTA + f"  Carpeta vigilada: {os.path.abspath(carpeta)}")
    print(Fore.MAGENTA + "  Ctrl+C para salir" + ("  |  'p' pausar" if msvcrt else ""))
    print(Fore.MAGENTA + Style.BRIGHT + "=" * 60 + Style.RESET_ALL)


def seguir(args):
    """Loop principal: detecta el .txt mas reciente y muestra lineas nuevas."""
    banner(args.carpeta)

    actual = None      # ruta del archivo que estamos siguiendo
    pos = 0            # ultima posicion leida (bytes)
    pausado = False
    salida = open(args.save, "a", encoding="utf-8") if args.save else None

    try:
        while True:
            if tecla_pausa():
                pausado = not pausado
                estado = "PAUSADO" if pausado else "REANUDADO"
                print(Fore.MAGENTA + Style.BRIGHT + f"-- {estado} --")

            if pausado:
                time.sleep(POLL_SEG)
                continue

            nuevo = txt_mas_reciente(args.carpeta)

            if nuevo is None:
                time.sleep(1)
                continue

            # Cambio a un archivo mas reciente.
            if nuevo != actual:
                actual = nuevo
                print(Fore.MAGENTA + Style.BRIGHT + f"\n>> Siguiendo: {os.path.basename(actual)}\n")
                # Empieza al final si --tail, sino desde el inicio.
                pos = os.path.getsize(actual) if args.tail else 0

            tam = os.path.getsize(actual)

            # Archivo truncado/rotado: reinicia desde el principio.
            if tam < pos:
                pos = 0

            if tam > pos:
                with open(actual, "r", encoding="utf-8", errors="replace") as fh:
                    fh.seek(pos)
                    for linea in fh:
                        salida_color = formatear(linea, args)
                        if salida_color is not None:
                            print(salida_color)
                            if salida:
                                salida.write(linea if linea.endswith("\n") else linea + "\n")
                    pos = fh.tell()
                if salida:
                    salida.flush()

            time.sleep(POLL_SEG)

    except KeyboardInterrupt:
        print(Fore.MAGENTA + Style.BRIGHT + "\n\nSaliendo. Hasta luego!" + Style.RESET_ALL)
    finally:
        if salida:
            salida.close()


def main():
    parser = argparse.ArgumentParser(
        description="NANO - Visor de logs en consola en tiempo real con colores."
    )
    parser.add_argument(
        "carpeta",
        nargs="?",
        default="logs",
        help="Carpeta a vigilar (default: ./logs). Sigue el .txt mas reciente.",
    )
    parser.add_argument(
        "-f", "--filter",
        help="Muestra solo lineas que contengan este texto (ej: ERROR).",
    )
    parser.add_argument(
        "-t", "--timestamp",
        action="store_true",
        help="Antepone la hora a cada linea.",
    )
    parser.add_argument(
        "-s", "--save",
        help="Guarda tambien la salida mostrada en este archivo.",
    )
    parser.add_argument(
        "--tail",
        action="store_true",
        help="Empieza al final del archivo (ignora lo ya escrito).",
    )
    args = parser.parse_args()
    seguir(args)


if __name__ == "__main__":
    main()
