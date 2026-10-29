"""Звіт і бал чистоти."""

from __future__ import annotations

from .facts import diff_facts
from .markers import apply_weak_gating, collect_rules, penalty_for
from .metrics import collect_metrics
from .rules import HARD_BANS, MARKERS
from .text import count_words, mask_segments


def _band(score: int) -> str:
    if score >= 85:
        return "чисто"
    if score >= 60:
        return "правка"
    return "рерайт"


def build_report(text: str, genre: str, before: str | None = None) -> dict:
    masked = mask_segments(text)
    words = count_words(masked)

    hard = collect_rules(HARD_BANS, masked, genre)
    markers = collect_rules(MARKERS, masked, genre)
    apply_weak_gating(hard + markers)

    metrics = collect_metrics(text, masked, words, genre)
    lock = diff_facts(before, text).as_dict() if before is not None else None

    hard_penalty = penalty_for(hard)
    marker_penalty = penalty_for(markers)
    metric_penalty = sum(item["penalty"] for item in metrics)
    fact_penalty = lock["penalty"] if lock else 0
    score = max(0, 100 - hard_penalty - marker_penalty - metric_penalty - fact_penalty)

    weak_alone = [item for item in hard + markers if item.get("weak_alone")]
    notes: list[str] = []
    if weak_alone:
        notes.append(
            "слабкі сигнали без компанії: "
            + ", ".join(f"{item['id']} «{item['label']}»" for item in weak_alone[:5])
            + ". Не штрафуються, доки в абзаці немає іншого маркера."
        )
    if not hard and not markers and words >= 100:
        notes.append("жодного маркера. Це нормально: мета — типова частота, а не стерильний нуль.")

    return {
        "score": score,
        "band": _band(score),
        "genre": genre,
        "words": words,
        "counts": {
            "hard_bans": len(hard),
            "markers": len(markers),
            "marker_hits": sum(item["count"] for item in markers) + sum(item["count"] for item in hard),
            "metrics": len(metrics),
            "weak_alone": len(weak_alone),
            "fact_lock": fact_penalty,
        },
        "penalties": {
            "hard_bans": hard_penalty,
            "markers": marker_penalty,
            "metrics": metric_penalty,
            "fact_lock": fact_penalty,
        },
        "hard_bans": hard,
        "markers": markers,
        "metrics": metrics,
        "fact_lock": lock,
        "notes": notes,
    }


def _lines(value: list[int]) -> str:
    if not value:
        return ""
    if len(value) == 1:
        return f"рядок {value[0]}"
    return "рядки " + ", ".join(str(item) for item in value)


def _fact_line(prefix: str, items: list[str]) -> list[str]:
    return [f"  {prefix}: {item}" for item in items]


def format_report(report: dict, quiet: bool = False) -> str:
    if quiet:
        return str(report["score"])

    lines = [
        f"ЧИСТОТА: {report['score']}/100  [{report['genre']}] · {report['band']}",
    ]

    penalties = report["penalties"]
    if penalties["hard_bans"]:
        lines.append(f"  -{penalties['hard_bans']}  жорсткі заборони: {report['counts']['hard_bans']}")
    if penalties["markers"]:
        per_100 = report["counts"]["marker_hits"] / max(report["words"], 1) * 100
        lines.append(f"  -{penalties['markers']}  маркери: {report['counts']['marker_hits']} ({per_100:.1f}/100 слів)")
    if penalties["metrics"]:
        lines.append(f"  -{penalties['metrics']}  метрики: {report['counts']['metrics']}")
    if penalties["fact_lock"]:
        lines.append(f"  -{penalties['fact_lock']}  факт-замок")
    if report["counts"]["weak_alone"]:
        lines.append(f"  слабких без штрафу: {report['counts']['weak_alone']}")
    lines.append(f"  слів: {report['words']}")

    if report["hard_bans"]:
        lines.append("")
        lines.append("ЖОРСТКІ ЗАБОРОНИ:")
        for item in report["hard_bans"]:
            suffix = " (слабкий, без штрафу)" if item.get("weak_alone") else ""
            lines.append(f"  ⛔ {item['id']} «{item['label']}» ×{item['count']} ({_lines(item['lines'])}){suffix}")

    if report["markers"]:
        lines.append("")
        lines.append("МАРКЕРИ:")
        for item in report["markers"]:
            suffix = " (слабкий, без штрафу)" if item.get("weak_alone") else ""
            lines.append(f"  • {item['id']} «{item['label']}» ×{item['count']} ({_lines(item['lines'])}){suffix}")

    if report["metrics"]:
        lines.append("")
        lines.append("МЕТРИКИ:")
        for item in report["metrics"]:
            detail = f" — {item['detail']}" if item["detail"] else ""
            penalty = "" if item["penalty"] else " (без штрафу)"
            lines.append(f"  • {item['label']}: {item['value']} (норма до {item['limit']}){detail}{penalty}")

    lock = report["fact_lock"]
    if lock:
        lines.append("")
        lines.append("ФАКТ-ЗАМОК:")
        if lock["lost"]:
            lines.extend(_fact_line("втрачено", lock["lost"]))
        if lock["added"]:
            lines.extend(_fact_line("додано", lock["added"]))
        if lock["soft_added"]:
            lines.extend(_fact_line("кількість", lock["soft_added"]))
        if lock["claims_added"]:
            lines.extend(_fact_line("квантор", lock["claims_added"]))
        if lock["emphasis_lost"]:
            lines.extend(_fact_line("виділення", lock["emphasis_lost"]))
        if lock["markup_lost"]:
            lines.extend(_fact_line("розмітка", lock["markup_lost"]))
        if lock["ok"]:
            lines.append(f"  OK: зіставлено елементів {lock['kept']}; змін не знайдено")

    if report["notes"]:
        lines.append("")
        lines.append("ПРИМІТКИ:")
        for note in report["notes"]:
            lines.append(f"  · {note}")

    return "\n".join(lines)
