"""Tests del estado acumulado de la sesion."""

from datetime import datetime

from nano.core.estado import EstadoSesion, normalizar_mensaje
from nano.core.parser import parsear_linea


def linea(nivel: str, mensaje: str, hora: str = "14:09:19",
          origen: str = "\\Bots\\Main") -> str:
    return (f"16/06/2026 {hora} | {nivel} | {mensaje} | NEON | {origen} | "
            "https://ejemplo.local/")


def registrar(estado: EstadoSesion, *lineas: str, ahora: float = 0.0) -> None:
    for texto in lineas:
        estado.registrar(parsear_linea(texto), ahora=ahora)


def test_contadores_por_nivel():
    estado = EstadoSesion()
    registrar(estado,
              linea("INFO", "a"), linea("ERROR", "b"),
              linea("WARN", "c"), linea("DEBUG", "d"), linea("CRITICAL", "e"))
    assert estado.errores == 2      # ERROR + CRITICAL
    assert estado.warnings == 1
    assert estado.contadores["INFO"] == 1
    assert estado.total == 5


def test_lineas_sin_nivel_van_aparte():
    estado = EstadoSesion()
    registrar(estado, "texto suelto", linea("INFO", "a"))
    assert estado.sin_nivel == 1
    assert estado.total == 2


def test_historial_respeta_el_maximo():
    estado = EstadoSesion(max_historial=3)
    registrar(estado, *[linea("ERROR", f"fallo {i}") for i in range(10)])
    assert len(estado.ultimos_errores) == 3
    assert [e.mensaje for e in estado.ultimos_errores] == [
        "fallo 7", "fallo 8", "fallo 9"]


def test_warnings_en_su_propio_historial():
    estado = EstadoSesion()
    registrar(estado, linea("ERROR", "e1"), linea("WARNING", "w1"))
    assert [e.mensaje for e in estado.ultimos_errores] == ["e1"]
    assert [e.mensaje for e in estado.ultimos_warnings] == ["w1"]


def test_entrada_guarda_hora_y_origen_corto():
    estado = EstadoSesion()
    registrar(estado, linea("ERROR", "x", hora="15:30:45",
                            origen="\\Bots\\Facturacion\\MainProceso"))
    entrada = estado.ultimos_errores[0]
    assert entrada.hora == "15:30:45"
    assert entrada.origen == "MainProceso"


def test_top_agrupa_errores_equivalentes():
    estado = EstadoSesion()
    registrar(estado,
              linea("ERROR", "Timeout tabla [[Censo]] tras 30 s"),
              linea("ERROR", "Timeout tabla [[Urgencias]] tras 45 s"),
              linea("ERROR", "Elemento no encontrado"))
    top = estado.top()
    assert top[0][1] == 2
    assert "Timeout tabla [...] tras # s" == top[0][0]


def test_normalizar_mensaje_recorta():
    assert normalizar_mensaje("a" * 200, largo=10) == "a" * 10
    assert normalizar_mensaje("  doble   espacio  ") == "doble espacio"


def test_duracion_entre_primera_y_ultima_linea():
    estado = EstadoSesion()
    registrar(estado, linea("INFO", "a", hora="14:00:00"),
              linea("INFO", "b", hora="15:30:45"))
    assert estado.primera_ts == datetime(2026, 6, 16, 14, 0, 0)
    assert estado.duracion() == "01:30:45"


def test_duracion_sin_marcas_de_tiempo():
    estado = EstadoSesion()
    registrar(estado, "sin fecha")
    assert estado.duracion() == "--:--:--"


def test_ritmo_usa_la_ventana_deslizante():
    estado = EstadoSesion(ventana_ritmo=10.0)
    for i in range(5):
        registrar(estado, linea("INFO", str(i)), ahora=float(i))
    assert estado.ritmo(ahora=4.0) == 5 / 4
    # A los 100 s ya no queda ninguna marca dentro de la ventana.
    assert estado.ritmo(ahora=100.0) == 0.0


def test_ritmo_sin_lineas():
    assert EstadoSesion().ritmo(ahora=1.0) == 0.0


def test_inactividad():
    estado = EstadoSesion()
    assert estado.inactivo(ahora=5000.0) is False  # aun no llego nada
    registrar(estado, linea("INFO", "a"), ahora=0.0)
    assert estado.segundos_inactivo(ahora=30.0) == 30.0
    assert estado.inactivo(ahora=30.0) is False
    assert estado.inactivo(ahora=5000.0) is True


def test_bot_y_origen_actuales():
    estado = EstadoSesion()
    registrar(estado, linea("INFO", "a", origen="\\Bots\\Uno"))
    registrar(estado, linea("INFO", "b", origen="\\Bots\\Dos"))
    assert estado.bot_actual == "NEON"
    assert estado.origen_actual == "\\Bots\\Dos"


def test_limpiar_reinicia_todo_menos_el_archivo():
    estado = EstadoSesion()
    registrar(estado, linea("ERROR", "a"), linea("WARNING", "b"))
    estado.limpiar()
    assert estado.total == 0
    assert estado.errores == 0
    assert not estado.ultimos_errores
    assert not estado.ultimos_warnings
    assert not estado.top()
    assert estado.duracion() == "--:--:--"
    assert estado.bot_actual == "NEON"  # se conserva el contexto


def test_resumen_expone_los_datos_del_cierre():
    estado = EstadoSesion()
    registrar(estado, linea("ERROR", "fallo"), linea("INFO", "ok"))
    resumen = estado.resumen()
    assert resumen["total"] == 2
    assert resumen["contadores"]["ERROR"] == 1
    assert len(resumen["errores"]) == 1
    assert resumen["bot"] == "NEON"
