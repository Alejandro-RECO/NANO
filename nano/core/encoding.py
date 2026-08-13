"""Deteccion del encoding de los archivos de log."""

from __future__ import annotations

import codecs
import os

from nano import config


def detectar_encoding(ruta: str | os.PathLike[str],
                      forzado: str | None = None) -> str:
    """Determina el encoding del archivo.

    Si `forzado` (--encoding) tiene valor, se respeta sin mirar el archivo.
    Si no: BOM -> utf-8-sig; si la muestra decodifica como UTF-8 -> utf-8;
    en caso contrario cp1252, comun en logs de Windows con acentos.

    Se usa un decodificador incremental para que un caracter multibyte
    cortado al final de la muestra no se confunda con "no es UTF-8".
    """
    if forzado:
        return forzado
    try:
        with open(ruta, "rb") as fh:
            muestra = fh.read(config.MUESTRA_ENCODING)
    except OSError:
        return config.ENCODING_RESERVA

    if muestra.startswith(codecs.BOM_UTF8):
        return "utf-8-sig"
    try:
        codecs.getincrementaldecoder("utf-8")().decode(muestra, False)
        return "utf-8"
    except UnicodeDecodeError:
        return config.ENCODING_RESERVA
