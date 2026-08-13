"""Constantes de configuracion de NANO.

Toda constante "magica" del proyecto vive aqui para poder ajustarla en un
solo sitio y para que los tests puedan referirse a ella por nombre.
"""

from __future__ import annotations

# --- Seguimiento del archivo -------------------------------------------------

#: Cada cuantos segundos se revisa si el archivo crecio.
POLL_SEG: float = 0.3

#: Bytes que se leen del archivo para adivinar su encoding.
MUESTRA_ENCODING: int = 65536

#: Encoding de reserva cuando el archivo no es UTF-8 (tipico en Windows).
ENCODING_RESERVA: str = "cp1252"

# --- Estado de la sesion -----------------------------------------------------

#: Cuantos ERROR/WARNING recientes conservan los paneles de historial.
MAX_HISTORIAL: int = 8

#: Ventana deslizante (segundos) sobre la que se calcula el ritmo de lineas/s.
VENTANA_RITMO: float = 60.0

#: Longitud maxima del mensaje normalizado usado para agrupar errores repetidos.
MAX_MENSAJE_TOP: int = 80

#: Segundos sin lineas nuevas tras los que el proceso se considera "inactivo".
UMBRAL_INACTIVO: float = 120.0

#: Segundos desde la ultima escritura por debajo de los cuales un archivo se
#: marca como ACTIVO en el menu de seleccion de log.
UMBRAL_ACTIVO: float = 120.0

# --- Panel de control --------------------------------------------------------

#: Lineas que guarda el buffer del stream (se muestran solo las que quepan).
BUFFER_STREAM: int = 1000

#: El panel se redibuja desde el bucle principal, no desde un hilo de rich:
#: la cadencia real es una vez por vuelta, es decir cada POLL_SEG segundos.

#: Alturas fijas (en filas) de cada zona del layout, bordes incluidos.
ALTO_CABECERA: int = 4
ALTO_PANELES: int = 9
ALTO_TOP: int = 3
ALTO_BARRA: int = 1

#: Minimo de lineas de log visibles aunque la terminal sea muy baja.
MIN_ALTO_STREAM: int = 3

#: Ancho de la columna de resumen (contadores) dentro de la franja inferior.
ANCHO_RESUMEN: int = 24

#: Entradas del ranking de errores repetidos que se intentan mostrar.
TOP_ERRORES: int = 4

#: Niveles canonicos, en el orden en que se listan en el panel de resumen.
NIVELES: tuple[str, ...] = ("ERROR", "WARNING", "INFO", "DEBUG")
