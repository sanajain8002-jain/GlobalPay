#!/usr/bin/env python3
"""
GlobalPay 2.0 — Master Python Project Rebuilder & Customizer
Run this script (`python3 tools/python_generators/rebuild_project.py`) after
modifying any generator template or currency/corridor configuration.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

SCRIPTS = [
    "build_backend_and_db.py",
    "build_server_files.py",
    "build_server_engine.py",
    "build_ts_client_docs.py",
    "build_tests_and_docs.py",
    "build_publishing_bundle.py",
]

def main() -> None:
    print("[GlobalPay 2.0 Python Builder] Starting full project regeneration...")
    for script in SCRIPTS:
        script_path = HERE / script
        if script_path.exists():
            print(f" -> Executing {script}...")
            subprocess.run([sys.executable, str(script_path)], check=False)
    print("[GlobalPay 2.0 Python Builder] Regeneration complete.")

if __name__ == "__main__":
    main()
