#!/usr/bin/env python3
"""Статична перевірка опису скіла: чи покриті тригери й винятки."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILL = ROOT.parent / "skills" / "humanizer-ua" / "SKILL.md"


def frontmatter_description(text: str) -> str:
    match = re.search(r'(?ms)^description:\s*"(.+?)"\s*$', text)
    if not match:
        match = re.search(r"(?ms)^description:\s*\|\s*\n((?:  .*\n)+)", text)
        if match:
            return " ".join(line.strip() for line in match.group(1).splitlines())
        raise ValueError("немає description у frontmatter")
    return match.group(1)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    data = json.loads((ROOT / "triggers.json").read_text(encoding="utf-8"))
    text = SKILL.read_text(encoding="utf-8")
    try:
        description = frontmatter_description(text)
    except ValueError as error:
        print(f"RESULT: FAIL triggers ({error})")
        return 1

    lowered = description.lower()
    errors = []
    for phrase in data["description_should_cover"]:
        if phrase.lower() not in lowered:
            errors.append(f"опис не згадує тригер: «{phrase}»")
    for phrase in data["description_should_exclude"]:
        if phrase.lower() not in lowered:
            errors.append(f"опис не містить винятку: «{phrase}»")

    if errors:
        print(f"RESULT: FAIL triggers ({len(errors)})")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(
        f"RESULT: PASS triggers ({len(data['description_should_cover'])} тригерів, "
        f"{len(data['description_should_exclude'])} винятків; статична перевірка)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
