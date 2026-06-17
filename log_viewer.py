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

from colorama import just_fix_windows_console

# Windows: msvcrt permite leer teclas sin bloquear (para pausa con 'p').
try:
    import msvcrt
except ImportError:  # No Windows
    msvcrt = None

# Habilita el procesamiento de secuencias ANSI en la consola de Windows
# SIN traducirlas, para poder usar color verdadero de 24 bits (neon/pastel).
just_fix_windows_console()

RESET = "\x1b[0m"
BLANCO = "\x1b[38;2;255;255;255m"  # mensaje siempre en blanco


def ansi(rgb):
    """Secuencia ANSI de color verdadero (24 bits) para primer plano."""
    r, g, b = rgb
    return f"\x1b[38;2;{r};{g};{b}m"


def ansi_fuerte(rgb, factor=1.6):
    """Version mas fuerte (mas saturada) del color, misma gama."""
    media = sum(rgb) / 3
    fuerte = tuple(
        max(0, min(255, round(media + (c - media) * factor))) for c in rgb
    )
    return ansi(fuerte)


# Temas de color. Cada nivel/elemento es un RGB; el color del nivel se usa
# tambien para el "resto" de la linea, y se deriva una variante mas fuerte
# para la palabra del nivel.
TEMAS = {
    "neon": {
        "nombre": "Neon",
        "ERROR": (255, 16, 80),     # rojo/rosa neon
        "WARNING": (255, 234, 0),   # amarillo neon
        "INFO": (57, 255, 20),      # verde neon
        "DEBUG": (0, 255, 255),     # cian neon
        "fecha": (255, 255, 255),   # blanco
        "acento": (255, 0, 255),    # magenta neon
    },
    "tokyo": {
        "nombre": "Tokyo Night",
        "ERROR": (247, 118, 142),   # #f7768e
        "WARNING": (224, 175, 104), # #e0af68
        "INFO": (158, 206, 106),    # #9ece6a
        "DEBUG": (125, 207, 255),   # #7dcfff
        "fecha": (192, 202, 245),   # #c0caf5
        "acento": (187, 154, 247),  # #bb9af7
    },
    "pastel": {
        "nombre": "Pastel",
        "ERROR": (255, 153, 162),   # rosa pastel
        "WARNING": (255, 234, 167), # amarillo pastel
        "INFO": (178, 235, 190),    # verde pastel
        "DEBUG": (174, 198, 255),   # azul pastel
        "fecha": (245, 245, 245),   # blanco suave
        "acento": (199, 179, 255),  # lila pastel
    },
}

# Variantes de nivel -> nivel canonico con color en los temas.
ALIAS_NIVEL = {
    "ERROR": "ERROR", "CRITICAL": "ERROR", "FATAL": "ERROR",
    "WARNING": "WARNING", "WARN": "WARNING",
    "INFO": "INFO",
    "DEBUG": "DEBUG", "TRACE": "DEBUG",
}

# Tema activo (se fija al arrancar). Por defecto: Neon.
TEMA = TEMAS["neon"]

# Fecha al inicio de la linea. Soporta DD/MM/YYYY (log real) y YYYY-MM-DD.
FECHA_RE = re.compile(
    r"^(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}|\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
)
# Nivel dentro del formato con barras:  | INFO |
NIVEL_BARRA_RE = re.compile(r"\|\s*([A-Za-z]+)\s*\|")

POLL_SEG = 0.3  # cada cuanto revisa cambios


def detectar_nivel(texto):
    """Detecta el nivel canonico (ERROR/WARNING/INFO/DEBUG) o None."""
    # Formato real:  fecha | NIVEL | mensaje | ...
    m = NIVEL_BARRA_RE.search(texto)
    if m and m.group(1).upper() in ALIAS_NIVEL:
        return ALIAS_NIVEL[m.group(1).upper()]
    # Formato simple:  fecha NIVEL mensaje  (se ignora la fecha inicial)
    mf = FECHA_RE.match(texto)
    resto = texto[mf.end():] if mf else texto
    m = re.match(r"\s*([A-Za-z]+)\b", resto)
    if m and m.group(1).upper() in ALIAS_NIVEL:
        return ALIAS_NIVEL[m.group(1).upper()]
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


def detectar_encoding(ruta, forzado=None):
    """Determina el encoding del archivo.

    Si --encoding lo fuerza, se respeta. Si no: prueba UTF-8 (con o sin BOM)
    y si falla usa cp1252 (Windows), comun en logs de Windows con acentos.
    """
    if forzado:
        return forzado
    try:
        with open(ruta, "rb") as fh:
            muestra = fh.read(65536)
        if muestra.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig"
        muestra.decode("utf-8")
        return "utf-8"
    except (UnicodeDecodeError, OSError):
        return "cp1252"


def formatear(linea, args):
    """Aplica filtro y color. Devuelve texto listo o None si se filtra.

    Campos separados por '|':  fecha | NIVEL | mensaje | resto...
    Reglas de color:
      - Fecha: color de fecha del tema.
      - NIVEL: color del nivel pero mas fuerte (misma gama, mas saturado).
      - Mensaje (3er campo): siempre blanco.
      - Resto de campos y separadores '|': color del nivel.
      - Lineas sin nivel reconocido: color de fecha.
    """
    if args.filter and args.filter.upper() not in linea.upper():
        return None

    cruda = linea.rstrip("\n")

    nivel = detectar_nivel(cruda)
    rgb = TEMA.get(nivel, TEMA["fecha"])
    col_nivel = ansi(rgb)                 # resto / separadores
    col_fuerte = ansi_fuerte(rgb)         # palabra del nivel
    col_fecha = ansi(TEMA["fecha"])

    prefijo = ""
    if args.timestamp:
        ahora = datetime.now().strftime("%H:%M:%S")
        prefijo = f"{col_fecha}[{ahora}] "

    # Formato con campos separados por '|'.
    if "|" in cruda and nivel is not None:
        campos = cruda.split("|")
        piezas = []
        for i, campo in enumerate(campos):
            if i == 0:
                c = col_fecha          # fecha
            elif i == 1:
                c = col_fuerte         # nivel (mas fuerte)
            elif i == 2:
                c = BLANCO             # mensaje (siempre blanco)
            else:
                c = col_nivel          # resto
            piezas.append(c + campo)
        # Separadores '|' con el color del nivel.
        cuerpo = (col_nivel + "|").join(piezas)
        return prefijo + cuerpo + RESET

    # Formato simple (sin barras): fecha en su color, resto color del nivel.
    m_fecha = FECHA_RE.match(cruda)
    if m_fecha:
        fecha = cruda[: m_fecha.end()]
        resto = cruda[m_fecha.end():]
        return prefijo + col_fecha + fecha + col_nivel + resto + RESET
    return prefijo + col_nivel + cruda + RESET


def tecla_pausa():
    """True si el usuario presiono 'p' (toggle pausa). Solo Windows."""
    if msvcrt and msvcrt.kbhit():
        tecla = msvcrt.getch().lower()
        return tecla in (b"p", b"q")
    return False


def elegir_tema(preseleccion=None):
    """Fija el tema activo. Usa preseleccion (--theme) o pregunta al usuario."""
    global TEMA
    orden = ["neon", "tokyo", "pastel"]

    if preseleccion and preseleccion.lower() in TEMAS:
        TEMA = TEMAS[preseleccion.lower()]
        return

    acento = ansi(TEMAS["neon"]["acento"])
    print(f"\n{acento}=== NANO - Elige un tema de colores ==={RESET}\n")
    for i, clave in enumerate(orden, 1):
        t = TEMAS[clave]
        muestra = (
            ansi_fuerte(t["INFO"]) + "INFO " + ansi_fuerte(t["WARNING"]) + "WARNING "
            + ansi_fuerte(t["ERROR"]) + "ERROR " + ansi_fuerte(t["DEBUG"]) + "DEBUG" + RESET
        )
        marca = " (por defecto)" if clave == "neon" else ""
        print(f"  {i}) {t['nombre']:<12}{marca}   {muestra}")
    print(f"\n  Enter = 1 (Neon)")

    try:
        sel = input("  Opcion: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        sel = ""

    mapa = {"1": "neon", "2": "tokyo", "3": "pastel",
            "neon": "neon", "tokyo": "tokyo", "pastel": "pastel"}
    TEMA = TEMAS[mapa.get(sel, "neon")]
    print(f"{ansi(TEMA['acento'])}  Tema seleccionado: {TEMA['nombre']}{RESET}")


def banner(carpeta):
    a = ansi(TEMA["acento"])
    print(a + "=" * 60)
    print(a + "  NANO - Visor de logs en tiempo real")
    print(a + f"  Carpeta vigilada: {os.path.abspath(carpeta)}")
    print(a + "  Ctrl+C para salir" + ("  |  'p' pausar" if msvcrt else ""))
    print(a + "=" * 60 + RESET)


def seguir(args):
    """Loop principal: detecta el .txt mas reciente y muestra lineas nuevas."""
    banner(args.carpeta)

    actual = None      # ruta del archivo que estamos siguiendo
    enc = "utf-8"      # encoding del archivo actual
    pos = 0            # ultima posicion leida (bytes)
    pausado = False
    salida = open(args.save, "a", encoding="utf-8") if args.save else None

    try:
        while True:
            if tecla_pausa():
                pausado = not pausado
                estado = "PAUSADO" if pausado else "REANUDADO"
                print(ansi(TEMA["acento"]) + f"-- {estado} --" + RESET)

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
                enc = detectar_encoding(actual, args.encoding)
                print(ansi(TEMA["acento"]) + f"\n>> Siguiendo: {os.path.basename(actual)} [{enc}]\n" + RESET)
                # Empieza al final si --tail, sino desde el inicio.
                pos = os.path.getsize(actual) if args.tail else 0

            tam = os.path.getsize(actual)

            # Archivo truncado/rotado: reinicia desde el principio.
            if tam < pos:
                pos = 0

            if tam > pos:
                with open(actual, "r", encoding=enc, errors="replace") as fh:
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
        print(ansi(TEMA["acento"]) + "\n\nSaliendo. Hasta luego!" + RESET)
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
    parser.add_argument(
        "--theme",
        choices=["neon", "tokyo", "pastel"],
        help="Tema de color. Si se omite, se elige al arrancar (default: neon).",
    )
    parser.add_argument(
        "--encoding",
        help="Forzar encoding del log (ej: utf-8, cp1252). Por defecto auto-detecta.",
    )
    args = parser.parse_args()

    # Salida de consola en UTF-8 para mostrar acentos y ñ correctamente.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    elegir_tema(args.theme)
    seguir(args)


if __name__ == "__main__":
    main()
