from __future__ import annotations

from fnmatch import fnmatchcase
import tomllib
from pathlib import Path


def test_all_static_assets_are_declared_as_package_data() -> None:
    project_root = Path(__file__).resolve().parents[2]
    package_root = project_root / "src" / "paperwise"
    pyproject = tomllib.loads((project_root / "pyproject.toml").read_text())
    package_data = pyproject["tool"]["setuptools"]["package-data"]["paperwise"]

    missing = []
    for asset_path in (package_root / "server" / "static").rglob("*"):
        if not asset_path.is_file():
            continue
        relative_path = asset_path.relative_to(package_root).as_posix()
        if not any(_matches_package_data_pattern(relative_path, pattern) for pattern in package_data):
            missing.append(relative_path)

    assert missing == []


def _matches_package_data_pattern(relative_path: str, pattern: str) -> bool:
    path_parts = relative_path.split("/")
    pattern_parts = pattern.split("/")
    return len(path_parts) == len(pattern_parts) and all(
        fnmatchcase(path_part, pattern_part)
        for path_part, pattern_part in zip(path_parts, pattern_parts, strict=True)
    )
