#!/usr/bin/env python3
"""CI-гейт: сканує файли й падає, якщо бал нижчий за поріг."""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from humanizer_ua import VERSION  # noqa: E402
from humanizer_ua.rules import GENRES  # noqa: E402
from humanizer_ua.score import build_report  # noqa: E402
from humanizer_ua.text import read_text  # noqa: E402

SKIP_PARTS = {".git", "node_modules", "__pycache__", ".venv", "dist", "build"}


def expand(paths: list[str], extensions: set[str]) -> list[Path]:
    found: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if any(char in raw for char in "*?["):
            candidates = [Path(item) for item in glob.glob(raw, recursive=True)]
        elif path.is_dir():
            candidates = list(path.rglob("*"))
        else:
            candidates = [path]
        for candidate in candidates:
            if not candidate.is_file():
                continue
            if candidate.suffix.lower() not in extensions:
                continue
            if any(part in SKIP_PARTS for part in candidate.parts):
                continue
            found.append(candidate)
    return sorted({item.resolve() for item in found})


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Сканер-гейт Humanizer-UA")
    parser.add_argument("paths", nargs="+", help="файли, теки або glob-шаблони")
    parser.add_argument("--genre", choices=GENRES, default="marketing", help="жанр тексту")
    parser.add_argument("--min-score", type=int, default=60, help="мінімальний бал")
    parser.add_argument("--ext", default=".md,.txt,.markdown", help="розширення через кому")
    parser.add_argument("--fail-on-hard-ban", action="store_true", help="падати на будь-якій жорсткій забороні")
    parser.add_argument("--json", action="store_true", help="вивести JSON")
    parser.add_argument("--quiet", action="store_true", help="лише підсумок")
    args = parser.parse_args(argv)

    extensions = {item.strip().lower() for item in args.ext.split(",") if item.strip()}
    files = expand(args.paths, extensions)
    if not files:
        print("Не знайдено файлів для сканування.", file=sys.stderr)
        return 2

    rows = []
    failed = False
    for path in files:
        try:
            text = read_text(str(path))
            report = build_report(text, args.genre, None)
        except (OSError, ValueError) as error:
            failed = True
            rows.append(
                {
                    "file": str(path),
                    "score": None,
                    "band": "помилка",
                    "hard_bans": 0,
                    "markers": 0,
                    "metrics": 0,
                    "status": "FAIL",
                    "error": str(error),
                    "diagnostics": [],
                }
            )
            continue

        hard = report["counts"]["hard_bans"]
        score = report["score"]
        below = score is None or score < args.min_score
        hard_fail = args.fail_on_hard_ban and hard > 0
        status = "FAIL" if below or hard_fail else "OK"
        failed = failed or status == "FAIL"
        rows.append(
            {
                "file": str(path),
                "score": score,
                "band": report["band"],
                "hard_bans": hard,
                "markers": report["counts"]["marker_hits"],
                "metrics": report["counts"]["metrics"],
                "status": status,
                "diagnostics": report["diagnostics"],
            }
        )

    if args.json:
        print(json.dumps({"version": VERSION, "min_score": args.min_score, "files": rows, "ok": not failed}, ensure_ascii=False, indent=2))
        return 1 if failed else 0

    if not args.quiet:
        print(f"{'файл':50} {'бал':>5} {'заборони':>9} {'маркери':>8} {'метрики':>8}  статус")
        for row in rows:
            score = "—" if row["score"] is None else str(row["score"])
            reason = row.get("error") or ", ".join(row.get("diagnostics", []))
            note = f"  {reason}" if reason else ""
            print(
                f"{row['file']:50} {score:>5} {row['hard_bans']:>9} "
                f"{row['markers']:>8} {row['metrics']:>8}  {row['status']}{note}"
            )

    print(f"RESULT: {'FAIL' if failed else 'PASS'} ({len(rows)} файлів, поріг {args.min_score})")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
