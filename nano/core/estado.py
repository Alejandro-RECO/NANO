"""Estado acumulado de la sesion: contadores, historiales y ritmo.

Clase pura, sin entrada/salida: recibe `LogRecord` y ofrece lo que el panel
de control necesita pintar. Es la pieza con mas cobertura de tests.
"""

from __future__ import annotations

import re
import time
from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import datetime

from nano import config
from nano.core.modelo import LogRecord

#: Numeros -> '#', para que "Reintento 3" y "Reintento 7" cuenten como uno.
_NUMEROS_RE = re.compile(r"\d+")
#: Contenido entre corchetes -> '[...]' (tablas, rutas, ids variables).
#: Los '+' cubren los corchetes dobles del log RPA, p. ej. [[Censo]].
_CORCHETES_RE = re.compile(r"\[+[^\[\]]*\]+")
#: Espacios repetidos -> uno solo.
_ESPACIOS_RE = re.compile(r"\s+")


def normalizar_mensaje(mensaje: str,
                       largo: int = config.MAX_MENSAJE_TOP) -> str:
    """Reduce un mensaje a su "forma" para agrupar errores equivalentes."""
    texto = _CORCHETES_RE.sub("[...]", mensaje)
    texto = _NUMEROS_RE.sub("#", texto)
    texto = _ESPACIOS_RE.sub(" ", texto).strip()
    return texto[:largo]


@dataclass(frozen=True)
class Entrada:
    """Una linea guardada en un panel de historial."""

    ts: datetime | None
    mensaje: str
    origen: str

    @property
    def hora(self) -> str:
        """Hora del log en HH:MM:SS, o '--:--:--' si la linea no la traia."""
        return self.ts.strftime("%H:%M:%S") if self.ts else "--:--:--"


@dataclass
class EstadoSesion:
    """Todo lo que el panel de control muestra sobre la sesion en curso."""

    max_historial: int = config.MAX_HISTORIAL
    ventana_ritmo: float = config.VENTANA_RITMO

    contadores: Counter = field(default_factory=Counter)
    top_errores: Counter = field(default_factory=Counter)
    total: int = 0
    sin_nivel: int = 0

    primera_ts: datetime | None = None
    ultima_ts: datetime | None = None
    ultima_recepcion: float | None = None
    inicio_sesion: float = field(default_factory=time.monotonic)

    bot_actual: str | None = None
    origen_actual: str | None = None

    ultimos_errores: deque = field(init=False)
    ultimos_warnings: deque = field(init=False)
    _marcas: deque = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.ultimos_errores = deque(maxlen=self.max_historial)
        self.ultimos_warnings = deque(maxlen=self.max_historial)
        self._marcas = deque()

    # --- ingesta -------------------------------------------------------------

    def registrar(self, rec: LogRecord, *, ahora: float | None = None) -> None:
        """Incorpora una linea al estado.

        `ahora` (reloj monotono) es inyectable para poder testear el ritmo
        sin esperas reales.
        """
        instante = time.monotonic() if ahora is None else ahora
        self.total += 1
        self.ultima_recepcion = instante
        self._marcas.append(instante)
        self._podar_marcas(instante)

        if rec.nivel:
            self.contadores[rec.nivel] += 1
        else:
            self.sin_nivel += 1

        if rec.ts:
            if self.primera_ts is None:
                self.primera_ts = rec.ts
            self.ultima_ts = rec.ts
        if rec.bot:
            self.bot_actual = rec.bot
        if rec.origen:
            self.origen_actual = rec.origen

        if rec.nivel == "ERROR":
            self.ultimos_errores.append(self._entrada(rec))
            self.top_errores[normalizar_mensaje(rec.mensaje)] += 1
        elif rec.nivel == "WARNING":
            self.ultimos_warnings.append(self._entrada(rec))

    def limpiar(self) -> None:
        """Reinicia contadores e historiales sin perder el archivo seguido."""
        self.contadores.clear()
        self.top_errores.clear()
        self.ultimos_errores.clear()
        self.ultimos_warnings.clear()
        self._marcas.clear()
        self.total = 0
        self.sin_nivel = 0
        self.primera_ts = None
        self.ultima_ts = None
        self.ultima_recepcion = None
        self.inicio_sesion = time.monotonic()

    def reiniciar_todo(self) -> None:
        """Como `limpiar`, pero olvidando tambien el bot y la HU.

        Se usa al cambiar de archivo: el contexto del log anterior es de otro
        proceso y mezclarlo haria que los paneles mintieran.
        """
        self.limpiar()
        self.bot_actual = None
        self.origen_actual = None

    # --- consultas -----------------------------------------------------------

    @property
    def errores(self) -> int:
        return self.contadores["ERROR"]

    @property
    def warnings(self) -> int:
        return self.contadores["WARNING"]

    def duracion(self) -> str:
        """Tiempo cubierto por el log (primera a ultima linea) como HH:MM:SS."""
        if not self.primera_ts or not self.ultima_ts:
            return "--:--:--"
        segundos = int((self.ultima_ts - self.primera_ts).total_seconds())
        if segundos < 0:
            return "--:--:--"
        horas, resto = divmod(segundos, 3600)
        minutos, seg = divmod(resto, 60)
        return f"{horas:02d}:{minutos:02d}:{seg:02d}"

    def ritmo(self, ahora: float | None = None) -> float:
        """Lineas por segundo en la ventana deslizante reciente."""
        instante = time.monotonic() if ahora is None else ahora
        self._podar_marcas(instante)
        if not self._marcas:
            return 0.0
        transcurrido = instante - self._marcas[0]
        if transcurrido <= 0:
            return float(len(self._marcas))
        return len(self._marcas) / transcurrido

    def segundos_inactivo(self, ahora: float | None = None) -> float:
        """Segundos desde la ultima linea recibida (0 si aun no llego ninguna)."""
        if self.ultima_recepcion is None:
            return 0.0
        instante = time.monotonic() if ahora is None else ahora
        return max(0.0, instante - self.ultima_recepcion)

    def inactivo(self, ahora: float | None = None) -> bool:
        """True si hace demasiado que no llega nada: el bot pudo colgarse."""
        if self.ultima_recepcion is None:
            return False
        return self.segundos_inactivo(ahora) >= config.UMBRAL_INACTIVO

    def top(self, cuantos: int = config.TOP_ERRORES) -> list[tuple[str, int]]:
        """Errores repetidos mas frecuentes, del mas comun al menos."""
        return [par for par in self.top_errores.most_common(cuantos)
                if par[1] > 0]

    def resumen(self) -> dict[str, object]:
        """Datos planos para imprimir el resumen final al salir."""
        return {
            "total": self.total,
            "contadores": dict(self.contadores),
            "sin_nivel": self.sin_nivel,
            "duracion": self.duracion(),
            "primera_ts": self.primera_ts,
            "ultima_ts": self.ultima_ts,
            "bot": self.bot_actual,
            "errores": list(self.ultimos_errores),
            "top": self.top(),
        }

    # --- internos ------------------------------------------------------------

    def _entrada(self, rec: LogRecord) -> Entrada:
        return Entrada(ts=rec.ts, mensaje=rec.mensaje or rec.crudo,
                       origen=rec.origen_corto)

    def _podar_marcas(self, ahora: float) -> None:
        limite = ahora - self.ventana_ritmo
        while self._marcas and self._marcas[0] < limite:
            self._marcas.popleft()
