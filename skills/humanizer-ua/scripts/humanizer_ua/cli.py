"""CLI сканера Humanizer-UA."""

from __future__ import annotations

import argparse
import json
import sys

from .rules import GENRES
from .score import build_report, format_report
from .text import read_text
from .version import VERSION


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="scan.py",
        description="Сканер українського тексту Humanizer-UA. Не детектор ШІ.",
    )
    parser.add_argument("path", nargs="?", default="-", help="файл або - для stdin")
    parser.add_argument("--genre", choices=GENRES, default="marketing", help="жанр тексту")
    parser.add_argument("--before", metavar="FILE", help="оригінал для факт-замку")
    parser.add_argument("--json", action="store_true", help="вивести JSON")
    parser.add_argument("--min-score", type=int, metavar="N", help="код 1, якщо бал нижчий за N")
    parser.add_argument("--quiet", action="store_true", help="лише число")
    parser.add_argument("--verbose", action="store_true", help="повний список знахідок із цитатами")
    parser.add_argument("--allow-mixed", action="store_true", help="аналізувати змішаний текст із поміткою")
    parser.add_argument("--encoding", choices=("auto", "utf-8", "utf-8-sig", "cp1251"), default="auto", help="кодування файлу")
    parser.add_argument("--version", action="version", version=f"humanizer-ua {VERSION}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    try:
        text = read_text(args.path, args.encoding)
        before = None
        if args.before:
            if args.before == "-":
                print("Помилка: --before не може читати зі stdin.", file=sys.stderr)
                return 2
            before = read_text(args.before, args.encoding)
    except (OSError, ValueError) as error:
        print(f"Помилка читання: {error}", file=sys.stderr)
        return 2

    report = build_report(text, args.genre, before, allow_mixed=args.allow_mixed)

    if args.json:
        payload = dict(report)
        payload["version"] = VERSION
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_report(report, quiet=args.quiet, verbose=args.verbose))

    if args.min_score is not None:
        if report["score"] is None or report["score"] < args.min_score:
            return 1
    return 0
