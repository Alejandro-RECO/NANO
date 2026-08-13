"""Seguimiento incremental del archivo de log mas reciente de una carpeta."""

from __future__ import annotations

import codecs
import os

from nano.core.encoding import detectar_encoding

#: Lecturas seguidas sin datos nuevos tras las que se da por cerrada una
#: linea final que llego sin salto de linea.
_TICKS_PARA_CERRAR_RESTO = 2


def txt_mas_reciente(carpeta: str | os.PathLike[str]) -> str | None:
    """Ruta del .txt modificado mas recientemente en la carpeta, o None."""
    try:
        archivos = [
            os.path.join(carpeta, f)
            for f in os.listdir(carpeta)
            if f.lower().endswith(".txt")
        ]
    except OSError:
        return None
    if not archivos:
        return None
    try:
        return max(archivos, key=os.path.getmtime)
    except OSError:
        # Algun archivo desaparecio entre el listado y el stat.
        return None


class Seguidor:
    """Sigue (tail) el .txt mas reciente de una carpeta.

    Trabaja en binario con desplazamientos de bytes reales y un decodificador
    incremental, de modo que:

    - un caracter multibyte partido entre dos lecturas se reconstruye bien;
    - una linea que el escritor aun no ha terminado no se muestra a medias:
      se guarda y se completa en la siguiente lectura;
    - la posicion es comparable con el tamano del archivo, asi se detecta
      con fiabilidad el truncado o la rotacion.
    """

    def __init__(self, carpeta: str | os.PathLike[str], *,
                 desde_el_final: bool = False,
                 encoding_forzado: str | None = None) -> None:
        self.carpeta = carpeta
        self.desde_el_final = desde_el_final
        self.encoding_forzado = encoding_forzado

        self.archivo: str | None = None
        self.encoding: str = "utf-8"
        self._pos: int = 0
        self._resto: str = ""
        self._decodificador = codecs.getincrementaldecoder("utf-8")(
            errors="replace"
        )
        self._sin_datos: int = 0
        self._cambio: bool = False
        self._rotado: bool = False

    # --- estado observable ---------------------------------------------------

    @property
    def nombre_archivo(self) -> str:
        """Nombre (sin ruta) del archivo seguido, o cadena vacia."""
        return os.path.basename(self.archivo) if self.archivo else ""

    @property
    def hubo_cambio_de_archivo(self) -> bool:
        """True si se empezo a seguir otro archivo. Se consume al consultarla."""
        valor, self._cambio = self._cambio, False
        return valor

    @property
    def hubo_rotacion(self) -> bool:
        """True si el archivo se trunco o roto. Se consume al consultarla."""
        valor, self._rotado = self._rotado, False
        return valor

    # --- lectura -------------------------------------------------------------

    def leer_nuevas(self) -> list[str]:
        """Lineas aparecidas desde la llamada anterior.

        Devuelve una lista (no un generador) para que la posicion quede
        siempre actualizada, aunque quien la consume deje de recorrerla.
        Si la carpeta no tiene ningun .txt, devuelve una lista vacia.
        """
        nuevo = txt_mas_reciente(self.carpeta)
        if nuevo is None:
            return []

        if nuevo != self.archivo:
            self._empezar_archivo(nuevo)

        try:
            tam = os.path.getsize(self.archivo)
        except OSError:
            return []

        if tam < self._pos:  # truncado o rotado: volver al principio
            self._reiniciar_lectura()
            self._rotado = True

        if tam <= self._pos:
            return self._cerrar_resto_si_procede()

        try:
            with open(self.archivo, "rb") as fh:
                fh.seek(self._pos)
                datos = fh.read()
                self._pos = fh.tell()
        except OSError:
            return []

        self._sin_datos = 0
        texto = self._resto + self._decodificador.decode(datos)

        partes = texto.split("\n")
        self._resto = partes.pop()  # lo que va tras el ultimo salto de linea
        return [p + "\n" for p in partes]

    # --- internos ------------------------------------------------------------

    def _empezar_archivo(self, ruta: str) -> None:
        """Cambia el archivo seguido y reinicia el estado de decodificacion."""
        self.archivo = ruta
        self.encoding = detectar_encoding(ruta, self.encoding_forzado)
        self._cambio = True
        try:
            inicio = os.path.getsize(ruta) if self.desde_el_final else 0
        except OSError:
            inicio = 0
        self._reiniciar_lectura(inicio)

    def _reiniciar_lectura(self, pos: int = 0) -> None:
        self._pos = pos
        self._resto = ""
        self._sin_datos = 0
        self._decodificador = codecs.getincrementaldecoder(self.encoding)(
            errors="replace"
        )

    def _cerrar_resto_si_procede(self) -> list[str]:
        """Emite la ultima linea si llego sin salto y el archivo dejo de crecer."""
        if not self._resto:
            return []
        self._sin_datos += 1
        if self._sin_datos < _TICKS_PARA_CERRAR_RESTO:
            return []
        linea, self._resto = self._resto, ""
        self._sin_datos = 0
        return [linea + "\n"]


__all__ = ["Seguidor", "txt_mas_reciente"]
