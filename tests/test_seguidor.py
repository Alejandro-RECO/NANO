"""Tests del seguimiento incremental de archivos."""

import os
import time

from nano.core.seguidor import Seguidor, txt_mas_reciente


def escribir(ruta, texto, modo="a", encoding="utf-8"):
    with open(ruta, modo, encoding=encoding, newline="") as fh:
        fh.write(texto)


def test_carpeta_vacia_o_inexistente(tmp_path):
    assert txt_mas_reciente(tmp_path) is None
    assert txt_mas_reciente(tmp_path / "no-existe") is None
    assert Seguidor(tmp_path).leer_nuevas() == []


def test_lee_solo_lo_nuevo(tmp_path):
    log = tmp_path / "a.txt"
    escribir(log, "uno\ndos\n")
    seg = Seguidor(tmp_path)

    assert seg.leer_nuevas() == ["uno\n", "dos\n"]
    assert seg.leer_nuevas() == []

    escribir(log, "tres\n")
    assert seg.leer_nuevas() == ["tres\n"]


def test_tail_ignora_lo_ya_escrito(tmp_path):
    log = tmp_path / "a.txt"
    escribir(log, "viejo\n")
    seg = Seguidor(tmp_path, desde_el_final=True)

    assert seg.leer_nuevas() == []
    escribir(log, "nuevo\n")
    assert seg.leer_nuevas() == ["nuevo\n"]


def test_linea_incompleta_se_completa_despues(tmp_path):
    log = tmp_path / "a.txt"
    escribir(log, "mitad")
    seg = Seguidor(tmp_path)

    assert seg.leer_nuevas() == []          # aun no hay salto de linea
    escribir(log, " y mitad\n")
    assert seg.leer_nuevas() == ["mitad y mitad\n"]


def test_ultima_linea_sin_salto_acaba_emitiendose(tmp_path):
    log = tmp_path / "a.txt"
    escribir(log, "sin salto")
    seg = Seguidor(tmp_path)

    assert seg.leer_nuevas() == []
    assert seg.leer_nuevas() == []          # primer intento en vacio
    assert seg.leer_nuevas() == ["sin salto\n"]


def test_multibyte_partido_entre_lecturas(tmp_path):
    log = tmp_path / "a.txt"
    crudo = "niño\n".encode("utf-8")
    with open(log, "wb") as fh:
        fh.write(crudo[:3])                 # corta la 'ñ' por la mitad
    seg = Seguidor(tmp_path)
    assert seg.leer_nuevas() == []
    with open(log, "ab") as fh:
        fh.write(crudo[3:])
    assert seg.leer_nuevas() == ["niño\n"]


def test_cp1252_con_acentos(tmp_path):
    log = tmp_path / "a.txt"
    with open(log, "wb") as fh:
        fh.write("Depuración\n".encode("cp1252"))
    seg = Seguidor(tmp_path)
    assert seg.leer_nuevas() == ["Depuración\n"]
    assert seg.encoding == "cp1252"


def test_truncado_relee_desde_el_inicio(tmp_path):
    log = tmp_path / "a.txt"
    escribir(log, "uno\ndos\ntres\n")
    seg = Seguidor(tmp_path)
    seg.leer_nuevas()

    escribir(log, "nuevo\n", modo="w")      # el archivo encoge
    assert seg.leer_nuevas() == ["nuevo\n"]
    assert seg.hubo_rotacion is True
    assert seg.hubo_rotacion is False       # la senal se consume


def test_cambia_al_txt_mas_reciente(tmp_path):
    viejo = tmp_path / "viejo.txt"
    escribir(viejo, "linea vieja\n")
    seg = Seguidor(tmp_path)
    assert seg.leer_nuevas() == ["linea vieja\n"]
    assert seg.hubo_cambio_de_archivo is True
    assert seg.hubo_cambio_de_archivo is False

    nuevo = tmp_path / "nuevo.txt"
    escribir(nuevo, "linea nueva\n")
    os.utime(nuevo, (time.time() + 10, time.time() + 10))

    assert seg.leer_nuevas() == ["linea nueva\n"]
    assert seg.nombre_archivo == "nuevo.txt"
    assert seg.hubo_cambio_de_archivo is True


def test_ignora_archivos_que_no_son_txt(tmp_path):
    escribir(tmp_path / "datos.csv", "no soy un log\n")
    assert txt_mas_reciente(tmp_path) is None
