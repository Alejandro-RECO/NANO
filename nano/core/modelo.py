"""Modelo de datos de una linea de log."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class LogRecord:
    """Una linea de log ya interpretada.

    Toda linea produce un LogRecord, incluso si no se reconoce su formato:
    en ese caso `nivel` es None y `mensaje` es la linea completa.

    Campos del formato RPA:
        fecha | NIVEL | mensaje | bot | origen | url
          0       1        2       3      4       5
    """

    crudo: str
    """Linea original, sin el salto de linea final."""

    ts: datetime | None = None
    """Marca de tiempo del log (no la hora de lectura)."""

    nivel: str | None = None
    """Nivel canonico: ERROR, WARNING, INFO, DEBUG. None si no se reconoce."""

    mensaje: str = ""
    """Tercer campo, o la linea completa si no hay formato con barras."""

    bot: str | None = None
    """Cuarto campo: nombre del bot (ej. NEON)."""

    origen: str | None = None
    """Quinto campo: ruta del bot / HU / funcion que emitio la linea."""

    url: str | None = None
    """Sexto campo: URL del Control Room."""

    campos: list[str] = field(default_factory=list)
    """Split crudo por '|' sin limpiar, usado por el modo simple."""

    @property
    def origen_corto(self) -> str:
        """Ultimo segmento de `origen`, para mostrar sin ocupar media pantalla."""
        if not self.origen:
            return ""
        return self.origen.replace("/", "\\").rstrip("\\").rsplit("\\", 1)[-1]
