#!/usr/bin/env python3
"""Genera un log RPA sintetico para probar o demostrar el panel de NANO.

Escribe lineas con el mismo formato que los logs reales sobre un archivo de
la carpeta indicada, al ritmo que se pida. Pensado para correr en una
segunda consola mientras NANO esta abierto en la primera.

Con --bots escribe varios logs a la vez, uno por bot, para reproducir la
carpeta compartida entre varias personas y probar el selector de archivo.

Ejemplos:
    python scripts/simular_log.py                       # 5 lineas/s en ./logs
    python scripts/simular_log.py --ritmo 20 --errores 25
    python scripts/simular_log.py --lineas 200 --rotar
    python scripts/simular_log.py --bots WPROFABRIC6RPA,WPROFABRIC7RPA
"""

from __future__ import annotations

import argparse
import random
import time
from datetime import datetime
from pathlib import Path

BOT = "NEON"
URL = "https://colsubsidio-2.my.automationanywhere.digital/"

#: Bot por defecto, con el mismo formato de nombre que los logs reales.
BOTS_POR_DEFECTO = "WPROFABRIC6RPA:CGRPA070"

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


def parsear_bots(texto: str) -> list[tuple[str, str]]:
    """'BOT1:PROC1,BOT2' -> [('BOT1', 'PROC1'), ('BOT2', 'CGRPA001')]."""
    bots = []
    for i, tramo in enumerate(t.strip() for t in texto.split(",") if t.strip()):
        if ":" in tramo:
            nombre, proceso = tramo.split(":", 1)
        else:
            nombre, proceso = tramo, f"CGRPA{i:03d}"
        bots.append((nombre, proceso))
    return bots or parsear_bots(BOTS_POR_DEFECTO)


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
    parser.add_argument("--bots", default=BOTS_POR_DEFECTO,
                        help="Bots que escriben a la vez, separados por comas "
                             "(ej: WPROFABRIC6RPA,WPROFABRIC7RPA). Cada uno "
                             "escribe su propio .txt en la misma carpeta.")
    args = parser.parse_args()

    carpeta = Path(args.carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.semilla)
    espera = 1.0 / args.ritmo if args.ritmo > 0 else 0.0

    bots = parsear_bots(args.bots)
    tanda = 0
    escritas = 0
    rutas = [nueva_ruta(carpeta, bot, proceso, tanda) for bot, proceso in bots]
    print(f"Escribiendo {len(rutas)} log(s) en {carpeta}  "
          f"({args.ritmo} l/s, {args.errores}% ERROR). Ctrl+C para parar.")
    for ruta in rutas:
        print(f"  - {ruta.name}")

    try:
        while not args.lineas or escritas < args.lineas:
            if args.rotar and escritas and escritas % 100 == 0:
                tanda += 1
                rutas = [nueva_ruta(carpeta, bot, proceso, tanda)
                         for bot, proceso in bots]
                print(f"-- rotando a la tanda {tanda} --")
            # Cada linea va a un bot al azar: asi los archivos se turnan y se
            # ve el problema de "el mas reciente cambia solo".
            ruta = rng.choice(rutas)
            nivel = elegir_nivel(rng, args.errores, args.warnings)
            with open(ruta, "a", encoding=args.encoding, errors="replace") as fh:
                fh.write(construir_linea(nivel, rng))
            escritas += 1
            if espera:
                time.sleep(espera)
    except KeyboardInterrupt:
        pass

    print(f"\n{escritas} lineas escritas en {carpeta}.")
    return 0


def nueva_ruta(carpeta: Path, bot: str, proceso: str, tanda: int) -> Path:
    marca = datetime.now().strftime("%Y%m%d")
    sufijo = f"_{tanda}" if tanda else ""
    return carpeta / f"Log_{bot}_{proceso}_{marca}{sufijo}.txt"


if __name__ == "__main__":
    raise SystemExit(main())
