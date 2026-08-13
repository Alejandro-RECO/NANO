"""Tests del menu de seleccion de log."""

import os
import time

import pytest

from nano.core.catalogo import ArchivoFijo, MasReciente, PatronBot, listar_logs
from nano.ui.menu import elegir_archivo, interpretar_opcion
from nano.ui.temas import TEMAS

TEMA = TEMAS["neon"]
MIO = "Log_WPROFABRIC6RPA_CGRPA070_20260616.txt"
SUYO = "Log_WPROFABRIC7RPA_CGRPA055_20260616.txt"


def crear(carpeta, nombre, edad_seg=0.0):
    ruta = carpeta / nombre
    ruta.write_text("x\n", encoding="utf-8")
    if edad_seg:
        cuando = time.time() - edad_seg
        os.utime(ruta, (cuando, cuando))
    return ruta


@pytest.fixture
def carpeta_compartida(tmp_path):
    crear(tmp_path, SUYO, edad_seg=30)
    crear(tmp_path, MIO)
    return tmp_path


@pytest.fixture
def con_tty(monkeypatch):
    """Finge una terminal interactiva para que el menu se muestre."""
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)


def responder(monkeypatch, *respuestas):
    cola = list(respuestas)
    monkeypatch.setattr("builtins.input", lambda *_: cola.pop(0))


# --- interpretacion de lo tecleado -------------------------------------------

@pytest.fixture
def disponibles(carpeta_compartida):
    return listar_logs(carpeta_compartida)


def test_numero_elige_archivo_exacto(disponibles):
    objetivo = interpretar_opcion("1", disponibles)
    assert isinstance(objetivo, ArchivoFijo)
    assert objetivo.nombre == MIO


def test_numero_con_b_elige_al_bot(disponibles):
    objetivo = interpretar_opcion("1b", disponibles)
    assert isinstance(objetivo, PatronBot)
    assert objetivo.patron == "Log_WPROFABRIC6RPA_CGRPA070*"
    assert objetivo.descripcion == "bot WPROFABRIC6RPA CGRPA070"


def test_la_b_vale_delante_o_detras(disponibles):
    assert interpretar_opcion("b2", disponibles).patron == \
           interpretar_opcion("2b", disponibles).patron


@pytest.mark.parametrize("sel", ["", "0", "3", "99", "x", "bb", "-1", "1.5"])
def test_opciones_invalidas(sel, disponibles):
    assert interpretar_opcion(sel, disponibles) is None


# --- cuando pregunta y cuando no ---------------------------------------------

def test_pregunta_con_varios_archivos(carpeta_compartida, con_tty, monkeypatch):
    responder(monkeypatch, "2")
    objetivo = elegir_archivo(carpeta_compartida, TEMA)
    assert isinstance(objetivo, ArchivoFijo)
    assert objetivo.nombre == SUYO


def test_enter_deja_el_comportamiento_de_siempre(carpeta_compartida, con_tty,
                                                 monkeypatch):
    responder(monkeypatch, "")
    assert isinstance(elegir_archivo(carpeta_compartida, TEMA), MasReciente)


def test_con_un_solo_archivo_no_pregunta(tmp_path, con_tty, monkeypatch):
    crear(tmp_path, MIO)
    monkeypatch.setattr("builtins.input", _no_preguntar)
    assert isinstance(elegir_archivo(tmp_path, TEMA), MasReciente)


def test_elegir_fuerza_el_menu_con_un_solo_archivo(tmp_path, con_tty,
                                                   monkeypatch):
    crear(tmp_path, MIO)
    responder(monkeypatch, "1")
    objetivo = elegir_archivo(tmp_path, TEMA, forzar=True)
    assert isinstance(objetivo, ArchivoFijo)


def test_sin_tty_no_pregunta(carpeta_compartida, monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("builtins.input", _no_preguntar)
    assert isinstance(elegir_archivo(carpeta_compartida, TEMA), MasReciente)


def test_carpeta_vacia_no_pregunta(tmp_path, con_tty, monkeypatch):
    monkeypatch.setattr("builtins.input", _no_preguntar)
    assert isinstance(elegir_archivo(tmp_path, TEMA, forzar=True), MasReciente)


def test_los_flags_saltan_el_menu(carpeta_compartida, con_tty, monkeypatch):
    monkeypatch.setattr("builtins.input", _no_preguntar)

    objetivo = elegir_archivo(carpeta_compartida, TEMA, archivo=MIO)
    assert isinstance(objetivo, ArchivoFijo) and objetivo.nombre == MIO

    objetivo = elegir_archivo(carpeta_compartida, TEMA, archivo="Log_WPRO*")
    assert isinstance(objetivo, PatronBot)

    objetivo = elegir_archivo(carpeta_compartida, TEMA, bot="WPROFABRIC6RPA")
    assert objetivo.resolver(carpeta_compartida) == str(carpeta_compartida / MIO)


def test_reintenta_ante_entrada_invalida(carpeta_compartida, con_tty,
                                         monkeypatch):
    responder(monkeypatch, "zzz", "1")
    objetivo = elegir_archivo(carpeta_compartida, TEMA)
    assert isinstance(objetivo, ArchivoFijo) and objetivo.nombre == MIO


def test_tras_varios_fallos_usa_el_mas_reciente(carpeta_compartida, con_tty,
                                                monkeypatch):
    responder(monkeypatch, "no", "tampoco", "nada")
    assert isinstance(elegir_archivo(carpeta_compartida, TEMA), MasReciente)


def test_ctrl_c_en_el_menu_no_rompe(carpeta_compartida, con_tty, monkeypatch):
    def interrumpir(*_):
        raise KeyboardInterrupt
    monkeypatch.setattr("builtins.input", interrumpir)
    assert isinstance(elegir_archivo(carpeta_compartida, TEMA), MasReciente)


def test_el_listado_sale_por_pantalla(carpeta_compartida, con_tty, monkeypatch,
                                      capsys):
    responder(monkeypatch, "1")
    elegir_archivo(carpeta_compartida, TEMA)
    salida = capsys.readouterr().out
    assert "Elige el log a seguir" in salida
    assert "WPROFABRIC6RPA" in salida and "WPROFABRIC7RPA" in salida
    assert "CGRPA070" in salida
    assert "ACTIVO" in salida
    assert MIO in salida
    assert "Siguiendo: solo " + MIO in salida


def _no_preguntar(*_):
    raise AssertionError("no deberia haber preguntado")
