"""Публічний API Humanizer-UA."""

from .cli import main
from .score import build_report, format_report
from .version import VERSION

__all__ = ["VERSION", "build_report", "format_report", "main"]
