"""Parseo de lineas de log a `LogRecord`.

Formatos soportados:
  - RPA (real):  DD/MM/YYYY HH:MM:SS | NIVEL | mensaje | bot | origen | url
  - Simple:      YYYY-MM-DD HH:MM:SS NIVEL mensaje

Ninguna funcion de este modulo lanza excepciones ante entrada inesperada:
una linea irreconocible se devuelve con `nivel=None` y `mensaje` = la linea.
"""

from __future__ import annotations

import re
from datetime import datetime

from nano.core.modelo import LogRecord

#: Variantes de nivel -> nivel canonico con color en los temas.
ALIAS_NIVEL: dict[str, str] = {
    "ERROR": "ERROR", "CRITICAL": "ERROR", "FATAL": "ERROR",
    "WARNING": "WARNING", "WARN": "WARNING",
    "INFO": "INFO",
    "DEBUG": "DEBUG", "TRACE": "DEBUG",
}

#: Fecha al inicio de la linea. Soporta DD/MM/YYYY (log real) y YYYY-MM-DD.
FECHA_RE = re.compile(
    r"^(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}|\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
)

#: Nivel dentro del formato con barras:  | INFO |
NIVEL_BARRA_RE = re.compile(r"\|\s*([A-Za-z]+)\s*\|")

#: Primera palabra tras la fecha, para el formato sin barras.
PRIMERA_PALABRA_RE = re.compile(r"\s*([A-Za-z]+)\b")

_FORMATOS_FECHA = ("%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S")


def detectar_nivel(texto: str) -> str | None:
    """Devuelve el nivel canonico (ERROR/WARNING/INFO/DEBUG) o None."""
    # Formato real:  fecha | NIVEL | mensaje | ...
    m = NIVEL_BARRA_RE.search(texto)
    if m and m.group(1).upper() in ALIAS_NIVEL:
        return ALIAS_NIVEL[m.group(1).upper()]
    # Formato simple:  fecha NIVEL mensaje  (se ignora la fecha inicial)
    mf = FECHA_RE.match(texto)
    resto = texto[mf.end():] if mf else texto
    m = PRIMERA_PALABRA_RE.match(resto)
    if m and m.group(1).upper() in ALIAS_NIVEL:
        return ALIAS_NIVEL[m.group(1).upper()]
    return None


def detectar_fecha(texto: str) -> datetime | None:
    """Convierte la fecha inicial de la linea en datetime, o None."""
    m = FECHA_RE.match(texto.lstrip())
    if not m:
        return None
    crudo = m.group(1)
    for formato in _FORMATOS_FECHA:
        try:
            return datetime.strptime(crudo, formato)
        except ValueError:
            continue
    return None


def parsear_linea(linea: str) -> LogRecord:
    """Interpreta una linea de log. Nunca lanza."""
    crudo = linea.rstrip("\r\n")
    nivel = detectar_nivel(crudo)
    ts = detectar_fecha(crudo)
    campos = crudo.split("|")

    if len(campos) < 2:
        # Sin formato de campos: el mensaje es la linea sin la fecha inicial
        # ni la palabra del nivel.
        m = FECHA_RE.match(crudo)
        resto = crudo[m.end():] if m else crudo
        mp = PRIMERA_PALABRA_RE.match(resto)
        if mp and mp.group(1).upper() in ALIAS_NIVEL:
            resto = resto[mp.end():]
        return LogRecord(crudo=crudo, ts=ts, nivel=nivel,
                         mensaje=resto.strip(), campos=campos)

    limpios = [c.strip() for c in campos]
    # El formato RPA tiene 6 campos. Si hay mas, el mensaje contenia '|':
    # los tres ultimos siguen siendo bot / origen / url.
    if len(limpios) >= 6:
        mensaje = " | ".join(limpios[2:-3])
        bot, origen, url = limpios[-3], limpios[-2], limpios[-1]
    else:
        mensaje = limpios[2] if len(limpios) > 2 else ""
        bot = limpios[3] if len(limpios) > 3 else None
        origen = limpios[4] if len(limpios) > 4 else None
        url = None

    return LogRecord(
        crudo=crudo,
        ts=ts,
        nivel=nivel,
        mensaje=mensaje,
        bot=bot or None,
        origen=origen or None,
        url=url or None,
        campos=campos,
    )
