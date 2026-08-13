#!/usr/bin/env python3
"""Genera un log RPA sintetico para probar o demostrar el panel de NANO.

Escribe lineas con el mismo formato que los logs reales sobre un archivo de
la carpeta indicada, al ritmo que se pida. Pensado para correr en una
segunda consola mientras NANO esta abierto en la primera.

Ejemplos:
    python scripts/simular_log.py                       # 5 lineas/s en ./logs
    python scripts/simular_log.py --ritmo 20 --errores 25
    python scripts/simular_log.py --lineas 200 --rotar
"""

from __future__ import annotations

import argparse
import random
import time
from datetime import datetime
from pathlib import Path

BOT = "NEON"
URL = "https://colsubsidio-2.my.automationanywhere.digital/"

ORIGENES = [
    "\\Bots\\GlobalFunctions\\HU00_DespliegueAmbiente",
    "\\Bots\\GlobalFunctions\\ConfigFunctions\\DepurarDirectoriosYArchivos",
    "\\Bots\\Facturacion\\GestionDeAutorizaciones\\MainRPAGestionDeMedicamentos",
    "\\Bots\\Facturacion\\GestionDeAutorizaciones\\Funciones\\EnviarCorreos",
    "\\Bots\\Facturacion\\GestionDeAutorizaciones\\Funciones\\GestionarTicketInsumo",
]

MENSAJES = {
    "INFO": [
        "Inicio HU HU00_DespliegueAmbiente",
        "Conexion a base de datos establecida",
        "Procesando autorizacion {n} del afiliado",
        "Se depuraran archivos anteriores a [{fecha}]",
        "Ticket {n} gestionado correctamente",
        "Fin Funcion GestionarTicketInsumo",
        "Depuracion iniciada parametros recibidos Ruta a depurar "
        "[\\\\192.168.50.169\\RPA_NEON_GestionAutorizaciones\\Audit\\Logs\\], "
        "Dias hacia atras [365], Recursiva [false]",
    ],
    "DEBUG": [
        "Parametros cargados: {n}",
        "No se encontraron registros a depurar Tabla: [[CensoUrgencias]]",
        "Respuesta del servicio en {n} ms",
    ],
    "WARNING": [
        "Uso de memoria al {n}%",
        "Reintento {n} de 5 en la consulta",
        "Cola con {n} elementos pendientes",
        "El elemento tardo {n} s en responder",
    ],
    "ERROR": [
        "Timeout conexion SAP tras {n} s",
        "Elemento no encontrado [btnGuardar]",
        "Elemento no encontrado [txtCedula]",
        "Fallo al procesar el lote {n}",
        "Fallo al guardar el acta de entrega",
    ],
}


def construir_linea(nivel: str, rng: random.Random) -> str:
    """Una linea con el formato exacto del log RPA real."""
    plantilla = rng.choice(MENSAJES[nivel])
    mensaje = plantilla.format(n=rng.randint(1, 999),
                               fecha=datetime.now().strftime("%m/%d/%y"))
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    return f"{ahora} | {nivel} | {mensaje} | {BOT} | {rng.choice(ORIGENES)} | {URL}\n"


def elegir_nivel(rng: random.Random, pct_error: int, pct_warning: int) -> str:
    tirada = rng.randint(1, 100)
    if tirada <= pct_error:
        return "ERROR"
    if tirada <= pct_error + pct_warning:
        return "WARNING"
    return "INFO" if rng.random() < 0.75 else "DEBUG"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("carpeta", nargs="?", default="logs",
                        help="Carpeta donde escribir (default: ./logs).")
    parser.add_argument("--ritmo", type=float, default=5.0,
                        help="Lineas por segundo (default: 5).")
    parser.add_argument("--lineas", type=int, default=0,
                        help="Cuantas lineas escribir. 0 = sin fin.")
    parser.add_argument("--errores", type=int, default=12, metavar="PCT",
                        help="Porcentaje de lineas ERROR (default: 12).")
    parser.add_argument("--warnings", type=int, default=10, metavar="PCT",
                        help="Porcentaje de lineas WARNING (default: 10).")
    parser.add_argument("--encoding", default="utf-8",
                        help="Encoding del archivo (prueba con cp1252).")
    parser.add_argument("--rotar", action="store_true",
                        help="Cada 100 lineas empieza un archivo nuevo.")
    parser.add_argument("--semilla", type=int, default=None,
                        help="Semilla aleatoria, para repetir la misma secuencia.")
    args = parser.parse_args()

    carpeta = Path(args.carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.semilla)
    espera = 1.0 / args.ritmo if args.ritmo > 0 else 0.0

    tanda = 0
    escritas = 0
    ruta = nueva_ruta(carpeta, tanda)
    print(f"Escribiendo en {ruta}  ({args.ritmo} l/s, {args.errores}% ERROR). "
          "Ctrl+C para parar.")

    try:
        while not args.lineas or escritas < args.lineas:
            if args.rotar and escritas and escritas % 100 == 0:
                tanda += 1
                ruta = nueva_ruta(carpeta, tanda)
                print(f"-- rotando a {ruta.name} --")
            nivel = elegir_nivel(rng, args.errores, args.warnings)
            with open(ruta, "a", encoding=args.encoding, errors="replace") as fh:
                fh.write(construir_linea(nivel, rng))
            escritas += 1
            if espera:
                time.sleep(espera)
    except KeyboardInterrupt:
        pass

    print(f"\n{escritas} lineas escritas en {ruta}.")
    return 0


def nueva_ruta(carpeta: Path, tanda: int) -> Path:
    marca = datetime.now().strftime("%Y%m%d")
    sufijo = f"_{tanda}" if tanda else ""
    return carpeta / f"prueba_WPROFABRIC6RPA_{marca}{sufijo}.txt"


if __name__ == "__main__":
    raise SystemExit(main())
