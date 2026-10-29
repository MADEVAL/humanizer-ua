#!/usr/bin/env python3
"""Збирає ZIP для завантаження в Claude.ai або інший агент.

У корені архіву лежить SKILL.md, а не вкладена папка.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
ROOT = SKILL.parent.parent
SKIP_DIRS = {"__pycache__", ".git"}
SKIP_SUFFIXES = {".pyc", ".pyo"}
SKIP_NAMES = {".DS_Store", "Thumbs.db"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Зібрати ZIP скіла Humanizer-UA")
    parser.add_argument("--output", default=str(ROOT / "dist" / "humanizer-ua.zip"))
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    added = 0
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(SKILL.rglob("*")):
            if not path.is_file():
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.suffix in SKIP_SUFFIXES or path.name in SKIP_NAMES:
                continue
            archive.write(path, path.relative_to(SKILL).as_posix())
            added += 1

    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
    if "SKILL.md" not in names:
        print("RESULT: FAIL build-zip (SKILL.md не в корені архіву)")
        return 1

    print(f"RESULT: PASS build-zip ({output}, {added} файлів, {output.stat().st_size} байт)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
