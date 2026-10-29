#!/usr/bin/env python3
"""Dogfood: сканує власну прозу скіла на жорсткі заборони."""

from __future__ import annotations

import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
ROOT = SKILL.parent.parent
sys.path.insert(0, str(SKILL / "scripts"))

from humanizer_ua.score import build_report  # noqa: E402

FILES = [
    SKILL / "SKILL.md",
    SKILL / "references" / "registers.md",
    SKILL / "references" / "review.md",
    SKILL / "references" / "voice.md",
    SKILL / "references" / "typography.md",
    ROOT / "README.md",
    ROOT / "AGENTS.md",
]


def prose_only(text: str) -> str:
    lines = []
    in_code = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if stripped.startswith((">", "|", "#")):
            continue
        if "**Було:**" in line or "**Стало:**" in line:
            continue
        lines.append(line)
    return "\n".join(lines)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    failures = []
    for path in FILES:
        if not path.exists():
            failures.append(f"немає файлу: {path}")
            continue
        report = build_report(prose_only(path.read_text(encoding="utf-8")), "marketing", None)
        for item in report["hard_bans"]:
            failures.append(f"{path.name}: {item['id']} «{item['label']}» ({item['count']})")

    if failures:
        print(f"RESULT: FAIL self-scan ({len(failures)})")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print(f"RESULT: PASS self-scan ({len(FILES)} файлів)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
