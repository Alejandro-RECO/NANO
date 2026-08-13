"""Temas de color y utilidades de color verdadero (24 bits).

El color del nivel se usa tambien para el "resto" de la linea, y de el se
deriva una variante mas saturada para la palabra del nivel.
"""

from __future__ import annotations

from dataclasses import dataclass

RGB = tuple

RESET = "\x1b[0m"
BLANCO = "\x1b[38;2;255;255;255m"  # mensaje siempre en blanco
BLANCO_HEX = "#ffffff"

#: Factor de saturacion de la variante "fuerte" de un color.
FACTOR_FUERTE = 1.6


def ansi(rgb: RGB) -> str:
    """Secuencia ANSI de color verdadero (24 bits) para primer plano."""
    r, g, b = rgb
    return f"\x1b[38;2;{r};{g};{b}m"


def realzar(rgb: RGB, factor: float = FACTOR_FUERTE) -> RGB:
    """Version mas saturada del color, dentro de la misma gama."""
    media = sum(rgb) / 3
    return tuple(max(0, min(255, round(media + (c - media) * factor)))
                 for c in rgb)


def ansi_fuerte(rgb: RGB, factor: float = FACTOR_FUERTE) -> str:
    """Secuencia ANSI de la variante mas fuerte del color."""
    return ansi(realzar(rgb, factor))


def hexadecimal(rgb: RGB) -> str:
    """Color en formato #rrggbb, que es lo que entiende rich."""
    r, g, b = rgb
    return f"#{r:02x}{g:02x}{b:02x}"


@dataclass(frozen=True)
class Tema:
    """Paleta de colores completa del visor."""

    clave: str
    nombre: str
    colores: dict

    # --- acceso a colores ----------------------------------------------------

    def rgb(self, nivel: str | None) -> RGB:
        """Color del nivel; si el nivel no se reconoce, el color de fecha."""
        return self.colores.get(nivel or "", self.colores["fecha"])

    def ansi(self, nivel: str | None) -> str:
        return ansi(self.rgb(nivel))

    def ansi_fuerte(self, nivel: str | None) -> str:
        return ansi_fuerte(self.rgb(nivel))

    @property
    def ansi_fecha(self) -> str:
        return ansi(self.colores["fecha"])

    @property
    def ansi_acento(self) -> str:
        return ansi(self.colores["acento"])

    # --- equivalentes para rich ----------------------------------------------

    def estilo(self, nivel: str | None) -> str:
        return hexadecimal(self.rgb(nivel))

    def estilo_fuerte(self, nivel: str | None) -> str:
        return hexadecimal(realzar(self.rgb(nivel)))

    @property
    def estilo_fecha(self) -> str:
        return hexadecimal(self.colores["fecha"])

    @property
    def estilo_acento(self) -> str:
        return hexadecimal(self.colores["acento"])

    def muestra_ansi(self) -> str:
        """Linea de ejemplo con los cuatro niveles, para el menu de temas."""
        piezas = [
            f"{self.ansi_fuerte(n)}{n}" for n in ("INFO", "WARNING", "ERROR", "DEBUG")
        ]
        return " ".join(piezas) + RESET


#: Definicion de los temas disponibles. Cada elemento es un RGB.
TEMAS: dict = {
    "neon": Tema(
        clave="neon",
        nombre="Neon",
        colores={
            "ERROR": (255, 16, 80),     # rojo/rosa neon
            "WARNING": (255, 234, 0),   # amarillo neon
            "INFO": (57, 255, 20),      # verde neon
            "DEBUG": (0, 255, 255),     # cian neon
            "fecha": (255, 255, 255),   # blanco
            "acento": (255, 0, 255),    # magenta neon
        },
    ),
    "tokyo": Tema(
        clave="tokyo",
        nombre="Tokyo Night",
        colores={
            "ERROR": (247, 118, 142),   # #f7768e
            "WARNING": (224, 175, 104), # #e0af68
            "INFO": (158, 206, 106),    # #9ece6a
            "DEBUG": (125, 207, 255),   # #7dcfff
            "fecha": (192, 202, 245),   # #c0caf5
            "acento": (187, 154, 247),  # #bb9af7
        },
    ),
    "pastel": Tema(
        clave="pastel",
        nombre="Pastel",
        colores={
            "ERROR": (255, 153, 162),   # rosa pastel
            "WARNING": (255, 234, 167), # amarillo pastel
            "INFO": (178, 235, 190),    # verde pastel
            "DEBUG": (174, 198, 255),   # azul pastel
            "fecha": (245, 245, 245),   # blanco suave
            "acento": (199, 179, 255),  # lila pastel
        },
    ),
}

#: Orden en que se listan los temas y cual es el predeterminado.
ORDEN_TEMAS: tuple = ("neon", "tokyo", "pastel")
TEMA_POR_DEFECTO = "neon"
