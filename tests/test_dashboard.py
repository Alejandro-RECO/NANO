"""Tests de render del panel de control.

No se arranca el bucle en vivo: se pinta el layout sobre una consola de
prueba de tamano fijo y se comprueba el texto resultante.
"""

import os
import time

import pytest

from nano.core.catalogo import ArchivoFijo, PatronBot
from nano.core.estado import EstadoSesion
from nano.core.parser import parsear_linea
from nano.core.seguidor import Seguidor
from nano.opciones import Opciones
from nano.ui.temas import TEMAS

rich = pytest.importorskip("rich")
from rich.console import Console  # noqa: E402

from nano.ui.dashboard import VisorDashboard  # noqa: E402

ANCHO, ALTO = 110, 34


def linea(nivel, mensaje, hora="14:09:19", origen="\\Bots\\Main\\Proceso"):
    return (f"16/06/2026 {hora} | {nivel} | {mensaje} | NEON | {origen} | "
            "https://ejemplo.local/\n")


def construir(tmp_path, opciones=None, lineas=()):
    (tmp_path / "log.txt").write_text("", encoding="utf-8")
    opciones = opciones or Opciones(carpeta=str(tmp_path))
    seguidor = Seguidor(str(tmp_path))
    estado = EstadoSesion(max_historial=opciones.max_errores)
    visor = VisorDashboard(seguidor, estado, TEMAS["neon"], opciones)
    visor.console = Console(width=ANCHO, height=ALTO, force_terminal=True,
                            color_system="truecolor", record=True)
    for texto in lineas:
        rec = parsear_linea(texto)
        estado.registrar(rec)
        visor._mostrar(rec)
    return visor


def pintar(visor) -> str:
    visor.console.print(visor._render())
    return visor.console.export_text()


def test_render_vacio_no_falla(tmp_path):
    salida = pintar(construir(tmp_path))
    assert "NANO" in salida
    assert "RESUMEN" in salida
    assert "sin registros" in salida
    assert "sin errores repetidos" in salida


def test_render_muestra_contadores_y_errores(tmp_path):
    lineas = [
        linea("INFO", "Inicio del proceso"),
        linea("WARNING", "Uso de memoria al 82%", hora="14:10:00"),
        linea("ERROR", "Fallo al procesar el lote", hora="14:11:00"),
        linea("ERROR", "Timeout tabla [[Censo]] tras 30 s", hora="14:12:00"),
        linea("ERROR", "Timeout tabla [[Urgencias]] tras 45 s", hora="14:13:00"),
    ]
    salida = pintar(construir(tmp_path, lineas=lineas))

    assert "Fallo al procesar el lote" in salida     # stream
    assert "ULTIMOS ERRORES" in salida
    assert "ULTIMOS WARNING" in salida
    assert "TOP ERRORES" in salida
    assert "x2" in salida                            # timeouts agrupados
    assert "BOT" in salida and "NEON" in salida
    assert "EN VIVO" in salida


def test_el_panel_no_desborda_el_ancho(tmp_path):
    largo = "mensaje larguisimo " * 20
    lineas = [linea("ERROR", largo, origen="\\Bots\\Ruta\\Muy\\Larga\\DeVerdad")]
    salida = pintar(construir(tmp_path, lineas=lineas))
    for fila in salida.splitlines():
        assert len(fila) <= ANCHO


def test_altura_respeta_el_layout(tmp_path):
    lineas = [linea("INFO", f"linea {i}") for i in range(200)]
    salida = pintar(construir(tmp_path, lineas=lineas))
    assert len(salida.splitlines()) <= ALTO
    assert "linea 199" in salida        # se ve lo mas reciente
    assert "linea 0" not in salida      # lo viejo se desplaza


def test_sin_panel_de_warning(tmp_path):
    opciones = Opciones(carpeta=str(tmp_path), panel_warning=False)
    salida = pintar(construir(tmp_path, opciones=opciones,
                              lineas=[linea("WARNING", "aviso")]))
    assert "ULTIMOS WARNING" not in salida
    assert "ULTIMOS ERRORES" in salida


def test_modo_ascii_no_usa_box_drawing(tmp_path):
    opciones = Opciones(carpeta=str(tmp_path), ascii=True)
    salida = pintar(construir(tmp_path, opciones=opciones,
                              lineas=[linea("INFO", "hola")]))
    assert "╭" not in salida and "│" not in salida
    assert "+" in salida


def test_avisos_del_visor_aparecen_en_el_stream(tmp_path):
    visor = construir(tmp_path)
    visor._live = None
    visor._avisar("Archivo rotado")
    assert "Archivo rotado" in pintar(visor)


def test_pausa_e_inactividad_en_la_barra(tmp_path):
    visor = construir(tmp_path, lineas=[linea("INFO", "x")])
    visor.pausado = True
    assert "PAUSADO" in pintar(visor)


@pytest.mark.parametrize("tema", ["neon", "tokyo", "pastel"])
def test_todos_los_temas_pintan(tmp_path, tema):
    visor = construir(tmp_path, lineas=[linea("ERROR", "algo")])
    visor.tema = TEMAS[tema]
    assert "ULTIMOS ERRORES" in pintar(visor)


def test_terminal_muy_baja_sigue_pintando(tmp_path):
    visor = construir(tmp_path, lineas=[linea("INFO", "x")])
    visor.console = Console(width=80, height=12, force_terminal=True,
                            color_system="truecolor", record=True)
    salida = pintar(visor)
    assert "RESUMEN" in salida


# --- navegacion por el historial --------------------------------------------

def con_muchas_lineas(tmp_path, cuantas=200):
    return construir(tmp_path,
                     lineas=[linea("INFO", f"linea {i}") for i in range(cuantas)])


def test_al_inicio_la_vista_esta_pegada_al_vivo(tmp_path):
    visor = con_muchas_lineas(tmp_path)
    assert visor.desplazamiento == 0
    assert visor.en_historial is False
    salida = pintar(visor)
    assert "linea 199" in salida
    assert "HISTORIAL" not in salida


def test_flecha_arriba_sube_una_linea(tmp_path):
    visor = con_muchas_lineas(tmp_path)
    visor._tecla_extra("arriba")
    assert visor.desplazamiento == 1
    salida = pintar(visor)
    assert "linea 198" in salida
    assert "linea 199" not in salida
    assert "HISTORIAL" in salida


def test_repag_salta_una_pantalla_y_avpag_vuelve(tmp_path):
    visor = con_muchas_lineas(tmp_path)
    alto = visor._alto_stream()
    visor._tecla_extra("repag")
    assert visor.desplazamiento == alto - 1
    visor._tecla_extra("avpag")
    assert visor.desplazamiento == 0


def test_inicio_va_al_principio_del_buffer(tmp_path):
    visor = con_muchas_lineas(tmp_path)
    visor._tecla_extra("inicio")
    salida = pintar(visor)
    assert "linea 0" in salida
    assert visor.desplazamiento == 200 - visor._alto_stream()


def test_fin_vuelve_al_vivo(tmp_path):
    visor = con_muchas_lineas(tmp_path)
    visor._tecla_extra("inicio")
    visor._tecla_extra("fin")
    assert visor.desplazamiento == 0
    assert "linea 199" in pintar(visor)


def test_no_se_puede_pasar_de_los_limites(tmp_path):
    visor = con_muchas_lineas(tmp_path, cuantas=5)
    for _ in range(50):
        visor._tecla_extra("arriba")
    assert visor.desplazamiento == 0      # caben las 5: no hay nada arriba
    visor = con_muchas_lineas(tmp_path)
    for _ in range(500):
        visor._tecla_extra("arriba")
    assert visor.desplazamiento == 200 - visor._alto_stream()
    for _ in range(500):
        visor._tecla_extra("abajo")
    assert visor.desplazamiento == 0


def test_las_lineas_nuevas_no_mueven_la_vista(tmp_path):
    visor = con_muchas_lineas(tmp_path)
    visor._tecla_extra("arriba")
    visible_antes = pintar(visor)
    for i in range(5):
        rec = parsear_linea(linea("INFO", f"recien llegada {i}"))
        visor.estado.registrar(rec)
        visor._mostrar(rec)
    assert visor.desplazamiento == 6      # 1 + las 5 lineas nuevas
    assert "linea 198" in visible_antes
    assert "linea 198" in pintar(visor)   # sigue viendose lo mismo
    assert "recien llegada" not in pintar(visor)


def test_el_log_sigue_contando_mientras_se_navega(tmp_path):
    visor = con_muchas_lineas(tmp_path)
    visor._tecla_extra("inicio")
    rec = parsear_linea(linea("ERROR", "fallo mientras miro atras"))
    visor.estado.registrar(rec)
    visor._mostrar(rec)
    salida = pintar(visor)
    assert visor.estado.errores == 1
    assert "fallo mientras miro atras" in salida   # en el panel de errores
    assert "linea 0" in salida                     # la vista no se movio


def test_tecla_desconocida_no_hace_nada(tmp_path):
    visor = con_muchas_lineas(tmp_path)
    visor._tecla_extra("z")
    assert visor.desplazamiento == 0


# --- selector de archivo (tecla 'a') -----------------------------------------

def crear_log(carpeta, nombre, edad_seg=0.0):
    ruta = carpeta / nombre
    ruta.write_text("x\n", encoding="utf-8")
    if edad_seg:
        cuando = time.time() - edad_seg
        os.utime(ruta, (cuando, cuando))
    return ruta


@pytest.fixture
def con_dos_bots(tmp_path):
    """Carpeta compartida: el log de dos personas y nada mas."""
    visor = construir(tmp_path, lineas=[linea("INFO", "algo"),
                                        linea("ERROR", "un fallo")])
    (tmp_path / "log.txt").unlink()   # el que crea construir()
    crear_log(tmp_path, "Log_WPROFABRIC7RPA_CGRPA055_20260616.txt", edad_seg=30)
    crear_log(tmp_path, "Log_WPROFABRIC6RPA_CGRPA070_20260616.txt")
    return visor


def test_la_tecla_a_abre_el_selector(con_dos_bots):
    assert con_dos_bots._tecla_capturada("a") is True
    assert con_dos_bots.selector is not None
    salida = pintar(con_dos_bots)
    assert "ELEGIR LOG" in salida
    assert "WPROFABRIC6RPA" in salida and "WPROFABRIC7RPA" in salida
    assert "ELIGIENDO LOG" in salida
    assert "ACTIVO" in salida


def test_sin_el_selector_abierto_las_teclas_pasan_de_largo(con_dos_bots):
    assert con_dos_bots._tecla_capturada("q") is False
    assert con_dos_bots._tecla_capturada("arriba") is False


def test_con_el_selector_abierto_q_cancela_y_no_cierra(con_dos_bots):
    con_dos_bots._tecla_capturada("a")
    assert con_dos_bots._tecla_capturada("q") is True   # consumida
    assert con_dos_bots.selector is None
    assert "ELEGIR LOG" not in pintar(con_dos_bots)


def test_esc_cancela_sin_cambiar_nada(con_dos_bots):
    antes = con_dos_bots.seguidor.objetivo
    con_dos_bots._tecla_capturada("a")
    con_dos_bots._tecla_capturada("esc")
    assert con_dos_bots.selector is None
    assert con_dos_bots.seguidor.objetivo is antes


def test_las_flechas_mueven_la_seleccion(con_dos_bots):
    con_dos_bots._tecla_capturada("a")
    assert con_dos_bots.selector.indice == 0
    con_dos_bots._tecla_capturada("abajo")
    assert con_dos_bots.selector.indice == 1
    con_dos_bots._tecla_capturada("abajo")
    assert con_dos_bots.selector.indice == 1      # no se pasa del final
    con_dos_bots._tecla_capturada("arriba")
    con_dos_bots._tecla_capturada("arriba")
    assert con_dos_bots.selector.indice == 0      # ni del principio


def test_enter_fija_el_archivo_elegido(con_dos_bots):
    con_dos_bots._tecla_capturada("a")
    con_dos_bots._tecla_capturada("abajo")
    con_dos_bots._tecla_capturada("enter")

    objetivo = con_dos_bots.seguidor.objetivo
    assert isinstance(objetivo, ArchivoFijo)
    assert objetivo.nombre == "Log_WPROFABRIC7RPA_CGRPA055_20260616.txt"
    assert con_dos_bots.selector is None


def test_la_tecla_b_sigue_al_bot(con_dos_bots):
    con_dos_bots._tecla_capturada("a")
    con_dos_bots._tecla_capturada("b")

    objetivo = con_dos_bots.seguidor.objetivo
    assert isinstance(objetivo, PatronBot)
    assert objetivo.patron == "Log_WPROFABRIC6RPA_CGRPA070*"


def test_cambiar_de_log_no_mezcla_los_contadores(con_dos_bots):
    assert con_dos_bots.estado.errores == 1
    con_dos_bots._tecla_capturada("a")
    con_dos_bots._tecla_capturada("enter")

    assert con_dos_bots.estado.errores == 0
    assert con_dos_bots.estado.total == 0
    assert con_dos_bots.estado.bot_actual is None
    assert not con_dos_bots.estado.ultimos_errores
    assert con_dos_bots.desplazamiento == 0
    assert "Ahora sigue:" in pintar(con_dos_bots)


def test_el_objetivo_se_ve_en_la_cabecera(con_dos_bots):
    assert "mas reciente" in pintar(con_dos_bots)
    con_dos_bots._tecla_capturada("a")
    con_dos_bots._tecla_capturada("b")
    assert "bot WPROFABRIC6RPA CGRPA070" in pintar(con_dos_bots)


def test_selector_con_carpeta_vacia(tmp_path):
    visor = construir(tmp_path)
    (tmp_path / "log.txt").unlink()
    visor._tecla_capturada("a")
    salida = pintar(visor)
    assert "no hay ningun .txt" in salida
    visor._tecla_capturada("enter")          # no debe romper
    assert visor.selector is None


def test_selector_con_muchos_archivos_desplaza_la_ventana(tmp_path):
    for i in range(40):
        crear_log(tmp_path, f"Log_BOT{i:02d}_PROC_2026061{i % 10}.txt",
                  edad_seg=i * 10)
    visor = construir(tmp_path)
    visor._tecla_capturada("a")
    visor._tecla_capturada("fin")
    salida = pintar(visor)
    assert visor.selector.indice == len(visor.selector.disponibles) - 1
    assert len(salida.splitlines()) <= ALTO       # no desborda el layout
