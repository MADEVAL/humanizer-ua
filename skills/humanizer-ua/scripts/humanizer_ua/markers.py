"""Зіставлення правил із текстом: місця, події, впевненість."""

from __future__ import annotations

from collections import Counter
import re

from .context import confidence
from .scoring import event_penalty
from .text import count_words, line_of, paragraph_at, paragraph_spans

QUOTE_LIMIT = 90


def _unique_intervals(matches: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Прибирає перетини, коли правило має кілька шаблонів."""
    result: list[tuple[int, int]] = []
    for start, end in sorted(matches):
        if result and start < result[-1][1]:
            continue
        result.append((start, end))
    return result


def rule_matches(rule: dict, raw: str, masked: str, genre: str, words: int) -> dict | None:
    if genre in rule.get("exempt", ()):
        return None

    found: list[tuple[int, int]] = []
    for pattern in rule.get("patterns") or [rule["pattern"]]:
        for match in re.finditer(pattern, masked, flags=re.IGNORECASE):
            found.append((match.start(), match.end()))
    hits = _unique_intervals(found)
    if not hits:
        return None
    if len(hits) < rule.get("min_hits", 1):
        return None

    spans = paragraph_spans(raw)
    confidences = [confidence(rule, raw, start, end, genre) for start, end in hits]
    level = round(sum(confidences) / len(confidences), 2)

    lines: list[int] = []
    paragraphs: list[int] = []
    for start, _ in hits:
        line = line_of(raw, start)
        if line not in lines:
            lines.append(line)
        paragraph = paragraph_at(raw, start, spans)
        if paragraph not in paragraphs:
            paragraphs.append(paragraph)

    first_start, first_end = hits[0]
    quote = re.sub(r"\s+", " ", raw[first_start:first_end]).strip()[:QUOTE_LIMIT]
    severity = rule.get("severity", "warning")
    penalty = event_penalty(
        len(paragraphs),
        words,
        severity,
        level,
        rule.get("max_events"),
    )
    low_confidence = level < 0.5
    if low_confidence:
        penalty = 0.0
    penalty = round(penalty * rule.get("boost", 1.0), 2)

    return {
        "id": rule["id"],
        "rule_id": rule["id"],
        "label": rule["label"],
        "hint": rule["hint"],
        "suggestion": rule.get("suggestion", rule["hint"]),
        "layer": rule.get("layer", "style"),
        "severity": severity,
        "count": len(hits),
        "events": len(paragraphs),
        "lines": lines[:8],
        "paragraphs": paragraphs,
        "weight": rule.get("weight", 5),
        "confidence": level,
        "penalty": penalty,
        "low_confidence": low_confidence,
        "span": {"start": first_start, "end": first_end, "line": lines[0]},
        "quote": quote,
        "weak": bool(rule.get("weak")),
        "max_events": rule.get("max_events"),
    }


def collect(rules: list[dict], raw: str, masked: str, genre: str, words: int | None = None) -> list[dict]:
    words = count_words(masked) if words is None else words
    found = []
    for rule in rules:
        result = rule_matches(rule, raw, masked, genre, words)
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
        if not item.get("weak"):
            continue
        company = max((by_paragraph[p] for p in item["paragraphs"]), default=0)
        if company < 2:
            item["penalty"] = 0.0
            item["weak_alone"] = True
        else:
            item["weak_alone"] = False
    return items


def penalty_for(items: list[dict]) -> int:
    return int(round(sum(item["penalty"] for item in items)))
