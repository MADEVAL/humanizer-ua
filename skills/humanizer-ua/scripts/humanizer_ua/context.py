"""Контекст навколо спрацювання: словники-винятки й впевненість.

Правило без контексту — це список слів. Тут вирішується, чи слово справді
маркер: чи стоїть поруч термін, джерело, число, заперечення або
протиставлення. Впевненість детермінована: ті самі сигнали дають те саме
число на тій самій машині.
"""

from __future__ import annotations

import re

from .text import sentence_bounds

# Технічні сполуки, у яких «ключовий», «унікальний» і «ефективний» —
# термін, а не рекламний епітет. Список навмисно короткий: краще пропустити,
# ніж покарати термін.
TECH_PHRASES = (
    r"унікальн\w*\s+(?:номер|ідентифікатор|код|ключ|адрес|значення|індекс|токен|ідентифікатор)",
    r"ключов\w*\s+(?:сигнал|параметр|показник|фактор|ознак|елемент|механізм|поле|слово|кадр|біт)",
    r"ефективн\w*\s+(?:алгоритм|метод|спосіб|реалізація|швидкість|площа|потужність|відсоткова)",
    r"значн\w*\s+(?:частина|частка|обсяг|об'єм|вибірка|похибка|розбіжність)",
    r"широк\w*\s+(?:спектр|діапазон|смуга|частот)",
    r"комплексн\w*\s+(?:число|аналіз|оцінка|змінна|сполука|добриво)",
    r"інноваційн\w*\s+(?:процес|цикл|політика|діяльність|екосистема)",
)

# Джерело поруч із оцінкою робить оцінку фактом.
SOURCE_WORDS = (
    "за даними",
    "згідно з",
    "відповідно до",
    "дослідження",
    "дослідженн",
    "звіт",
    "вимір",
    "статистик",
    "аналіз",
    "опитуванн",
    "джерело",
    "згідно",
    "за оцінкою",
    "за розрахунком",
)

CONTRAST_WORDS = ("але", "проте", "однак", "а й", "натомість", "хоча", "зате")

NEGATION_WORDS = ("не", "ні", "без", "жодн", "ані")

# Одиниці й символи, які роблять оцінку вимірюваною.
MEASURE_RE = re.compile(r"\d|%|відсотк|раз(?:и|ів)|грн|₴|\$|€")

SEVERITY_BASE = {"error": 0.95, "warning": 0.8, "info": 0.65}


def _window(text: str, start: int, end: int, size: int = 45) -> str:
    return text[max(0, start - size) : end + size].lower()


def allowlisted(rule: dict, text: str, start: int, end: int) -> str | None:
    """Повертає назву винятку, якщо спрацювання стоїть у терміні."""
    window = _window(text, start, end)
    for pattern in rule.get("allow", ()):
        if re.search(pattern, window, flags=re.IGNORECASE):
            return pattern
    for pattern in TECH_PHRASES:
        if re.search(pattern, window, flags=re.IGNORECASE):
            return "tech"
    return None


def has_source(text: str, start: int, end: int) -> bool:
    left, right = sentence_bounds(text, start)
    sentence = text[left:right].lower()
    return any(word in sentence for word in SOURCE_WORDS)


def has_contrast(text: str, start: int, end: int) -> bool:
    left, right = sentence_bounds(text, start)
    sentence = text[left:right].lower()
    return any(word in sentence for word in CONTRAST_WORDS)


def has_negation(text: str, start: int) -> bool:
    before = text[max(0, start - 25) : start].lower()
    return any(re.search(rf"\b{word}", before) for word in NEGATION_WORDS)


def has_measure(text: str, start: int, end: int, size: int = 50) -> bool:
    return MEASURE_RE.search(text[end : end + size]) is not None


def confidence(rule: dict, text: str, start: int, end: int, genre: str) -> float:
    """0–1: наскільки спрацювання схоже на справжній маркер у цьому місці.

    Сигнали навмисно прості й симетричні: термін або джерело знижують
    впевненість, вимірювана оцінка теж, а сама лише форма без підтримки
    лишається високою.
    """
    severity = rule.get("severity", "warning")
    value = SEVERITY_BASE.get(severity, 0.7)

    if allowlisted(rule, text, start, end):
        value = min(value, 0.3)

    if rule.get("source_aware") and has_source(text, start, end):
        value -= 0.2

    if rule.get("contrast_aware") and has_contrast(text, start, end):
        value -= 0.15

    if rule.get("measure_aware") and has_measure(text, start, end):
        value -= 0.15

    if rule.get("negation_aware") and has_negation(text, start):
        value -= 0.2

    if genre in ("legal", "academic") and rule.get("layer") == "style":
        value -= 0.1

    return round(min(1.0, max(0.3, value)), 2)
