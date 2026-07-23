from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def bundled_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS).resolve()
    return app_root()


def default_runtime_dir() -> Path:
    bundled_runtime = bundled_root() / "runtime" / "unity_mono"
    if bundled_runtime.exists():
        return bundled_runtime
    return app_root() / "runtime" / "unity_mono"
