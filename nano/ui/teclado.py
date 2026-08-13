"""Lectura de teclas sin bloquear, en Windows y en POSIX.

Se usa como context manager. Si la salida no es una terminal interactiva,
todo el objeto se comporta como un no-op que nunca devuelve teclas.
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
                self._ajustes = termios.tcgetattr(sys.stdin.fileno())
                tty.setcbreak(sys.stdin.fileno())
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
        """Tecla pulsada en minuscula, o None. No bloquea nunca."""
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
        if tecla in (b"\x00", b"\xe0"):  # teclas especiales: descartar el par
            msvcrt.getch()
            return None
        try:
            return tecla.decode("latin-1").lower()
        except UnicodeDecodeError:
            return None

    def _leer_posix(self) -> str | None:
        try:
            listas, _, _ = select.select([sys.stdin], [], [], 0)
        except (OSError, ValueError):
            return None
        if not listas:
            return None
        tecla = sys.stdin.read(1)
        return tecla.lower() if tecla else None
