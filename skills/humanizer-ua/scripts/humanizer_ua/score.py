"""Звіт: правила, три шкали, факт-ризик, текст і JSON."""

from __future__ import annotations

from . import scoring
from .facts import diff_facts, ledger
from .markers import apply_weak_gating, collect, penalty_for
from .metrics import collect_metrics
from .norm import NORM_RULES
from .rules import HARD_BANS, MARKERS
from .text import count_words, is_ukrainian, language_share, mask_code_only, mask_segments, mask_tables

SCHEMA = "humanizer-ua/report/2"

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}

GROUPS = (
    ("НОРМА (виправити обов'язково)", lambda item: item.get("layer") == "norm"),
    ("ЖОРСТКІ ЗАБОРОНИ", lambda item: item.get("severity") == "error"),
    ("ВАРТО ПЕРЕГЛЯНУТИ", lambda item: item.get("severity") == "warning"),
    ("СИГНАЛИ", lambda item: item.get("severity") == "info"),
)


def build_report(text: str, genre: str, before: str | None = None, allow_mixed: bool = False) -> dict:
    masked = mask_segments(text)
    code_masked = mask_tables(mask_code_only(text))
    words = count_words(masked)
    share = language_share(text) if words >= 5 else 1.0
    diagnostics: list[str] = []

    if not allow_mixed and not is_ukrainian(text):
        diagnostics.append("LANG_NOT_UK")
    elif allow_mixed and share < 0.8:
        diagnostics.append("LANG_MIXED")

    rules: list[dict] = []
    if "LANG_NOT_UK" not in diagnostics:
        hard = collect(HARD_BANS, text, masked, genre, words)
        markers = collect(MARKERS, text, masked, genre, words)
        norm = collect(NORM_RULES, text, code_masked, genre, words)
        rules = hard + markers + norm
        apply_weak_gating(rules)
    else:
        hard, markers, norm = [], [], []

    metrics = collect_metrics(text, masked, words, genre) if "LANG_NOT_UK" not in diagnostics else []
    lock = diff_facts(before, text).as_dict() if before is not None else None
    facts = ledger(text) if "LANG_NOT_UK" not in diagnostics else {"entities": [], "risks": []}

    findings = rules + metrics
    scores = scoring.sub_scores(findings)
    has_errors = any(item["severity"] == "error" and item["penalty"] > 0.5 for item in rules)
    cleanliness = None if "LANG_NOT_UK" in diagnostics else scoring.composite(scores, genre)
    label = "немає оцінки" if cleanliness is None else scoring.band(cleanliness, scores, genre, has_errors)

    penalties = {
        "hard_bans": penalty_for([item for item in rules if item["id"].startswith("HB")]),
        "norm": penalty_for([item for item in rules if item["layer"] == "norm"]),
        "markers": penalty_for(
            [item for item in rules if not item["id"].startswith("HB") and item["layer"] != "norm"]
        ),
        "metrics": int(round(sum(item["penalty"] for item in metrics))),
        "fact_lock": lock["penalty"] if lock else 0,
    }

    findings.sort(key=lambda item: (SEVERITY_ORDER.get(item.get("severity", "warning"), 1), item.get("span", {}).get("line", 0)))

    weak_alone = [item for item in rules if item.get("weak_alone")]
    notes: list[str] = []
    if weak_alone:
        notes.append(
            "слабкі сигнали без компанії: "
            + ", ".join(f"{item['id']} «{item['label']}»" for item in weak_alone[:5])
            + ". Не штрафуються, доки в абзаці немає іншого маркера."
        )
    if not rules and words >= 100 and "LANG_NOT_UK" not in diagnostics:
        notes.append("жодного маркера. Це нормально: мета — типова частота, а не стерильний нуль.")
    if allow_mixed and share < 0.8:
        notes.append("змішаний текст: української менше 80 %. Аналіз неповний.")

    return {
        "schema": SCHEMA,
        "score": cleanliness,
        "band": label,
        "genre": genre,
        "lang": "uk" if share >= 0.8 else "mixed",
        "lang_share": round(share, 3),
        "words": words,
        "scores": {
            "cleanliness": cleanliness,
            "norm": scores["norm"],
            "style": scores["style"],
            "structure": scores["structure"],
            "fact_risk": scoring.fact_risk(lock["penalty"]) if lock else 0,
        },
        "counts": {
            "hard_bans": len(hard),
            "norm_rules": len(norm),
            "norm": sum(1 for item in rules if item["layer"] == "norm"),
            "markers": len(markers),
            "marker_hits": sum(item["count"] for item in rules),
            "metrics": len(metrics),
            "weak_alone": len(weak_alone),
            "fact_lock": lock["penalty"] if lock else 0,
            "errors": sum(1 for item in rules if item["severity"] == "error"),
            "warnings": sum(1 for item in rules if item["severity"] == "warning"),
            "info": sum(1 for item in rules if item["severity"] == "info"),
            "style": sum(1 for item in findings if item.get("layer") == "style"),
            "structure": sum(1 for item in findings if item.get("layer") == "structure"),
        },
        "penalties": penalties,
        "hard_bans": [item for item in hard if item["id"].startswith("HB")],
        "norm": norm,
        "markers": markers,
        "metrics": metrics,
        "findings": findings,
        "fact_lock": lock,
        "facts": facts,
        "diagnostics": diagnostics,
        "notes": notes,
    }


def _lines(value: list[int]) -> str:
    if not value:
        return ""
    if len(value) == 1:
        return f"рядок {value[0]}"
    return "рядки " + ", ".join(str(item) for item in value)


def _summary_lines(report: dict) -> list[str]:
    scores = report["scores"]
    counts = report["counts"]
    return [
        f"  норма:      {scores['norm']:>5.0f}/100   ({counts['norm']} помилок)",
        f"  стиль:      {scores['style']:>5.0f}/100   ({counts['style']} зауважень)",
        f"  структура:  {scores['structure']:>5.0f}/100   ({counts['structure']} зауважень)",
        f"  факт-ризик: {scores['fact_risk']:>5}/100   ({len(report['facts'].get('risks', []))} пунктів на перевірку)",
    ]


def format_report(report: dict, quiet: bool = False, verbose: bool = False) -> str:
    if quiet:
        return "—" if report["score"] is None else str(report["score"])

    if "LANG_NOT_UK" in report["diagnostics"]:
        return (
            "НЕ УКРАЇНСЬКИЙ ТЕКСТ: LANG_NOT_UK\n"
            f"  українських ознак: {report['lang_share']:.0%}\n"
            "  Скіл править лише український текст. Бал не рахується.\n"
            "  Якщо це суржик або суміш — додай --allow-mixed."
        )

    head = f"ЧИСТОТА: {report['score']}/100  [{report['genre']}] · {report['band']}"
    lines = [head, *_summary_lines(report), f"  слів: {report['words']}"]

    limit = None if verbose else 60
    printed = 0
    used: set[int] = set()
    for title, predicate in GROUPS:
        group = [
            item
            for item in report["findings"]
            if item.get("rule_id") and id(item) not in used and predicate(item)
        ]
        if not group:
            continue
        used.update(id(item) for item in group)
        lines.append("")
        lines.append(title + ":")
        for item in group:
            if limit and printed >= limit:
                lines.append("  … повний список: --verbose")
                break
            mark = {"error": "✖", "warning": "⚠", "info": "·"}[item["severity"]]
            suffix = ""
            if item.get("weak_alone"):
                suffix = " (слабкий, без штрафу)"
            if item["confidence"] < 0.5:
                suffix += " (низька впевненість)"
            lines.append(f"  {mark} {item['id']} «{item['label']}» ×{item['count']} ({_lines(item['lines'])}){suffix}")
            if verbose and item.get("quote"):
                lines.append(f"      «{item['quote']}»")
            printed += 1

    if report["metrics"]:
        lines.append("")
        lines.append("МЕТРИКИ:")
        for item in report["metrics"]:
            detail = f" — {item['detail']}" if item["detail"] else ""
            penalty = "" if item["penalty"] else " (без штрафу)"
            lines.append(f"  · {item['label']}: {item['value']} (норма до {item['limit']}){detail}{penalty}")

    if report["facts"]["entities"]:
        lines.append("")
        lines.append(f"ФАКТИ: {len(report['facts']['entities'])} елементів у реєстрі")
        for risk in report["facts"]["risks"][:5]:
            lines.append(f"  ? {risk['kind']}: «{risk['quote']}» — перевір")

    lock = report["fact_lock"]
    if lock:
        lines.append("")
        lines.append("ФАКТ-ЗАМОК:")
        if lock["lost"]:
            lines.extend(f"  втрачено: {item}" for item in lock["lost"])
        if lock["added"]:
            lines.extend(f"  додано: {item}" for item in lock["added"])
        if lock["soft_added"]:
            lines.extend(f"  кількість: {item}" for item in lock["soft_added"])
        if lock["claims_added"]:
            lines.extend(f"  квантор: {item}" for item in lock["claims_added"])
        if lock["emphasis_lost"]:
            lines.extend(f"  виділення: {item}" for item in lock["emphasis_lost"])
        if lock["markup_lost"]:
            lines.extend(f"  розмітка: {item}" for item in lock["markup_lost"])
        if lock["ok"]:
            lines.append(f"  OK: зіставлено елементів {lock['kept']}; змін не знайдено")

    if report["notes"]:
        lines.append("")
        lines.append("ПРИМІТКИ:")
        for note in report["notes"]:
            lines.append(f"  · {note}")

    return "\n".join(lines)
