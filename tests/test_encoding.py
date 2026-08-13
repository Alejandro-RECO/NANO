"""Tests de deteccion de encoding."""

import codecs

from nano.core.encoding import detectar_encoding

TEXTO = "16/06/2026 14:09:19 | INFO | Depuracion del niño con acentos ó á | NEON\n"


def escribir(tmp_path, nombre, datos: bytes):
    ruta = tmp_path / nombre
    ruta.write_bytes(datos)
    return ruta


def test_utf8_sin_bom(tmp_path):
    ruta = escribir(tmp_path, "u.txt", TEXTO.encode("utf-8"))
    assert detectar_encoding(ruta) == "utf-8"


def test_utf8_con_bom(tmp_path):
    ruta = escribir(tmp_path, "b.txt", codecs.BOM_UTF8 + TEXTO.encode("utf-8"))
    assert detectar_encoding(ruta) == "utf-8-sig"


def test_cp1252(tmp_path):
    ruta = escribir(tmp_path, "c.txt", TEXTO.encode("cp1252"))
    assert detectar_encoding(ruta) == "cp1252"


def test_ascii_puro_se_trata_como_utf8(tmp_path):
    ruta = escribir(tmp_path, "a.txt", b"solo ascii\n")
    assert detectar_encoding(ruta) == "utf-8"


def test_encoding_forzado_gana(tmp_path):
    ruta = escribir(tmp_path, "f.txt", TEXTO.encode("utf-8"))
    assert detectar_encoding(ruta, "cp1252") == "cp1252"


def test_multibyte_cortado_al_final_de_la_muestra(tmp_path, monkeypatch):
    """Un caracter partido por el limite de la muestra no debe forzar cp1252."""
    from nano import config
    monkeypatch.setattr(config, "MUESTRA_ENCODING", 9)
    # 8 bytes ascii + 'ñ' (2 bytes en UTF-8): la muestra corta la 'ñ' a la mitad.
    ruta = escribir(tmp_path, "m.txt", b"12345678" + "ñ".encode("utf-8"))
    assert detectar_encoding(ruta) == "utf-8"


def test_archivo_inexistente_no_lanza(tmp_path):
    assert detectar_encoding(tmp_path / "no-existe.txt") == "cp1252"
