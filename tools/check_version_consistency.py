#!/usr/bin/env python3
"""Check that user-facing version strings match pyproject.toml."""

from __future__ import annotations

import re
import sys
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> int:
    pyproject_text = read_text("pyproject.toml")
    match = re.search(r'(?m)^version = "([^"]+)"$', pyproject_text)
    if not match:
        print("version check failed: could not find project.version in pyproject.toml", file=sys.stderr)
        return 1

    version = match.group(1)
    display_version = f"v{version}"

    checks = [
        (
            "src/paperwise/server/main.py",
            r"version=__version__",
            "FastAPI app version source",
        ),
        (
            "website/index.html",
            re.escape(display_version),
            "website displayed version",
        ),
    ]

    failures: list[str] = []
    for path, pattern, label in checks:
        if not re.search(pattern, read_text(path)):
            failures.append(f"{label} in {path} does not match {display_version}")

    if failures:
        for failure in failures:
            print(f"version check failed: {failure}", file=sys.stderr)
        return 1

    ref_type = os.environ.get("GITHUB_REF_TYPE")
    ref_name = os.environ.get("GITHUB_REF_NAME")
    if ref_type == "tag" and ref_name and ref_name.startswith("v") and ref_name != display_version:
        print(
            f"version check failed: git tag {ref_name} does not match {display_version}",
            file=sys.stderr,
        )
        return 1

    print(f"version check passed: {display_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
