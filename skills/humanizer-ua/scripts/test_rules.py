#!/usr/bin/env python3
"""Приклади для кожного правила й перевірка калібрування."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from humanizer_ua.norm import NORM_RULES  # noqa: E402
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
    "HB13": "Це не просто оновлення, а новий етап.",
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
    "A9": "У цій статті ми розглянемо, як працює кеш.",
    "A10": "Підсумовуючи, це працює.",
    "A11": "Це найкращий вибір для стартапів.",
    "B3": "Це інструмент, який допомагає команді, яка працює віддалено, яка потребує звітів.",
    "B6": "Існуючі проблеми треба вирішувати.",
    "B11": "Це працює, підкреслюючи важливість.",
    "B12": "Він працює, забезпечуючи стійкість.",
    "B13": "Процес забезпечення реалізації оптимізації.",
    "B14": "Це робить транзакції безклопітними.",
    "C1": "Ми відносимося до цього серйозно.",
    "C2": "Отримали фідбек від команди.",
    "C5": "Це виводить на новий рівень.",
    "C9": "Можливо, ймовірно, це працює.",
    "C11": "Це пов'язано з керівництвом.",
    "C12": "Галерея служить як простір.",
    "C13": "Вона пропонує зручний досвід.",
    "C14": "Це є ключем до успіху.",
    "C17": "Понад 90 % компаній обирають це.",
    "D8": "Це високо-якісний продукт.",
    "D9": "## Часті запитання",
    "D10": "## Що це?\n\n## Навіщо?\n\n## Кому?",
    "E1": "Гарне питання! Ось огляд.",
    "E2": "Схоже, що це працює.",
    "E4": "Ця стаття розповідає про це.",
    "E5": "Примітка для редакції: перевірити.",
    "F10": "Усі знають, що це працює.",
    "G1": "Вона і він прийшли.",
    "G5": "Було прийнято рішення.",
}

POSITIVE_NORM = {
    "N01": "Це - помилка.",
    "N02": "Тут з\\’єднання і пов\\’язані.",
    "N03": 'Він сказав "проєкт" і пішов.',
    "N04": "Слово , далі текст.",
    "N05": "Два  пробіли в реченні.",
    "N06": "Зростання 5% за рік.",
    "N07": "Це тривало 10-20 років.",
    "N08": "Текст\u00a0 .",
    "N13": "Це проэкт із ёлкою.",
    "N14": "Сайт працює, сайт росте.",
    "N15": "Він відкрив WоrdPress.",
}


def ids(text: str, genre: str = "marketing") -> set[str]:
    report = build_report(text, genre, None)
    return {item["id"] for item in report["hard_bans"] + report["markers"] + report["norm"]}


def report(text: str, genre: str = "marketing") -> dict:
    return build_report(text, genre, None)


def finding(text: str, rule_id: str) -> dict | None:
    for item in report(text)["findings"]:
        if item.get("rule_id") == rule_id:
            return item
    return None


class RuleCoverageTests(unittest.TestCase):
    def test_every_hard_ban_has_example(self) -> None:
        self.assertEqual(set(POSITIVE_HARD), {rule["id"] for rule in HARD_BANS})

    def test_every_marker_has_example(self) -> None:
        self.assertEqual(set(POSITIVE_MARKERS), {rule["id"] for rule in MARKERS})

    def test_every_norm_rule_has_example(self) -> None:
        self.assertEqual(set(POSITIVE_NORM), {rule["id"] for rule in NORM_RULES})

    def test_norm_ids_exist_in_hard_bans(self) -> None:
        docs = (HERE.parent / "references" / "hard-bans.md").read_text(encoding="utf-8")
        for rule in NORM_RULES:
            with self.subTest(rule=rule["id"]):
                self.assertIn(f"**{rule['id']}**", docs)

    def test_all_hard_bans_match(self) -> None:
        for rule_id, text in POSITIVE_HARD.items():
            with self.subTest(rule=rule_id):
                self.assertIn(rule_id, ids(text))

    def test_all_markers_match(self) -> None:
        for rule_id, text in POSITIVE_MARKERS.items():
            with self.subTest(rule=rule_id):
                self.assertIn(rule_id, ids(text))

    def test_all_norm_rules_match(self) -> None:
        for rule_id, text in POSITIVE_NORM.items():
            with self.subTest(rule=rule_id):
                self.assertIn(rule_id, ids(text))

    def test_correct_phrases_are_not_flagged(self) -> None:
        text = (
            "Згідно з наказом і завдяки підтримці це працює. "
            "Любий друг може допомогти. "
            "У статті розглядається термін «являється». "
            "`У сучасному світі` — це код."
        )
        self.assertEqual(ids(text), set())

    def test_genre_exemptions(self) -> None:
        cases = [
            ("Даний закон регулює відносини.", "academic", "HB04"),
            ("Це не просто оновлення, а новий етап.", "fiction", "HB13"),
            ("Це пов'язано з керівництвом.", "legal", "C11"),
            ("Це високо-якісний продукт.", "docs", "D8"),
            ("Вона і він прийшли.", "docs", "G1"),
            ("У цій статті ми розглянемо метод.", "academic", "A9"),
        ]
        for text, genre, rule_id in cases:
            with self.subTest(rule=rule_id, genre=genre):
                self.assertNotIn(rule_id, ids(text, genre))

    def test_weak_signal_needs_company(self) -> None:
        alone = report("Це дійсно працює.")
        self.assertEqual(alone["counts"]["weak_alone"], 1)
        self.assertEqual(alone["penalties"]["hard_bans"], 0)

        company = report("У сучасному світі це дійсно працює.")
        self.assertGreater(company["scores"]["style"], 0)
        self.assertLess(company["scores"]["style"], 100)

    def test_fact_claims_are_protected(self) -> None:
        before = "Це перший такий сервіс в Україні. Він може допомогти 40 % команд."
        after = "Це сервіс. Він допоможе 40 % команд."
        report = build_report(after, "marketing", before)
        lost = " ".join(report["fact_lock"]["lost"])
        self.assertIn("перший", lost)
        self.assertIn("може", lost)


class CalibrationTests(unittest.TestCase):
    """Хибні спрацювання, які знайшов аудит, не мають повертатися."""

    def test_contrast_without_second_part_is_not_flagged(self) -> None:
        self.assertIsNone(finding("Це не просто оновлення. Далі — факти.", "HB13"))

    def test_meaningful_contrast_costs_little(self) -> None:
        item = finding(
            "Ключ до швидкого проєкту лежить не лише в обладнанні, а й у тому, як платформа обробляє трафік.",
            "HB13",
        )
        self.assertIsNotNone(item)
        self.assertLessEqual(item["penalty"], 4)

    def test_technical_term_is_not_penalized(self) -> None:
        item = finding("ASN — це унікальний номер, що присвоюється кожній автономній системі.", "HB18")
        self.assertTrue(item is None or item["penalty"] == 0)

    def test_source_makes_quantity_legitimate(self) -> None:
        item = finding("За даними Cloudflare, значна частина шкідливих запитів надходить з IP-адрес.", "HB17")
        self.assertTrue(item is None or item["penalty"] < 3)

    def test_product_heading_is_not_title_case(self) -> None:
        text = "## Майстерність веброзробки: PHP, Laravel, WordPress, Magento, Bootstrap\n\nТекст."
        ids_here = {item["id"] for item in report(text, "docs")["metrics"]}
        self.assertNotIn("title_case", ids_here)

    def test_tech_names_are_not_english_noise(self) -> None:
        text = (
            "WordPress, Cloudflare, API і CLI працюють разом. "
            "Плагін ставить WordPress і Cloudflare в один ланцюг."
        )
        ids_here = {item["id"] for item in report(text)["metrics"]}
        self.assertNotIn("english", ids_here)

    def test_conditions_are_not_hedges(self) -> None:
        text = (
            "Якщо користувач може увійти, він часто бачить звіт. "
            "Іноді це зазвичай працює, але не завжди."
        )
        ids_here = {item["id"] for item in report(text)["metrics"]}
        self.assertNotIn("hedges", ids_here)

    def test_one_rule_cannot_zero_the_text(self) -> None:
        filler = " ".join(["Команда працює з даними щодня."] * 60)
        text = filler + " Це не просто звіт, а сигнал. Ще один: це не просто факт, а вимір."
        scores = report(text)["scores"]
        self.assertGreater(scores["style"], 80)

    def test_markdown_list_is_not_a_dash_error(self) -> None:
        text = "- перший пункт\n- другий пункт\n\nДіапазон 10–20 років."
        self.assertIsNone(finding(text, "N01"))

    def test_determinism(self) -> None:
        text = "У сучасному світі це не просто звіт, а сигнал. Слово  слово."
        first = json.dumps(report(text), ensure_ascii=False, sort_keys=True)
        second = json.dumps(report(text), ensure_ascii=False, sort_keys=True)
        self.assertEqual(first, second)

    def test_error_blocks_clean_band(self) -> None:
        from humanizer_ua import scoring

        perfect = {"norm": 100.0, "style": 100.0, "structure": 100.0}
        self.assertEqual(scoring.band(95, perfect, "marketing", errors=False), "чисто")
        self.assertEqual(scoring.band(95, perfect, "marketing", errors=True), "правка")

    def test_fact_ledger_without_before(self) -> None:
        report_here = report("Зростання понад 40 % за два роки. Це перший такий сервіс.")
        self.assertTrue(report_here["facts"]["entities"])
        kinds = {risk["kind"] for risk in report_here["facts"]["risks"]}
        self.assertIn("псевдоточність без джерела", kinds)

    def test_fact_risk_counts_ledger_risks_without_before(self) -> None:
        report_here = report("Понад 40 % команд обрали це. Це найбільший показник.")
        self.assertGreater(len(report_here["facts"]["risks"]), 0)
        self.assertGreater(report_here["scores"]["fact_risk"], 0)

    def test_bold_labels_are_not_lost_names(self) -> None:
        before = "**Головне:** продукт працює. **Ціна:** доступна."
        after = "Продукт працює. Ціна доступна."
        report_here = build_report(after, "marketing", before)
        self.assertEqual(report_here["fact_lock"]["lost"], [])

    def test_ordinary_business_phrases_are_not_errors(self) -> None:
        text = (
            "Станом на 1 жовтня 2026 року ми маємо 12 клієнтів. "
            "Дайте знати, якщо потрібні уточнення. "
            "Дякуючи за допомогу, ми завершили проєкт. "
            "Мені здається, що це правильне рішення. "
            "Це була остання крапка. Прийшов в офіс. "
            "Прапор синьо-жовтий. Він володіє англійською мовою."
        )
        report_here = report(text, "business")
        error_ids = {
            item["id"]
            for item in report_here["hard_bans"] + report_here["norm"]
            if item["severity"] == "error"
        }
        self.assertEqual(error_ids, set())
        flagged = {item["id"] for item in report_here["findings"]}
        self.assertNotIn("E2", flagged)
        self.assertNotIn("D8", flagged)
        self.assertNotIn("G1", flagged)
        self.assertNotIn("C12", flagged)

    def test_english_curly_quotes_are_not_a_norm_error(self) -> None:
        self.assertIsNone(finding("Він сказав “yes” і пішов.", "N03"))
        self.assertIsNotNone(finding("Він сказав “текст” і пішов.", "N03"))

    def test_zvisno_is_only_a_wrapper_when_standalone(self) -> None:
        self.assertIsNone(finding("Звісно, це нормальне пояснення.", "E1"))
        self.assertIsNotNone(finding("Звісно!", "E1"))

    def test_short_text_skips_density_metrics(self) -> None:
        report_here = report("Це коротке оновлення. Оновлення стосується розвитку. Розвиток триває.")
        metric_ids = {item["id"] for item in report_here["metrics"]}
        self.assertNotIn("nominalization", metric_ids)

    def test_fiction_dialogue_is_not_decoration(self) -> None:
        text = "Вона всміхнулася. 😊\n\n— Ти прийшла, — сказав він. — Я чекав."
        metric_ids = {item["id"] for item in report(text, "fiction")["metrics"]}
        self.assertNotIn("emoji", metric_ids)
        self.assertNotIn("dash", metric_ids)
        self.assertNotIn("staccato", metric_ids)


if __name__ == "__main__":
    unittest.main()
