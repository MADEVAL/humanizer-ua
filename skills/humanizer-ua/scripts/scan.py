#!/usr/bin/env python3
"""Тонка обгортка CLI. Рушій лежить у пакеті humanizer_ua/."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from humanizer_ua import VERSION, build_report, format_report  # noqa: E402
from humanizer_ua.cli import main  # noqa: E402

__all__ = ["VERSION", "build_report", "format_report", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
