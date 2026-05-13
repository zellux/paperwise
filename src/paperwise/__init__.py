"""paperwise package."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import re


def _resolve_version() -> str:
    try:
        return version("paperwise")
    except PackageNotFoundError:
        pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
        match = re.search(r'(?m)^version = "([^"]+)"$', pyproject.read_text(encoding="utf-8"))
        if match:
            return match.group(1)
        raise


__version__ = _resolve_version()
