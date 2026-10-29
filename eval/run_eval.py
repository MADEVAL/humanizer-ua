#!/usr/bin/env python3
"""Мінімальний eval: розділення AI/людських текстів і перевірка кейсів.

Запуск: python eval/run_eval.py
Код виходу 0 — усе пройшло, 1 — є провал.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILL = ROOT.parent / "skills" / "humanizer-ua"
sys.path.insert(0, str(SKILL / "scripts"))

import scan  # noqa: E402


def corpus_scores(folder: Path, genre: str) -> list[tuple[str, dict]]:
    results = []
    for path in sorted(folder.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        results.append((path.name, scan.build_report(text, genre, None)))
    return results


def print_table(rows: list[tuple[str, dict]]) -> None:
    print(f"{'файл':38} {'бал':>5} {'заборони':>9} {'маркери':>8} {'метрики':>8}")
    for name, report in rows:
        print(
            f"{name:38} {report['score']:>5} "
            f"{report['counts']['hard_bans']:>9} "
            f"{report['counts']['markers']:>8} "
            f"{report['counts']['metrics']:>8}"
        )


def check_cases() -> list[str]:
    errors: list[str] = []
    cases_path = ROOT / "cases.jsonl"
    if not cases_path.exists():
        return ["cases.jsonl не знайдено"]

    for line_number, line in enumerate(cases_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        case = json.loads(line)
        after = case["after"]

        for item in case.get("must_keep", []):
            if item not in after:
                errors.append(f"{case['id']}: втрачено обов'язкове «{item}»")

        for item in case.get("must_not_add", []):
            if item in after:
                errors.append(f"{case['id']}: додано зайве «{item}»")

        report = scan.build_report(after, case.get("genre", "marketing"), case["before"])
        lock = report["fact_lock"]
        lost = lock["lost"]
        for item in case.get("must_keep", []):
            if any(item in value for value in lost):
                errors.append(f"{case['id']}: факт-замок вважає втраченим «{item}»")

        print(f"  {case['id']:24} бал {report['score']:>3}  факт-замок {'OK' if not lost else 'УВАГА'}")

    return errors


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    ai_rows = corpus_scores(ROOT / "corpus" / "ai", "marketing")
    human_rows = corpus_scores(ROOT / "corpus" / "human", "marketing")

    print("AI-тексти:")
    print_table(ai_rows)
    print("\nЛюдські тексти:")
    print_table(human_rows)

    ai_scores = [report["score"] for _, report in ai_rows]
    human_scores = [report["score"] for _, report in human_rows]

    errors: list[str] = []

    if not ai_rows or not human_rows:
        errors.append("Порожній корпус: потрібні файли в corpus/ai і corpus/human")

    if ai_scores and max(ai_scores) >= 70:
        errors.append(f"AI-текст занадто високо: {max(ai_scores)} (очікується < 70)")

    if human_scores and min(human_scores) < 90:
        errors.append(f"Людський текст занадто низько: {min(human_scores)} (очікується >= 90)")

    if ai_scores and human_scores and (sum(human_scores) / len(human_scores)) - (sum(ai_scores) / len(ai_scores)) < 30:
        errors.append("Розрив між AI і людьми менший за 30 балів")

    print("\nКейси:")
    errors.extend(check_cases())

    print()
    if errors:
        print("РЕЗУЛЬТАТ: ПРОВАЛ")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("РЕЗУЛЬТАТ: ПРОЙШЛО")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
