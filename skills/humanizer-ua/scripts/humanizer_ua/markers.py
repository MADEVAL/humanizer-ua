"""Зіставлення правил із текстом і зважування слабких сигналів."""

from __future__ import annotations

from collections import Counter
import re

from .rules import WEAK_IDS
from .text import line_of, paragraph_ids


def rule_matches(rule: dict, text: str, genre: str) -> dict | None:
    if genre in rule.get("exempt", ()):  # type: ignore[arg-type]
        return None

    patterns = rule.get("patterns") or [rule["pattern"]]
    hits: list[tuple[int, str]] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            hits.append((match.start(), match.group(0)))

    if not hits:
        return None

    hits.sort(key=lambda item: item[0])
    lines: list[int] = []
    seen_lines: set[int] = set()
    for position, _ in hits:
        line = line_of(text, position)
        if line not in seen_lines:
            seen_lines.add(line)
            lines.append(line)

    ids = paragraph_ids(text)
    paragraphs = sorted({ids[min(max(line - 1, 0), len(ids) - 1)] for line in lines}) if ids else [0]

    weight = rule["weight"]
    return {
        "id": rule["id"],
        "label": rule["label"],
        "hint": rule["hint"],
        "count": len(hits),
        "lines": lines[:8],
        "paragraphs": paragraphs,
        "weight": weight,
        "penalty": min(3, len(hits)) * weight,
        "weak": rule["id"] in WEAK_IDS,
    }


def collect_rules(rules: list[dict], text: str, genre: str) -> list[dict]:
    found = []
    for rule in rules:
        result = rule_matches(rule, text, genre)
        if result:
            found.append(result)
    return found


def apply_weak_gating(items: list[dict]) -> list[dict]:
    """Слабкий маркер штрафується лише в компанії іншого маркера в абзаці."""
    by_paragraph: Counter = Counter()
    for item in items:
        for paragraph in item["paragraphs"]:
            by_paragraph[paragraph] += 1

    for item in items:
        if not item["weak"]:
            continue
        company = max((by_paragraph[p] for p in item["paragraphs"]), default=0)
        if company < 2:
            item["penalty"] = 0
            item["weak_alone"] = True
        else:
            item["weak_alone"] = False
    return items


def penalty_for(items: list[dict]) -> int:
    return sum(item["penalty"] for item in items)
