#!/usr/bin/env python3
"""Compatibilidade: encaminha para scripts/coletar_sisvan.py."""
from pathlib import Path
import runpy
import sys

if __name__ == "__main__":
    scripts = Path(__file__).resolve().parent / "scripts"
    sys.path.insert(0, str(scripts))
    runpy.run_path(
        str(scripts / "coletar_sisvan.py"),
        run_name="__main__",
    )
