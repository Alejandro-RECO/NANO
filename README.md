# NANO

Visor de **logs en consola en tiempo real** con colores. Vigila una carpeta,
sigue (tail) el archivo `.txt` más reciente y muestra las líneas nuevas a
medida que otros procesos las escriben — **sin abrir y cerrar el archivo**.

Los colores se aplican según el nivel detectado en cada línea:

| Nivel                     | Color    |
|---------------------------|----------|
| `ERROR` / `CRITICAL` / `FATAL` | Rojo     |
| `WARN` / `WARNING`        | Amarillo |
| `INFO`                    | Verde    |
| `DEBUG` / `TRACE`         | Cian     |
| (otro)                    | Blanco   |

## Requisitos

- Python 3.8+
- [colorama](https://pypi.org/project/colorama/)

```bash
pip install -r requirements.txt
```

## Uso

```bash
# Vigila ./logs y sigue el .txt mas reciente
python log_viewer.py

# Vigila otra carpeta
python log_viewer.py "C:\ruta\a\mis\logs"
```

### Opciones

| Opción              | Descripción                                          |
|---------------------|------------------------------------------------------|
| `-f`, `--filter X`  | Muestra solo líneas que contengan `X` (ej: `ERROR`). |
| `-t`, `--timestamp` | Antepone la hora a cada línea.                       |
| `-s`, `--save A.txt`| Guarda también la salida mostrada en `A.txt`.        |
| `--tail`            | Empieza al final del archivo (ignora lo ya escrito). |

En Windows, presiona **`p`** para pausar/reanudar y **`Ctrl+C`** para salir.

### Ejemplos

```bash
# Solo errores, con hora
python log_viewer.py logs -f ERROR -t

# Seguir desde el final y guardar copia
python log_viewer.py logs --tail -s salida.txt
```

## Cómo funciona

El script revisa cada ~0.3 s el tamaño del archivo y lee únicamente los bytes
nuevos desde la última posición leída (`seek`). Detecta:

- **Rotación / truncado**: si el archivo encoge, reinicia desde el principio.
- **Archivo nuevo**: si aparece un `.txt` más reciente, cambia a seguirlo.

## Prueba rápida

Con el visor corriendo (`python log_viewer.py`), en otra consola agrega líneas
al sample para verlas aparecer en vivo:

```powershell
Add-Content logs\sample.txt "2026-06-17 09:01:00 ERROR Prueba en vivo"
```
