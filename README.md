# NANO

**Panel de control de logs RPA en consola, en tiempo real.** Vigila una carpeta,
sigue (tail) el archivo `.txt` más reciente y muestra las líneas nuevas a medida
que el bot las escribe — **sin abrir y cerrar el archivo**.

A diferencia de un `tail` normal, NANO no deja que un error se pierda al
desplazarse la pantalla: **lo cuenta, lo guarda en su propio panel y agrupa los
repetidos**.

```
╭─ NANO ──────────────────────────────────────────────────────────────────────────────────────────────────╮
│ Log_WPROFABRIC6RPA_CGRPA070_20260616.txt  ·  utf-8                                             BOT NEON │
│ HU  GestionarTicketInsumo                                         00:13:46  ▸ 20.0 l/s  ·  ult 14:23:05 │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ 14:11:02 ERROR   Timeout conexión SAP tras 45 s                                    MainRPAGestionDeMed… │
│ 14:11:40 WARNING Cola con 340 elementos pendientes                                 GestionarTicketInsu… │
│ 14:12:47 ERROR   Elemento no encontrado [btnGuardar]                                      EnviarCorreos │
│ 14:13:05 DEBUG   No se encontraron registros a depurar Tabla: [[CensoUrgencias]]   HU00_DespliegueAmbi… │
│ 14:15:10 ERROR   Elemento no encontrado [txtCedula]                                       EnviarCorreos │
│ 14:16:22 INFO    Procesando autorización 4821 del afiliado                         MainRPAGestionDeMed… │
│ 14:17:03 WARNING Reintento 3 de 5 en la consulta                                   MainRPAGestionDeMed… │
│ 14:18:33 ERROR   Fallo al guardar el acta de entrega                               MainRPAGestionDeMed… │
│ 14:23:05 INFO    Ticket 99213 gestionado correctamente                             GestionarTicketInsu… │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ RESUMEN ────────────╮╭─ ULTIMOS ERRORES ─────────────────────╮╭─ ULTIMOS WARNING ──────────────────────╮
│ ERROR              5 ││ 14:18:33 Fallo al guardar el acta de… ││ 14:17:03 Reintento 3 de 5 en la consu… │
│ WARNING            3 ││ 14:15:10 Elemento no encontrado [txt… ││ 14:11:40 Cola con 340 elementos pendi… │
│ INFO              10 ││ 14:12:47 Elemento no encontrado [btn… ││ 14:09:34 Uso de memoria al 82%  · Mon… │
│ DEBUG              2 ││ 14:11:02 Timeout conexión SAP tras 4… ││                                        │
│                      ││ 14:09:36 Timeout conexión SAP tras 3… ││                                        │
│ total             20 ││                                       ││                                        │
╰──────────────────────╯╰───────────────────────────────────────╯╰────────────────────────────────────────╯
╭─ TOP ERRORES ───────────────────────────────────────────────────────────────────────────────────────────╮
│ ×2 Timeout conexión SAP tras # s   ·   ×2 Elemento no encontrado [...]   ·   ×1 Fallo al guardar el ac… │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────╯
 p  pausa    c  limpiar    q  salir                                                               EN VIVO ●
```

## Qué muestra cada zona

| Zona | Contenido |
|------|-----------|
| **Cabecera** | Archivo seguido y su encoding, bot, HU/función en curso, duración del log, ritmo en líneas/s y hora de la última línea. |
| **Stream** | Las últimas líneas del log: hora, nivel, mensaje y origen. Se omite la URL del Control Room (es idéntica en todas) y la ruta del bot se recorta a su último tramo. |
| **RESUMEN** | Contadores por nivel y total. **El borde se pone rojo en cuanto hay un ERROR**, para verlo sin leer los números. |
| **ÚLTIMOS ERRORES / WARNING** | Historial fijo, del más reciente al más antiguo. Aunque el stream avance, aquí no se pierden. |
| **TOP ERRORES** | Ranking de errores repetidos. Los mensajes se agrupan normalizando números y contenido entre corchetes, así `Timeout tras 30 s` y `Timeout tras 45 s` cuentan como el mismo fallo. |
| **Barra** | Teclas disponibles y estado: `EN VIVO`, `PAUSADO` o `SIN ACTIVIDAD hace N min` (útil para detectar un bot colgado). |

Al salir se imprime un **resumen final** en el flujo normal de la consola, con
totales, periodo cubierto, ranking y la lista de errores — queda en el historial
aunque el panel desaparezca.

### Teclas

| Tecla | Acción |
|-------|--------|
| `p` | Pausa / reanuda el avance del stream. |
| `c` | Reinicia contadores e historiales. |
| `q` | Sale (equivale a `Ctrl+C`). |

## Formato de log soportado

```
DD/MM/YYYY HH:MM:SS | NIVEL | mensaje | bot | origen | url        (log RPA real)
     0                  1        2       3      4       5
YYYY-MM-DD HH:MM:SS NIVEL mensaje                                  (simple, sin barras)
```

Niveles reconocidos: `ERROR`/`CRITICAL`/`FATAL`, `WARNING`/`WARN`, `INFO`,
`DEBUG`/`TRACE`. Las líneas sin nivel se muestran en el color de fecha y se
cuentan aparte. Una línea que no encaja en ningún formato **nunca rompe el
visor**: se muestra tal cual.

### Temas de color (color verdadero 24-bit)

Al arrancar se elige el tema con un menú (Enter = **Neon**). También se fija sin
menú con `--theme`:

| Tema | Estilo |
|------|--------|
| `neon` | Colores neón vivos (por defecto) |
| `tokyo` | Paleta Tokyo Night |
| `pastel` | Tonos pastel suaves |

## Correr en cualquier máquina (solo descargar el repo)

El iniciador crea un entorno virtual local (`.venv`), instala las dependencias e
inicia el visor. **No ensucia el Python global ni necesita permisos de
administrador.**

```bash
git clone <url-del-repo> NANO
cd NANO
```

| Sistema | Comando |
|---------|---------|
| Windows (CMD / doble-clic) | `iniciar.bat` |
| Windows (PowerShell) | `.\iniciar.ps1` |
| Linux / macOS | `chmod +x iniciar.sh && ./iniciar.sh` |

La primera vez tarda un poco (crea el `.venv` e instala). Las siguientes arranca
al instante: el iniciador guarda la huella de `requirements.txt` en
`.venv/.deps-ok` y **solo reinstala si ese archivo cambia**. Cualquier opción se
pasa al iniciador, ej.: `iniciar.bat logs -f ERROR`.

### Instalación manual (alternativa)

```bash
pip install -r requirements.txt
python -m nano
```

Requisitos: **Python 3.9+**. Dependencias: `rich` (el panel) y `colorama`
(consola de Windows).

## Uso

```bash
python -m nano                        # vigila ./logs con el panel de control
python -m nano "C:\ruta\a\mis\logs"   # otra carpeta
python -m nano logs --simple          # stream plano, sin panel
python -m nano logs -f ERROR          # el stream solo muestra lineas con ERROR
```

`python log_viewer.py` sigue funcionando por compatibilidad.

### Opciones

| Opción | Descripción |
|--------|-------------|
| `-f`, `--filter X` | El stream solo muestra líneas que contengan `X`. **No afecta a los contadores**: el panel sigue reflejando el log completo. |
| `-t`, `--timestamp` | Antepone la hora de lectura a cada línea (solo en modo simple). |
| `-s`, `--save A.txt` | Guarda también la salida mostrada en `A.txt`. |
| `--tail` | Empieza al final del archivo (ignora lo ya escrito). |
| `--theme T` | Tema: `neon`, `tokyo` o `pastel` (salta el menú). |
| `--encoding E` | Fuerza el encoding del log (ej. `cp1252`). Por defecto auto. |
| `--simple` | Stream plano línea por línea, sin panel. |
| `--ascii` | Dibuja el panel con bordes ASCII (consolas sin Unicode). |
| `--max-errores N` | Entradas de los paneles de historial (default: 8). |
| `--no-panel-warning` | Oculta el panel de WARNING y ensancha el de errores. |

El modo simple se activa **solo** cuando la salida no es una terminal
(redirecciones, tuberías, tareas programadas), así que `python -m nano > out.txt`
produce texto limpio sin códigos de dibujo.

## Estructura del proyecto

```
nano/
├── core/            logica pura, sin terminal (testeable sin consola)
│   ├── modelo.py    LogRecord: una linea ya interpretada
│   ├── parser.py    parseo de los dos formatos de log
│   ├── encoding.py  deteccion de UTF-8 / BOM / cp1252
│   ├── seguidor.py  tail incremental, rotacion, lineas partidas
│   └── estado.py    contadores, historiales, ritmo, top de errores
├── ui/
│   ├── temas.py     paletas de color y su equivalente para rich
│   ├── menu.py      seleccion de tema al arrancar
│   ├── teclado.py   lectura de teclas sin bloquear (Windows y POSIX)
│   ├── base.py      bucle comun a los dos modos
│   ├── simple.py    stream plano
│   ├── dashboard.py panel de control
│   └── resumen.py   resumen final al salir
├── cli.py           argumentos y montaje de las piezas
├── config.py        todas las constantes ajustables
└── opciones.py      opciones de una ejecucion

scripts/
├── simular_log.py       genera un log RPA sintetico para probar
└── preparar_entorno.py  instala dependencias solo si hicieron falta
tests/                   pytest sobre core/ y render del panel
```

`core/` no importa nada de `ui/`: el parseo y el estado se pueden probar sin
terminal.

## Caracteres especiales (acentos, ñ)

NANO **auto-detecta el encoding** de cada archivo: BOM → `utf-8-sig`, si la
muestra decodifica como UTF-8 → `utf-8`, y si no → **cp1252** (típico en logs de
Windows). Un carácter multibyte partido entre dos lecturas se reconstruye bien,
y la salida de consola se fuerza a UTF-8. Se puede forzar con `--encoding`.

## Cómo funciona

Cada ~0.3 s se compara el tamaño del archivo con la última posición leída y se
leen **solo los bytes nuevos** (en binario, con decodificador incremental).
Detecta:

- **Rotación / truncado**: si el archivo encoge, reinicia desde el principio.
- **Archivo nuevo**: si aparece un `.txt` más reciente, cambia a seguirlo.
- **Línea a medio escribir**: si el bot aún no terminó la línea, se espera a que
  la complete en vez de mostrarla partida en dos.

## Desarrollo

```bash
pip install -r requirements-dev.txt
python -m pytest              # tests de parseo, estado, encoding, tail y render
```

Para ver el panel funcionando sin depender de un bot real, en dos consolas:

```bash
# consola A
python -m nano logs

# consola B
python scripts/simular_log.py logs --ritmo 5 --errores 20
```
