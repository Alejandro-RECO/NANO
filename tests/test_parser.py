"""Tests del parseo de lineas de log."""

from datetime import datetime

import pytest

from nano.core.parser import detectar_fecha, detectar_nivel, parsear_linea

RPA = ("16/06/2026 14:09:19 | INFO | Inicio HU HU00 | NEON | "
       "\\Bots\\Config\\Depurar | https://ejemplo.local/")


def test_formato_rpa_completo():
    rec = parsear_linea(RPA + "\n")
    assert rec.nivel == "INFO"
    assert rec.ts == datetime(2026, 6, 16, 14, 9, 19)
    assert rec.mensaje == "Inicio HU HU00"
    assert rec.bot == "NEON"
    assert rec.origen == "\\Bots\\Config\\Depurar"
    assert rec.url == "https://ejemplo.local/"
    assert rec.origen_corto == "Depurar"
    assert rec.crudo == RPA  # sin el salto de linea


def test_mensaje_con_barra_interna_no_desplaza_los_campos():
    linea = ("16/06/2026 14:09:19 | ERROR | fallo A | reintento B | NEON | "
             "MainProceso | https://ejemplo.local/")
    rec = parsear_linea(linea)
    assert rec.mensaje == "fallo A | reintento B"
    assert rec.bot == "NEON"
    assert rec.origen == "MainProceso"
    assert rec.url == "https://ejemplo.local/"


def test_formato_simple_sin_barras():
    rec = parsear_linea("2026-06-17 09:01:00 ERROR Prueba en vivo\n")
    assert rec.nivel == "ERROR"
    assert rec.ts == datetime(2026, 6, 17, 9, 1, 0)
    assert rec.mensaje == "Prueba en vivo"
    assert rec.bot is None


@pytest.mark.parametrize("texto,esperado", [
    ("| CRITICAL | x |", "ERROR"),
    ("| FATAL | x |", "ERROR"),
    ("| WARN | x |", "WARNING"),
    ("| warning | x |", "WARNING"),
    ("2026-06-17 09:01:00 TRACE algo", "DEBUG"),
    ("2026-06-17 09:01:00 debug algo", "DEBUG"),
])
def test_alias_de_nivel(texto, esperado):
    assert detectar_nivel(texto) == esperado


@pytest.mark.parametrize("texto", [
    "",
    "   ",
    "linea suelta sin formato",
    "| NOSEQUE | mensaje | BOT |",
    "16/06/2026 14:09:19 | | vacio | BOT |",
])
def test_lineas_sin_nivel_no_lanzan(texto):
    rec = parsear_linea(texto)
    assert rec.nivel is None
    assert rec.crudo == texto


def test_linea_sin_formato_conserva_el_texto_como_mensaje():
    rec = parsear_linea("algo que no es un log\n")
    assert rec.mensaje == "algo que no es un log"


def test_fecha_invalida_devuelve_none():
    assert detectar_fecha("99/99/9999 99:99:99 | INFO | x") is None
    assert detectar_fecha("sin fecha") is None


def test_origen_corto_sin_origen():
    assert parsear_linea("texto").origen_corto == ""


def test_campos_conserva_el_split_crudo():
    rec = parsear_linea("a | b | c\n")
    assert rec.campos == ["a ", " b ", " c"]
