"""Звіт: правила, три шкали, факт-ризик, текст і JSON."""

from __future__ import annotations

from . import scoring
from .facts import diff_facts, ledger
from .markers import apply_weak_gating, collect, penalty_for
from .metrics import collect_metrics
from .norm import NORM_RULES
from .rules import HARD_BANS, MARKERS
from .text import (
    count_words,
    has_cyrillic,
    is_ukrainian,
    language_share,
    mask_code_only,
    mask_segments,
    mask_tables,
    normalise_newlines,
)

SCHEMA = "humanizer-ua/report/2"

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}

GROUPS = (
    ("НОРМА (виправити обов'язково)", lambda item: item.get("layer") == "norm"),
    ("ЖОРСТКІ ЗАБОРОНИ", lambda item: item.get("severity") == "error"),
    ("ВАРТО ПЕРЕГЛЯНУТИ", lambda item: item.get("severity") == "warning"),
    ("СИГНАЛИ", lambda item: item.get("severity") == "info"),
)


def _empty_report(genre: str) -> dict:
    return {
        "schema": SCHEMA,
        "score": None,
        "band": "немає тексту",
        "genre": genre,
        "lang": "unknown",
        "lang_share": 0.0,
        "words": 0,
        "scores": {
            "cleanliness": None,
            "norm": 100.0,
            "style": 100.0,
            "structure": 100.0,
            "fact_risk": 0,
        },
        "counts": {
            "hard_bans": 0,
            "norm_rules": 0,
            "norm": 0,
            "markers": 0,
            "marker_hits": 0,
            "metrics": 0,
            "weak_alone": 0,
            "fact_lock": 0,
            "errors": 0,
            "warnings": 0,
            "info": 0,
            "style": 0,
            "structure": 0,
        },
        "penalties": {"hard_bans": 0, "norm": 0, "markers": 0, "metrics": 0, "fact_lock": 0},
        "hard_bans": [],
        "norm": [],
        "markers": [],
        "metrics": [],
        "findings": [],
        "fact_lock": None,
        "facts": ledger(""),
        "diagnostics": ["TEXT_EMPTY"],
        "notes": [],
    }


def build_report(text: str, genre: str, before: str | None = None, allow_mixed: bool = False) -> dict:
    text = normalise_newlines(text)
    if before is not None:
        before = normalise_newlines(before)

    masked = mask_segments(text)
    code_masked = mask_tables(mask_code_only(text))
    # Цитати — це слова автора: вони не редагуються, але в знаменнику
    # щільності мають рахуватися. Тому рахуємо на code_masked, не на masked.
    words = count_words(code_masked)
    if not text.strip() or words == 0:
        return _empty_report(genre)

    share = language_share(text)
    diagnostics: list[str] = []

    if not has_cyrillic(text):
        diagnostics.append("LANG_NOT_UK")
    elif allow_mixed and share < 0.2:
        # Суржик — це суміш, а не чужа мова. Нижче 20 % українських ознак
        # прапорець не рятує: інакше чистий російський текст без ї/ы/э/ъ
        # отримував би «чисто».
        diagnostics.append("LANG_NOT_UK")
    elif not allow_mixed and not is_ukrainian(text):
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
    # Помилка — бінарна подія, а не плотнісна. На довгому тексті її штраф
    # прямує до нуля, але полосу «чисто» вона все одно блокує.
    has_errors = any(item["severity"] == "error" and item["penalty"] > 0 for item in rules)
    cleanliness = None if "LANG_NOT_UK" in diagnostics else scoring.composite(scores, genre)
    label = "немає оцінки" if cleanliness is None else scoring.band(cleanliness, scores, genre, has_errors)

    # Факт-ризик без оригіналу теж має сенс: реєстр показує неперевірені
    # числа, квантифікатори й діапазони. Квантор важить менше за
    # псевдоточність: «перший крок» — не те саме, що «понад 40 %».
    risk_points = sum(
        3 if risk.get("kind") in {"псевдоточність без джерела", "діапазон навпаки"} else 1
        for risk in facts.get("risks", [])
    )
    ledger_penalty = min(40, risk_points)
    # З оригіналом міряємо саме зміни факт-замком; реєстр потрібен лише
    # тоді, коли порівнювати нема з чим.
    risk_penalty = lock["penalty"] if lock else ledger_penalty

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
            "fact_risk": scoring.fact_risk(risk_penalty),
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


def _plural(number: int, one: str, few: str, many: str) -> str:
    """Українська форма множини для числа в звіті."""
    number = abs(number)
    if number % 10 == 1 and number % 100 != 11:
        return one
    if 2 <= number % 10 <= 4 and not 12 <= number % 100 <= 14:
        return few
    return many


def _summary_lines(report: dict) -> list[str]:
    scores = report["scores"]
    counts = report["counts"]
    lock = report.get("fact_lock")
    if lock:
        risks = sum(
            len(lock.get(key, []))
            for key in ("lost", "added", "soft_added", "claims_added")
        )
    else:
        risks = len(report["facts"].get("risks", []))
    return [
        f"  норма:      {scores['norm']:>5.0f}/100   ({counts['norm']} {_plural(counts['norm'], 'помилка', 'помилки', 'помилок')})",
        f"  стиль:      {scores['style']:>5.0f}/100   ({counts['style']} {_plural(counts['style'], 'зауваження', 'зауваження', 'зауважень')})",
        f"  структура:  {scores['structure']:>5.0f}/100   ({counts['structure']} {_plural(counts['structure'], 'зауваження', 'зауваження', 'зауважень')})",
        f"  факт-ризик: {scores['fact_risk']:>5}/100   ({risks} {_plural(risks, 'пункт', 'пункти', 'пунктів')} на перевірку)",
    ]


def format_report(report: dict, quiet: bool = False, verbose: bool = False) -> str:
    if quiet:
        return "—" if report["score"] is None else str(report["score"])

    if "TEXT_EMPTY" in report["diagnostics"]:
        return "ПОРОЖНІЙ ТЕКСТ: немає що сканувати.\n  Бал не рахується."

    if "LANG_NOT_UK" in report["diagnostics"]:
        return (
            "НЕ УКРАЇНСЬКИЙ ТЕКСТ: LANG_NOT_UK\n"
            f"  українських ознак: {report['lang_share']:.0%}\n"
            "  Скіл править лише український текст. Бал не рахується.\n"
            "  Якщо це суржик або суміш — додай --allow-mixed."
        )

    head = f"ЧИСТОТА: {report['score']}/100  [{report['genre']}] · {report['band']}"
    lines = [
        head,
        *_summary_lines(report),
        f"  слів: {report['words']}",
        f"  покриття: {len(MARKERS)} із 80 маркерів + {len(HARD_BANS)} заборон",
    ]

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
