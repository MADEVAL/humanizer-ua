#!/usr/bin/env python3
"""Повний набір прикладів для кожного правила сканера."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from humanizer_ua.rules import HARD_BANS, MARKERS  # noqa: E402
from humanizer_ua.score import build_report  # noqa: E402

POSITIVE_HARD = {
    "HB01": "У сучасному світі це важливо.",
    "HB02": "Варто зазначити, що це працює.",
    "HB03": "Не секрет, що це працює.",
    "HB04": "Даний інструмент працює.",
    "HB05": "Це являється проблемою.",
    "HB06": "Це відіграє важливу роль.",
    "HB07": "Це є невід'ємною частиною.",
    "HB08": "Це відкриває нові горизонти.",
    "HB09": "Потрібен комплексний підхід.",
    "HB10": "У рамках проєкту це працює.",
    "HB11": "З метою покращення це робимо.",
    "HB12": "Таким чином, це працює.",
    "HB13": "Це не просто оновлення.",
    "HB14": "Це не проблема. Це можливість.",
    "HB15": "Давайте розберемося.",
    "HB16": "Це дійсно працює.",
    "HB17": "Це значний результат.",
    "HB18": "Це ключовий показник.",
    "HB19": "Ми приймаємо участь.",
    "HB20": "На протязі року це працює.",
    "HB21": "Так як це працює, ми йдемо.",
    "HB22": "Згідно наказу це працює.",
    "HB23": "Слідуючий крок — це перевірка.",
    "HB24": "Здійснюється перевірка.",
    "HB25": "Експерти вважають, що це працює.",
    "HB26": "Це успішно працює.",
    "HB27": "Це має місце.",
    "HB28": "В силу обставин це працює.",
    "HB29": "З точки зору клієнта це працює.",
    "HB30": "На сьогоднішній день це працює.",
}

POSITIVE_MARKERS = {
    "A3": "Ось у чому справжня сила.",
    "A4": "У своїй основі це про людей.",
    "A6": "Хтось скаже, що це складно.",
    "A7": "Чому? Бо це працює.",
    "A8": "Підсумую: це працює.",
    "B3": "Це інструмент, який допомагає команді, яка працює віддалено.",
    "B6": "Існуючі проблеми треба вирішувати.",
    "B11": "Це працює, підкреслюючи важливість.",
    "C1": "Ми відносимося до цього серйозно.",
    "C2": "Отримали фідбек від команди.",
    "C5": "Це виводить на новий рівень.",
    "C9": "Можливо, ймовірно, це працює.",
    "C11": "Це пов'язано з керівництвом.",
    "C12": "Галерея служить як простір.",
    "D8": "Це високо-якісний продукт.",
    "E1": "Гарне питання! Ось огляд.",
    "E2": "Станом на 2025 рік це працює.",
    "E4": "Ця стаття розповідає про це.",
    "E5": "Примітка для редакції: перевірити.",
    "G1": "Вона і він прийшли.",
    "G5": "Було прийнято рішення.",
}


def found_ids(text: str, genre: str = "marketing") -> set[str]:
    report = build_report(text, genre, None)
    return {item["id"] for item in report["hard_bans"] + report["markers"]}


class RuleCoverageTests(unittest.TestCase):
    def test_every_hard_ban_has_example(self) -> None:
        self.assertEqual(set(POSITIVE_HARD), {rule["id"] for rule in HARD_BANS})

    def test_every_marker_has_example(self) -> None:
        self.assertEqual(set(POSITIVE_MARKERS), {rule["id"] for rule in MARKERS})

    def test_all_hard_bans_match(self) -> None:
        for rule_id, text in POSITIVE_HARD.items():
            with self.subTest(rule=rule_id):
                self.assertIn(rule_id, found_ids(text))

    def test_all_markers_match(self) -> None:
        for rule_id, text in POSITIVE_MARKERS.items():
            with self.subTest(rule=rule_id):
                self.assertIn(rule_id, found_ids(text))

    def test_correct_phrases_are_not_flagged(self) -> None:
        text = (
            "Згідно з наказом і завдяки підтримці це працює. "
            "Любий друг може допомогти. "
            "У статті розглядається термін «являється». "
            "`У сучасному світі` — це код."
        )
        self.assertEqual(found_ids(text), set())

    def test_genre_exemptions(self) -> None:
        cases = [
            ("Даний закон регулює відносини.", "academic", "HB04"),
            ("Це не просто оновлення, це новий етап.", "fiction", "HB13"),
            ("Це пов'язано з керівництвом.", "legal", "C11"),
            ("Це високо-якісний продукт.", "docs", "D8"),
            ("Вона і він прийшли.", "docs", "G1"),
        ]
        for text, genre, rule_id in cases:
            with self.subTest(rule=rule_id, genre=genre):
                self.assertNotIn(rule_id, found_ids(text, genre))

    def test_weak_signal_needs_company(self) -> None:
        alone = build_report("Це дійсно працює.", "marketing", None)
        self.assertEqual(alone["counts"]["weak_alone"], 1)
        self.assertEqual(alone["penalties"]["hard_bans"], 0)

        company = build_report("У сучасному світі це дійсно працює.", "marketing", None)
        self.assertGreater(company["penalties"]["hard_bans"], 0)

    def test_fact_claims_are_protected(self) -> None:
        before = "Це перший такий сервіс в Україні. Він може допомогти 40 % команд."
        after = "Це сервіс. Він допоможе 40 % команд."
        report = build_report(after, "marketing", before)
        lost = " ".join(report["fact_lock"]["lost"])
        self.assertIn("перший", lost)
        self.assertIn("може", lost)


if __name__ == "__main__":
    unittest.main()
