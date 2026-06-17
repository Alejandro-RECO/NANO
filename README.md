# NANO

Visor de **logs en consola en tiempo real** con colores. Vigila una carpeta,
sigue (tail) el archivo `.txt` más reciente y muestra las líneas nuevas a
medida que otros procesos las escriben — **sin abrir y cerrar el archivo**.

La **fecha se muestra en el color de fecha del tema**; el **nivel y su mensaje**
se pintan del color del nivel. Formato soportado:
`DD/MM/YYYY HH:MM:SS | NIVEL | mensaje | ...` (log real) y
`YYYY-MM-DD HH:MM:SS NIVEL mensaje`.

Niveles reconocidos: `ERROR`/`CRITICAL`/`FATAL`, `WARNING`/`WARN`, `INFO`,
`DEBUG`/`TRACE`. Las líneas sin nivel se muestran en el color de fecha.

### Temas de color (color verdadero 24-bit)

Al arrancar se elige el tema con un menú (Enter = **Neon**, por defecto).
También se puede fijar sin menú con `--theme`:

| Tema     | Estilo                              |
|----------|-------------------------------------|
| `neon`   | Colores neón vivos (por defecto)    |
| `tokyo`  | Paleta Tokyo Night                  |
| `pastel` | Tonos pastel suaves                 |

```bash
python log_viewer.py --theme tokyo     # salta el menu
python log_viewer.py                    # pregunta el tema al arrancar
```

## Requisitos

- Python 3.8+ (único requisito; lo demás se instala solo)

## Correr en cualquier máquina (solo descargar el repo)

El iniciador crea un entorno virtual local (`.venv`), instala las
dependencias e inicia el visor. **No ensucia el Python global ni necesita
permisos de administrador.** Solo clona/descarga y ejecuta:

```bash
git clone <url-del-repo> NANO
cd NANO
```

Luego, según tu sistema:

| Sistema           | Comando                          |
|-------------------|----------------------------------|
| Windows (CMD / doble-clic) | `iniciar.bat`           |
| Windows (PowerShell)       | `.\iniciar.ps1`         |
| Linux / macOS              | `chmod +x iniciar.sh && ./iniciar.sh` |

La primera vez tarda un poco (crea el `.venv` e instala). Las siguientes
arranca al instante. Cualquier opción del visor se puede pasar al iniciador,
ej.: `iniciar.bat logs -f ERROR -t`.

### Instalación manual (alternativa)

```bash
pip install -r requirements.txt
python log_viewer.py
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
| `--theme T`         | Tema de color: `neon`, `tokyo` o `pastel` (sin menú). |

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
