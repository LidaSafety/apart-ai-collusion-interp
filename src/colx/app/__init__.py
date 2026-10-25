"""The round-4 results app (marimo): `col lens-judge app`."""

import subprocess
import sys
from pathlib import Path

APP_FILE = Path(__file__).with_name("round4.py")


def launch(port: int, headless: bool) -> int:
    """Serve the app read-only with `marimo run`; returns marimo's exit code."""
    cmd = [sys.executable, "-m", "marimo", "run", str(APP_FILE), "--port", str(port)]
    if headless:
        cmd.append("--headless")
    return subprocess.call(cmd)
