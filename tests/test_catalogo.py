"""Tests del inventario de logs y de las estrategias de seleccion."""

import os
import time

import pytest

from nano import config
from nano.core.catalogo import (
    SIN_DATO,
    ArchivoFijo,
    MasReciente,
    PatronBot,
    listar_logs,
    objetivo_de_bot,
    objetivo_desde_texto,
    partes_del_nombre,
    patron_de_bot,
    rutas_txt,
)

REAL = "Log_WPROFABRIC6RPA_CGRPA070_20260616.txt"


def crear(carpeta, nombre, edad_seg=0.0, texto="x\n"):
    """Crea un .txt con una antiguedad concreta y devuelve su ruta."""
    ruta = carpeta / nombre
    ruta.write_text(texto, encoding="utf-8")
    if edad_seg:
        cuando = time.time() - edad_seg
        os.utime(ruta, (cuando, cuando))
    return ruta


# --- lectura del nombre ------------------------------------------------------

@pytest.mark.parametrize("nombre,esperado", [
    (REAL, ("WPROFABRIC6RPA", "CGRPA070")),
    ("Log_WPROFABRIC7RPA_CGRPA055_20260616.txt", ("WPROFABRIC7RPA", "CGRPA055")),
    ("WPROFABRIC6RPA_CGRPA070_20260616.txt", ("WPROFABRIC6RPA", "CGRPA070")),
    ("Log_SOLOBOT_20260616.txt", ("SOLOBOT", SIN_DATO)),
    ("Log_BOT_PROC_EXTRA_20260616.txt", ("BOT", "PROC_EXTRA")),
    ("cualquiera.txt", ("cualquiera", SIN_DATO)),
    ("Log_20260616.txt", (SIN_DATO, SIN_DATO)),
    (".txt", (SIN_DATO, SIN_DATO)),
])
def test_partes_del_nombre(nombre, esperado):
    assert partes_del_nombre(nombre) == esperado


@pytest.mark.parametrize("nombre,esperado", [
    (REAL, "Log_WPROFABRIC6RPA_CGRPA070*"),
    ("Log_WPROFABRIC6RPA_CGRPA070_20260617.txt", "Log_WPROFABRIC6RPA_CGRPA070*"),
    ("Log_BOT_20260616_2.txt", "Log_BOT*"),
    # Sin tramo variable que quitar, el patron es el nombre entero: elegir
    # "el bot" acaba siendo lo mismo que fijar el archivo.
    ("salida.txt", "salida.txt"),
    ("Log_BOT_PROC.txt", "Log_BOT_PROC.txt"),
])
def test_patron_de_bot(nombre, esperado):
    assert patron_de_bot(nombre) == esperado


def test_dos_dias_del_mismo_bot_comparten_patron():
    ayer = "Log_WPROFABRIC6RPA_CGRPA070_20260615.txt"
    assert patron_de_bot(REAL) == patron_de_bot(ayer)


# --- inventario --------------------------------------------------------------

def test_listar_ordena_del_mas_reciente_al_mas_viejo(tmp_path):
    crear(tmp_path, "viejo.txt", edad_seg=500)
    crear(tmp_path, "medio.txt", edad_seg=100)
    crear(tmp_path, "nuevo.txt")
    assert [d.nombre for d in listar_logs(tmp_path)] == [
        "nuevo.txt", "medio.txt", "viejo.txt"]


def test_marca_de_activo(tmp_path):
    crear(tmp_path, "corriendo.txt")
    crear(tmp_path, "de_ayer.txt", edad_seg=config.UMBRAL_ACTIVO + 60)
    activos = {d.nombre: d.activo for d in listar_logs(tmp_path)}
    assert activos == {"corriendo.txt": True, "de_ayer.txt": False}


def test_listar_expone_bot_proceso_y_patron(tmp_path):
    crear(tmp_path, REAL)
    log = listar_logs(tmp_path)[0]
    assert (log.bot, log.proceso) == ("WPROFABRIC6RPA", "CGRPA070")
    assert log.patron == "Log_WPROFABRIC6RPA_CGRPA070*"
    assert log.ruta == str(tmp_path / REAL)


def test_carpeta_vacia_o_inexistente(tmp_path):
    assert listar_logs(tmp_path) == []
    assert listar_logs(tmp_path / "no-existe") == []
    assert rutas_txt(tmp_path / "no-existe") == []


def test_solo_se_listan_txt(tmp_path):
    crear(tmp_path, "log.txt")
    (tmp_path / "datos.csv").write_text("no soy log", encoding="utf-8")
    assert [d.nombre for d in listar_logs(tmp_path)] == ["log.txt"]


# --- objetivos ---------------------------------------------------------------

def test_mas_reciente_es_el_comportamiento_de_siempre(tmp_path):
    crear(tmp_path, "a.txt", edad_seg=100)
    crear(tmp_path, "b.txt")
    assert MasReciente().resolver(tmp_path) == str(tmp_path / "b.txt")


def test_mas_reciente_sin_archivos(tmp_path):
    assert MasReciente().resolver(tmp_path) is None


def test_archivo_fijo_ignora_a_los_demas(tmp_path):
    crear(tmp_path, "mio.txt", edad_seg=500)
    crear(tmp_path, "del_companero.txt")  # mas reciente
    objetivo = ArchivoFijo("mio.txt")
    assert objetivo.resolver(tmp_path) == str(tmp_path / "mio.txt")


def test_archivo_fijo_que_aun_no_existe(tmp_path):
    objetivo = ArchivoFijo("todavia_no.txt")
    assert objetivo.resolver(tmp_path) is None
    crear(tmp_path, "todavia_no.txt")
    assert objetivo.resolver(tmp_path) == str(tmp_path / "todavia_no.txt")


def test_archivo_fijo_acepta_una_ruta_completa(tmp_path):
    crear(tmp_path, "mio.txt")
    objetivo = ArchivoFijo(str(tmp_path / "mio.txt"))
    assert objetivo.resolver(tmp_path) == str(tmp_path / "mio.txt")


def test_patron_sigue_al_bot_entre_dias(tmp_path):
    crear(tmp_path, "Log_WPROFABRIC6RPA_CGRPA070_20260615.txt", edad_seg=500)
    crear(tmp_path, "Log_WPROFABRIC7RPA_CGRPA055_20260616.txt")  # otro bot
    objetivo = PatronBot(patron_de_bot(REAL))

    ayer = str(tmp_path / "Log_WPROFABRIC6RPA_CGRPA070_20260615.txt")
    assert objetivo.resolver(tmp_path) == ayer   # ignora al companero

    hoy = crear(tmp_path, REAL)                  # aparece el log de hoy
    assert objetivo.resolver(tmp_path) == str(hoy)


def test_patron_sin_coincidencias(tmp_path):
    crear(tmp_path, "otra_cosa.txt")
    assert PatronBot("Log_NADIE*").resolver(tmp_path) is None


def test_descripciones_para_la_cabecera():
    assert MasReciente().descripcion == "mas reciente"
    assert ArchivoFijo("x.txt").descripcion == "fijado"
    assert PatronBot("Log_BOT_PROC*").descripcion == "bot Log_BOT_PROC"
    assert objetivo_de_bot("WPROFABRIC6RPA").descripcion == "bot WPROFABRIC6RPA"


def test_objetivo_desde_texto_distingue_patron_de_archivo():
    assert isinstance(objetivo_desde_texto(REAL), ArchivoFijo)
    assert isinstance(objetivo_desde_texto("Log_WPRO*"), PatronBot)
    assert isinstance(objetivo_desde_texto("Log_?.txt"), PatronBot)


def test_objetivo_de_bot_casa_por_texto_contenido(tmp_path):
    crear(tmp_path, REAL)
    crear(tmp_path, "Log_WPROFABRIC7RPA_CGRPA055_20260616.txt", edad_seg=10)
    assert objetivo_de_bot("FABRIC6").resolver(tmp_path) == str(tmp_path / REAL)
