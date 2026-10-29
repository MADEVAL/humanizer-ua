#!/usr/bin/env python3
"""Тести сканера Humanizer-UA. Запуск: python -m unittest scripts/test_scan.py"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import scan  # noqa: E402

AI_TEXT = """У сучасному світі штучний інтелект відіграє важливу роль у розвитку бізнесу.
Варто зазначити, що даний інструмент являється комплексним рішенням, яке відкриває нові горизонти.
На протязі останнього року ми впровадили його в трьох проєктах. Експерти вважають, що це найкраще рішення.
"""

CLEAN_TEXT = """Ми впровадили інструмент у трьох проєктах. За рік витрати на звіти впали на 40 %.
Звіт, на який раніше йшло дві години, тепер збирається за двадцять хвилин.
Два проєкти прискорилися, третій довелося переробити. Інструмент не замінює команду.
"""


class ScannerTests(unittest.TestCase):
    def test_clean_text_scores_high(self) -> None:
        report = scan.build_report(CLEAN_TEXT, "marketing", None)
        self.assertGreaterEqual(report["score"], 90)
        self.assertEqual(report["hard_bans"], [])

    def test_hard_bans_detected(self) -> None:
        report = scan.build_report(AI_TEXT, "marketing", None)
        ids = {item["id"] for item in report["hard_bans"]}
        for expected in {"HB01", "HB02", "HB04", "HB05", "HB06", "HB08", "HB20", "HB25"}:
            self.assertIn(expected, ids)
        self.assertLess(report["score"], 50)

    def test_new_catalog_markers(self) -> None:
        text = (
            "Високо-якісний продукт, підкреслюючи важливість. "
            "Він пов’язаний із керівництвом. Галерея служить як виставковий простір."
        )
        report = scan.build_report(text, "marketing", None)
        ids = {item["id"] for item in report["markers"]}
        for expected in {"B11", "C11", "C12", "D8"}:
            self.assertIn(expected, ids)

    def test_preposition_and_any_context(self) -> None:
        correct = "Згідно зі стандартом і згідно з наказом. Любий друг може допомогти."
        wrong = "Згідно наказу. Любий варіант підійде."
        correct_ids = {item["id"] for item in scan.build_report(correct, "business", None)["hard_bans"]}
        wrong_ids = {item["id"] for item in scan.build_report(wrong, "business", None)["hard_bans"]}
        self.assertNotIn("HB22", correct_ids)
        self.assertNotIn("HB23", correct_ids)
        self.assertIn("HB22", wrong_ids)
        self.assertIn("HB23", wrong_ids)

    def test_genre_exemption(self) -> None:
        text = "Даний закон регулює відносини між сторонами."
        marketing = scan.build_report(text, "marketing", None)
        academic = scan.build_report(text, "academic", None)
        self.assertIn("HB04", {item["id"] for item in marketing["hard_bans"]})
        self.assertNotIn("HB04", {item["id"] for item in academic["hard_bans"]})

    def test_fact_lock_missing_number(self) -> None:
        before = "Витрати впали на 40 % за 2 роки."
        after = "Витрати впали."
        report = scan.build_report(after, "marketing", before)
        lost = report["fact_lock"]["lost"]
        self.assertTrue(any("40" in item and "%" in item for item in lost))
        self.assertGreater(report["penalties"]["fact_lock"], 0)

    def test_fact_lock_added_number(self) -> None:
        before = "Витрати впали."
        after = "Витрати впали на 25 %."
        report = scan.build_report(after, "marketing", before)
        added = report["fact_lock"]["added"]
        self.assertTrue(any("25" in item and "%" in item for item in added))

    def test_fact_lock_keeps_full_name(self) -> None:
        before = "Директор Олена Коваль підписала договір 12.03.2025."
        after = "Олена підписала договір."
        report = scan.build_report(after, "marketing", before)
        lost = report["fact_lock"]["lost"]
        self.assertTrue(any("Олена" in item for item in lost))
        self.assertTrue(any("12.03.2025" in item for item in lost))

    def test_typography_metrics(self) -> None:
        text = "Він сказав \"проєкт\" і пішов до об'єкта. Зростання 5%."
        report = scan.build_report(text, "marketing", None)
        ids = {item["id"] for item in report["metrics"]}
        self.assertIn("quotes", ids)
        self.assertIn("ascii_apostrophe", ids)
        self.assertIn("numbers", ids)

    def test_russian_letters(self) -> None:
        report = scan.build_report("Це проэкт із ёлкою.", "marketing", None)
        ids = {item["id"] for item in report["metrics"]}
        self.assertIn("russian_letters", ids)
        self.assertGreater(report["penalties"]["metrics"], 0)

    def test_report_is_json_serialisable(self) -> None:
        report = scan.build_report(AI_TEXT, "marketing", AI_TEXT)
        payload = json.dumps(report, ensure_ascii=False)
        self.assertIn("score", json.loads(payload))

    def test_all_patterns_compile(self) -> None:
        from rules_ua import HARD_BANS, MARKERS

        for rule in HARD_BANS + MARKERS:
            patterns = rule.get("patterns") or [rule["pattern"]]
            for pattern in patterns:
                re.compile(pattern)

    def test_rule_ids_exist_in_docs(self) -> None:
        from rules_ua import HARD_BANS, MARKERS

        catalog = (SKILL_ROOT / "references" / "catalog.md").read_text(encoding="utf-8")
        hard_bans = (SKILL_ROOT / "references" / "hard-bans.md").read_text(encoding="utf-8")
        for rule in HARD_BANS:
            self.assertIn(rule["id"], hard_bans)
        for rule in MARKERS:
            self.assertIn(rule["id"], catalog)

    def test_unique_rule_ids(self) -> None:
        from rules_ua import HARD_BANS, MARKERS

        ids = [rule["id"] for rule in HARD_BANS + MARKERS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_cli_stdin(self) -> None:
        result = subprocess.run(
            [sys.executable, str(HERE / "scan.py"), "-", "--json"],
            input=AI_TEXT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertLess(payload["score"], 50)

    def test_cli_min_score_exit_code(self) -> None:
        result = subprocess.run(
            [sys.executable, str(HERE / "scan.py"), "-", "--min-score", "90"],
            input=AI_TEXT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 1, result.stderr)


if __name__ == "__main__":
    unittest.main()
