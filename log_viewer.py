#!/usr/bin/env python3
"""NANO - Visor de logs en consola en tiempo real.

Vigila una carpeta, sigue (tail) el archivo .txt mas reciente y muestra
las lineas nuevas coloreando el nivel y su mensaje (INFO/WARNING/DEBUG/ERROR),
con la fecha siempre en blanco, sin necesidad de abrir y cerrar el archivo.
"""

import argparse
import os
import re
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

# Nivel -> color del nivel y su mensaje. Niveles ajustados al log real
# (INFO / WARNING / DEBUG / ERROR). Se incluyen variantes equivalentes.
COLORES_NIVEL = {
    "ERROR": Fore.RED + Style.BRIGHT,
    "CRITICAL": Fore.RED + Style.BRIGHT,
    "FATAL": Fore.RED + Style.BRIGHT,
    "WARNING": Fore.YELLOW + Style.BRIGHT,
    "WARN": Fore.YELLOW + Style.BRIGHT,
    "INFO": Fore.GREEN,
    "DEBUG": Fore.CYAN + Style.DIM,
    "TRACE": Fore.CYAN + Style.DIM,
}

# Fecha al inicio de la linea. Soporta DD/MM/YYYY (log real) y YYYY-MM-DD.
FECHA_RE = re.compile(
    r"^(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}|\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
)
# Nivel dentro del formato con barras:  | INFO |
NIVEL_BARRA_RE = re.compile(r"\|\s*([A-Za-z]+)\s*\|")

POLL_SEG = 0.3  # cada cuanto revisa cambios


def detectar_nivel(resto):
    """Detecta el nivel del log en el texto posterior a la fecha."""
    # Formato real:  fecha | NIVEL | mensaje | ...
    m = NIVEL_BARRA_RE.search(resto)
    if m and m.group(1).upper() in COLORES_NIVEL:
        return m.group(1).upper()
    # Formato simple:  fecha NIVEL mensaje
    m = re.match(r"\s*([A-Za-z]+)\b", resto)
    if m and m.group(1).upper() in COLORES_NIVEL:
        return m.group(1).upper()
    return None


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
    """Aplica filtro y color. Devuelve texto listo o None si se filtra.

    Reglas de color:
      - La fecha siempre se muestra en blanco.
      - El nivel y su mensaje se pintan del color del nivel.
      - Lineas sin nivel reconocido: todo en blanco.
    """
    if args.filter and args.filter.upper() not in linea.upper():
        return None

    cruda = linea.rstrip("\n")

    m_fecha = FECHA_RE.match(cruda)
    if m_fecha:
        fecha = m_fecha.group(1)
        resto = cruda[m_fecha.end():]
    else:
        fecha = ""
        resto = cruda

    nivel = detectar_nivel(resto if fecha else cruda)
    color = COLORES_NIVEL.get(nivel, Fore.WHITE)

    partes = []
    if args.timestamp:
        ahora = datetime.now().strftime("%H:%M:%S")
        partes.append(f"{Style.DIM}[{ahora}]{Style.RESET_ALL} ")
    if fecha:
        partes.append(Fore.WHITE + fecha)      # fecha siempre blanca
        partes.append(color + resto)           # nivel + mensaje con color
    else:
        partes.append(color + resto)
    return "".join(partes)


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
