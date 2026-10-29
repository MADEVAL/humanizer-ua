#!/usr/bin/env python3
"""Перевіряє, що приклад у README збігається з реальним сканером."""

from __future__ import annotations

import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
ROOT = SKILL.parent.parent
sys.path.insert(0, str(SKILL / "scripts"))

from humanizer_ua.score import build_report  # noqa: E402


def blockquote_after(lines: list[str], marker: str) -> str:
    start = next((index for index, line in enumerate(lines) if marker in line), None)
    if start is None:
        raise ValueError(f"немає маркера: {marker}")
    collected = []
    for line in lines[start + 1 :]:
        if line.startswith(">"):
            collected.append(line[1:].strip())
        elif collected and line.strip():
            break
        elif collected:
            break
    if not collected:
        raise ValueError(f"немає цитати після: {marker}")
    return " ".join(collected)


def fenced_block_after(lines: list[str], marker: str) -> list[str]:
    start = next((index for index, line in enumerate(lines) if marker in line), None)
    if start is None:
        raise ValueError(f"немає маркера: {marker}")
    fence = next((index for index in range(start + 1, len(lines)) if lines[index].strip().startswith("```")), None)
    if fence is None:
        raise ValueError(f"немає блоку коду після: {marker}")
    collected = []
    for line in lines[fence + 1 :]:
        if line.strip().startswith("```"):
            return collected
        collected.append(line)
    raise ValueError("блок коду не закритий")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    errors: list[str] = []
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    lines = readme.splitlines()

    try:
        before = blockquote_after(lines, "**Було:**")
        audit = "\n".join(fenced_block_after(lines, "**Аудит того самого тексту:**"))
    except ValueError as error:
        print(f"RESULT: FAIL ({error})")
        return 1

    report = build_report(before, "marketing", None)
    declared_score = re.search(r"ЧИСТОТА:\s*(\d+)/100", audit)
    declared_ids = set(re.findall(r"HB\d{2}", audit))
    actual_ids = {item["id"] for item in report["hard_bans"]}

    if not declared_score:
        errors.append("у блоці аудиту немає «ЧИСТОТА: N/100»")
    elif int(declared_score.group(1)) != report["score"]:
        errors.append(f"README: бал {declared_score.group(1)}, сканер: {report['score']}")

    if declared_ids != actual_ids:
        errors.append(f"README: ID {sorted(declared_ids)}, сканер: {sorted(actual_ids)}")

    catalog = (SKILL / "references" / "catalog.md").read_text(encoding="utf-8")
    if len(re.findall(r"(?m)^### [A-H][0-9]+\. ", catalog)) != 80:
        errors.append("catalog.md: не 80 маркерів")

    hard = (SKILL / "references" / "hard-bans.md").read_text(encoding="utf-8")
    if len(re.findall(r"\*\*HB[0-9]{2}\*\*", hard)) != 30:
        errors.append("hard-bans.md: не 30 заборон")
    if len(re.findall(r"\*\*N[0-9]{2}\*\*", hard)) != 15:
        errors.append("hard-bans.md: не 15 нормативних правил")

    if "80 маркерів" not in readme:
        errors.append("README: немає «80 маркерів»")

    if errors:
        print(f"RESULT: FAIL ({len(errors)})")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"RESULT: PASS check-examples (бал {report['score']}, {len(actual_ids)} заборон)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
