#!/usr/bin/env python3
"""Compatibilidad: `python log_viewer.py` sigue funcionando.

La implementacion vive ahora en el paquete `nano/`. La forma recomendada de
arrancar es `python -m nano`.
"""

from nano.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
