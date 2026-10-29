#!/usr/bin/env python3
"""Експорт правил у JSON для інтеграцій, веб-демо або CI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
ROOT = SKILL.parent.parent
sys.path.insert(0, str(SKILL / "scripts"))

from humanizer_ua.norm import NORM_RULES  # noqa: E402
from humanizer_ua.rules import GENRES, HARD_BANS, MARKERS, WEAK_IDS  # noqa: E402
from humanizer_ua.version import VERSION  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Експорт правил Humanizer-UA у JSON")
    parser.add_argument("--output", default=str(ROOT / "dist" / "rules-ua.json"))
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": VERSION,
        "genres": list(GENRES),
        "weak_ids": sorted(WEAK_IDS),
        "hard_bans": HARD_BANS,
        "norm": NORM_RULES,
        "markers": MARKERS,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"RESULT: PASS export-rules ({output}, "
        f"{len(HARD_BANS)} заборон, {len(NORM_RULES)} норм, {len(MARKERS)} маркерів)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
