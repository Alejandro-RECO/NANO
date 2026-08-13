"""Lectura de teclas sin bloquear, en Windows y en POSIX.

Se usa como context manager. Si la salida no es una terminal interactiva,
todo el objeto se comporta como un no-op que nunca devuelve teclas.

Las teclas normales se devuelven en minuscula ("p", "q"). Las demas se
traducen a un nombre comun en las dos plataformas: "arriba", "abajo",
"repag", "avpag", "inicio", "fin", "enter" y "esc".
"""

from __future__ import annotations

import sys

try:  # Windows
    import msvcrt
except ImportError:  # POSIX
    msvcrt = None

try:  # POSIX
    import termios
    import tty
    import select
except ImportError:  # Windows
    termios = tty = select = None

#: Segundo byte que manda msvcrt tras el prefijo \x00 o \xe0.
ESPECIALES_WIN = {
    b"H": "arriba", b"P": "abajo",
    b"I": "repag", b"Q": "avpag",
    b"G": "inicio", b"O": "fin",
}

#: Cola de la secuencia ANSI que manda una terminal POSIX tras "\x1b[".
ESPECIALES_POSIX = {
    "A": "arriba", "B": "abajo",
    "5~": "repag", "6~": "avpag",
    "H": "inicio", "1~": "inicio",
    "F": "fin", "4~": "fin",
}

#: Teclas de control con el mismo nombre en las dos plataformas.
CONTROLES = {"\r": "enter", "\n": "enter", "\x1b": "esc"}


class Teclado:
    """Devuelve la ultima tecla pulsada, o None si no hay ninguna."""

    def __init__(self, activo: bool = True) -> None:
        interactivo = sys.stdin.isatty() and sys.stdout.isatty()
        self.activo = bool(activo and interactivo and (msvcrt or termios))
        self._ajustes = None

    @property
    def disponible(self) -> bool:
        """True si realmente se pueden leer teclas en este entorno."""
        return self.activo

    def __enter__(self) -> "Teclado":
        if self.activo and termios is not None:
            try:
                fd = sys.stdin.fileno()
                self._ajustes = termios.tcgetattr(fd)
                tty.setcbreak(fd)
                # setcbreak deja el eco encendido: sin esto, cada tecla
                # pulsada se imprimiria encima del panel.
                modo = termios.tcgetattr(fd)
                modo[3] &= ~termios.ECHO
                termios.tcsetattr(fd, termios.TCSADRAIN, modo)
            except (termios.error, ValueError):
                self.activo = False
        return self

    def __exit__(self, *_exc: object) -> None:
        if self._ajustes is not None and termios is not None:
            try:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN,
                                  self._ajustes)
            except (termios.error, ValueError):
                pass
            self._ajustes = None

    def leer(self) -> str | None:
        """Tecla pulsada, o None si no hay ninguna. No bloquea nunca."""
        if not self.activo:
            return None
        if msvcrt is not None:
            return self._leer_windows()
        return self._leer_posix()

    # --- por plataforma ------------------------------------------------------

    def _leer_windows(self) -> str | None:
        if not msvcrt.kbhit():
            return None
        tecla = msvcrt.getch()
        if tecla in (b"\x00", b"\xe0"):  # prefijo de tecla especial
            return ESPECIALES_WIN.get(msvcrt.getch())
        try:
            caracter = tecla.decode("latin-1")
        except UnicodeDecodeError:
            return None
        return CONTROLES.get(caracter, caracter.lower())

    def _leer_posix(self) -> str | None:
        if not self._hay_datos():
            return None
        tecla = sys.stdin.read(1)
        if not tecla:
            return None
        if tecla != "\x1b":
            return CONTROLES.get(tecla, tecla.lower())

        # Escape a secas: nada mas en la cola de entrada.
        if not self._hay_datos():
            return "esc"
        # Secuencia de escape: "\x1b[" + cola (ej. "A", "5~").
        if sys.stdin.read(1) != "[":
            return None
        cola = ""
        while self._hay_datos() and len(cola) < 4:
            caracter = sys.stdin.read(1)
            cola += caracter
            if caracter.isalpha() or caracter == "~":
                break
        return ESPECIALES_POSIX.get(cola)

    @staticmethod
    def _hay_datos() -> bool:
        try:
            listas, _, _ = select.select([sys.stdin], [], [], 0)
        except (OSError, ValueError):
            return False
        return bool(listas)
