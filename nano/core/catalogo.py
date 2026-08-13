"""Que archivo de la carpeta hay que seguir.

Cuando varias personas monitorean sus bots contra la misma carpeta, cada una
escribe su propio .txt. Este modulo resuelve dos cosas:

- **Inventario**: que logs hay, de que bot y proceso son, y cuales estan
  recibiendo lineas ahora mismo.
- **Objetivo**: la estrategia con la que se decide, en cada lectura, que
  archivo tocar. Puede ser el mas reciente (comportamiento historico), uno
  fijo, o el mas reciente de un bot concreto.

Modulo puro: no importa nada de `nano.ui` ni imprime nada.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from fnmatch import fnmatch

from nano import config

#: Tramo final del nombre que es una fecha o un correlativo, no parte del bot.
#: Ej. en Log_WPROFABRIC6RPA_CGRPA070_20260616_2 -> "20260616" y "2".
#: Solo tramos de puros digitos: un bot llamado "BOT2" no se ve afectado.
_TRAMO_VARIABLE_RE = re.compile(r"^\d+$")

#: Prefijos del nombre que no aportan nada al identificar el bot.
_PREFIJOS_IGNORADOS = ("log", "logs")

#: Valor que se muestra cuando el nombre no permite deducir el dato.
SIN_DATO = "-"


# --- inventario --------------------------------------------------------------

@dataclass(frozen=True)
class LogDisponible:
    """Un .txt de la carpeta, con lo necesario para elegirlo en el menu."""

    ruta: str
    nombre: str
    bot: str
    proceso: str
    mtime: float
    activo: bool

    @property
    def patron(self) -> str:
        """Patron que sigue a este mismo bot aunque cambie la fecha."""
        return patron_de_bot(self.nombre)

    @property
    def etiqueta(self) -> str:
        """Como se nombra a este bot en pantalla."""
        if self.proceso and self.proceso != SIN_DATO:
            return f"{self.bot} {self.proceso}"
        return self.bot


def _sin_extension(nombre: str) -> str:
    """Nombre sin la extension .txt.

    No usa splitext porque para un nombre como '.txt' devolveria '.txt'
    entero (lo trata como archivo oculto sin extension).
    """
    if nombre.lower().endswith(".txt"):
        return nombre[:-4]
    return os.path.splitext(nombre)[0]


def tramos_estables(nombre: str) -> list[str]:
    """Tramos del nombre que identifican al bot, sin fecha ni extension.

    'Log_WPROFABRIC6RPA_CGRPA070_20260616.txt' -> ['WPROFABRIC6RPA', 'CGRPA070']
    """
    tramos = [t for t in _sin_extension(nombre).split("_") if t]
    if tramos and tramos[0].lower() in _PREFIJOS_IGNORADOS:
        tramos = tramos[1:]
    # Se quitan los tramos finales que son fecha o correlativo.
    while tramos and _TRAMO_VARIABLE_RE.match(tramos[-1]):
        tramos.pop()
    return tramos


def partes_del_nombre(nombre: str) -> tuple[str, str]:
    """(bot, proceso) deducidos del nombre del archivo."""
    tramos = tramos_estables(nombre)
    if not tramos:
        return SIN_DATO, SIN_DATO
    if len(tramos) == 1:
        return tramos[0], SIN_DATO
    return tramos[0], "_".join(tramos[1:])


def patron_de_bot(nombre: str) -> str:
    """Patron glob que casa con los logs del mismo bot en cualquier fecha.

    Si el nombre no tiene ningun tramo variable que quitar, el patron es el
    nombre completo: elegir "el bot" equivale entonces a fijar el archivo.
    """
    tramos = [t for t in _sin_extension(nombre).split("_") if t]
    estables = list(tramos)
    while estables and _TRAMO_VARIABLE_RE.match(estables[-1]):
        estables.pop()
    if not estables or len(estables) == len(tramos):
        return nombre
    return "_".join(estables) + "*"


def rutas_txt(carpeta: str | os.PathLike[str],
              patron: str | None = None) -> list[str]:
    """Rutas de los .txt de la carpeta, filtradas por patron si se indica."""
    try:
        nombres = os.listdir(carpeta)
    except OSError:
        return []
    return [
        os.path.join(carpeta, n) for n in nombres
        if n.lower().endswith(".txt")
        and (patron is None or fnmatch(n, patron))
    ]


def listar_logs(carpeta: str | os.PathLike[str],
                ahora: float | None = None) -> list[LogDisponible]:
    """Inventario de la carpeta, del archivo mas reciente al mas antiguo."""
    instante = time.time() if ahora is None else ahora
    disponibles = []
    for ruta in rutas_txt(carpeta):
        try:
            mtime = os.path.getmtime(ruta)
        except OSError:
            continue  # desaparecio entre el listado y el stat
        nombre = os.path.basename(ruta)
        bot, proceso = partes_del_nombre(nombre)
        disponibles.append(LogDisponible(
            ruta=ruta,
            nombre=nombre,
            bot=bot,
            proceso=proceso,
            mtime=mtime,
            activo=(instante - mtime) < config.UMBRAL_ACTIVO,
        ))
    disponibles.sort(key=lambda d: d.mtime, reverse=True)
    return disponibles


# --- objetivos ---------------------------------------------------------------

class Objetivo:
    """Estrategia para decidir que archivo seguir. Interfaz comun."""

    #: Texto corto para la cabecera del panel.
    descripcion: str = ""
    #: Texto completo para confirmar la eleccion por consola.
    resumen: str = ""

    def resolver(self, carpeta: str | os.PathLike[str]) -> str | None:
        """Ruta a seguir ahora mismo, o None si todavia no hay ninguna."""
        raise NotImplementedError


class MasReciente(Objetivo):
    """El .txt modificado mas recientemente. Comportamiento historico."""

    descripcion = "mas reciente"
    resumen = "el .txt mas reciente de la carpeta"

    def resolver(self, carpeta: str | os.PathLike[str]) -> str | None:
        return _mas_reciente(rutas_txt(carpeta))


class ArchivoFijo(Objetivo):
    """Un archivo concreto, exista o no todavia.

    No salta a otro archivo aunque aparezca uno mas nuevo: es justo lo que
    hace falta cuando varias personas comparten la carpeta.
    """

    def __init__(self, nombre: str) -> None:
        self.nombre = os.path.basename(nombre)
        self.descripcion = "fijado"
        self.resumen = f"solo {self.nombre}"

    def resolver(self, carpeta: str | os.PathLike[str]) -> str | None:
        ruta = os.path.join(carpeta, self.nombre)
        return ruta if os.path.isfile(ruta) else None


class PatronBot(Objetivo):
    """El .txt mas reciente de entre los que casan con un patron glob.

    Sirve para el monitoreo del dia a dia: manana el bot creara un archivo
    con otra fecha y se enganchara solo, sin tocar los de los demas.
    """

    def __init__(self, patron: str, etiqueta: str | None = None) -> None:
        self.patron = patron
        self.descripcion = f"bot {etiqueta or patron.rstrip('*')}"
        self.resumen = f"el log mas reciente de {patron}"

    def resolver(self, carpeta: str | os.PathLike[str]) -> str | None:
        return _mas_reciente(rutas_txt(carpeta, self.patron))


def objetivo_desde_texto(texto: str) -> Objetivo:
    """Traduce lo que se paso por --archivo a un objetivo.

    Con comodines se trata como patron; sin ellos, como archivo exacto.
    """
    if any(c in texto for c in "*?["):
        return PatronBot(texto)
    return ArchivoFijo(texto)


def objetivo_de_log(log: LogDisponible, por_bot: bool = False) -> Objetivo:
    """Objetivo que resulta de elegir un log del inventario.

    `por_bot` distingue las dos formas de elegir: seguir ese archivo exacto,
    o seguir al bot que lo escribe aunque manana cambie de nombre.
    """
    if por_bot:
        return PatronBot(log.patron, etiqueta=log.etiqueta)
    return ArchivoFijo(log.nombre)


def objetivo_de_bot(texto: str) -> Objetivo:
    """Objetivo de --bot: cualquier log cuyo nombre contenga ese texto."""
    return PatronBot(f"*{texto}*", etiqueta=texto)


def _mas_reciente(rutas: list[str]) -> str | None:
    if not rutas:
        return None
    try:
        return max(rutas, key=os.path.getmtime)
    except OSError:
        return None
