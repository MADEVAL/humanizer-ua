"""Факт-замок: що з фактів джерела дожило до чистовика.

Не фактчек і не семантика. Перевіряє лише збереження вже наявних
елементів і появу нових: числа, величини, дати, місяці, посилання,
код, цитати, імена, квантори, оговорки, розмітку.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from .rules import NAME_STOPLIST
from .text import normalise_apostrophes, sentences

MONTH_RE = re.compile(
    r"\b(січн|лют|берез|квіт|трав|черв|лип|серп|верес|жовт|листоп|груд)\w*\b",
    re.IGNORECASE,
)
DATE_RE = re.compile(
    r"\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b"
    r"|\b\d{1,2}\s+(?:січня|лютого|березня|квітня|травня|червня|липня|серпня|вересня|жовтня|листопада|грудня)\s+\d{4}\b",
    re.IGNORECASE,
)
URL_RE = re.compile(r"https?://[^\s)>\]»]+|\b[a-z0-9-]+\.(?:ua|com|org|net|io|dev|ai)(?:/[^\s)>\]»]*)?", re.IGNORECASE)
CODE_RE = re.compile(r"`([^`\n]+)`")
QUOTE_RE = re.compile(r"«([^»]{1,200})»|“([^”]{1,200})”|\"([^\"\n]{1,200})\"")
NUMBER_RE = re.compile(r"(?<![A-Za-zА-Яа-яІіЇїЄєҐґ0-9_])[-+−]?(?:\d{1,3}(?:[ \u00A0]\d{3})+|\d+)(?:[.,]\d+)?")
UNIT_RE = re.compile(
    r"\s*(%|відсотк\w*|грн|₴|\$|€|млн\.?|мільйон\w*|млрд\.?|мільярд\w*|тис\.?|тисяч\w*|км|кг|см|мм|га|гб|мб|тб|мг|мл|л)(?![а-яіїєґa-z])",
    re.IGNORECASE,
)
NAME_RE = re.compile(r"\b[А-ЯІЇЄҐ][а-яіїєґ'’ʼ-]{2,}\b")
TOKEN_RE = re.compile(r"[А-Яа-яІіЇїЄєҐґA-Za-z0-9]+(?:['’ʼ-][А-Яа-яІіЇїЄєҐґA-Za-z0-9]+)*")

SOFT_NUMERALS = {
    "один", "одна", "одне", "два", "дві", "три", "пара", "половина",
    "третина", "чверть", "півтора", "вдвічі", "втричі", "двічі", "тричі",
    "другий", "третій",
}
HARD_NUMERALS = {
    "чотири", "п'ять", "шість", "сім", "вісім", "дев'ять", "десять",
    "одинадцять", "дванадцять", "п'ятнадцять", "двадцять", "тридцять",
    "сорок", "п'ятдесят", "шістдесят", "сімдесят", "вісімдесят",
    "дев'яносто", "сто", "двісті", "триста", "тисяча", "мільйон",
    "мільярд", "десяток", "сотня", "дюжина",
}
CLAIM_WORDS = {
    "перший", "перша", "перше", "перші", "єдиний", "єдина", "єдине",
    "вперше", "найбільший", "найбільша", "найкращий", "найкраща",
    "рекордний", "рекордна", "найстаріший",
    "ніколи", "ніхто", "назавжди", "безпрецедентний",
    "найшвидший", "найдешевший",
}
CLAIM_RE = re.compile(
    r"\b(?:перш(?:ий|а|е|і|ого|ому|им|их)|єдин(?:ий|а|е|і|ого|ому|им|их)|"
    r"вперше|найбільш(?:ий|а|і|ого|ому|им|их)|найкращ(?:ий|а|і|ого|ому|им|их)|"
    r"рекордн\w*|найстарш(?:ий|а|і|ого|ому|им|их)|ніколи|ніхто|"
    r"назавжди|безпрецедентн\w*|найшвидш(?:ий|а|і|ого|ому|им|их)|"
    r"найдешевш(?:ий|а|і|ого|ому|им|их))\b",
    re.IGNORECASE,
)
CLAIM_PHRASE_RE = re.compile(r"\bдо\s+цього\s+часу\b|\bу\s+світі\b|\bв\s+Україні\b|\bна\s+ринку\b", re.IGNORECASE)
HEDGE_RE = re.compile(
    r"\b(?:може|можуть|можлив\w*|ймовірно|зазвичай|як\s+правило|часто|іноді|"
    r"приблизно|близько|майже|у\s+середньому|не\s+обов'язково|не\s+завжди|"
    r"ризик\w*|один\s+із|одна\s+з|лише|тільки|якщо|за\s+даними|"
    r"(?:від|до|понад|більше|менше|не\s+більше|не\s+менше)(?=\s+\d))\b",
    re.IGNORECASE,
)
STRUCTURE_RE = {
    "заголовок": re.compile(r"^[ \t]{0,3}#{1,6}[ \t]+\S", re.MULTILINE),
    "пункт списку": re.compile(r"^[ \t]*(?:[-*+•]|\d{1,3}[.)])[ \t]+\S", re.MULTILINE),
    "рядок таблиці": re.compile(r"^[ \t]*\|.*\|[ \t]*$", re.MULTILINE),
}
EMPHASIS_RE = {
    "жирний": re.compile(r"\*\*[^*\n]+\*\*|__[^_\n]+__"),
    "курсив": re.compile(r"(?<![*\w])\*[^*\s][^*\n]*\*(?![*\w])"),
}


@dataclass
class Facts:
    hard: set[str] = field(default_factory=set)
    soft: set[str] = field(default_factory=set)
    words: set[str] = field(default_factory=set)
    claims: set[str] = field(default_factory=set)
    hedges: set[str] = field(default_factory=set)
    display: dict[str, str] = field(default_factory=dict)


@dataclass
class FactsDiff:
    lost: list[str]
    added: list[str]
    kept: int
    soft_added: list[str]
    claims_added: list[str]
    emphasis_lost: list[str]
    markup_lost: list[str]
    lost_keys: list[str] = field(default_factory=list, repr=False)
    added_keys: list[str] = field(default_factory=list, repr=False)

    @property
    def ok(self) -> bool:
        return not (
            self.lost
            or self.added
            or self.soft_added
            or self.claims_added
            or self.emphasis_lost
            or self.markup_lost
        )

    @property
    def status(self) -> str:
        return "no_detected_changes" if self.ok else "review_required"

    @property
    def penalty(self) -> int:
        hard_prefixes = {"число", "величина", "дата", "місяць", "посилання", "код", "цитата", "ім'я", "число словами"}
        lost_hard = sum(1 for item in self.lost_keys if item.split(":", 1)[0] in hard_prefixes)
        added_hard = sum(1 for item in self.added_keys if item.split(":", 1)[0] in hard_prefixes)
        lost_soft = len(self.lost_keys) - lost_hard
        added_claims = len(self.claims_added)
        return min(
            40,
            lost_hard * 6
            + added_hard * 8
            + lost_soft * 2
            + added_claims * 3
            + len(self.markup_lost) * 2
            + len(self.emphasis_lost),
        )

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "status": self.status,
            "lost": self.lost,
            "added": self.added,
            "kept": self.kept,
            "soft_added": self.soft_added,
            "claims_added": self.claims_added,
            "emphasis_lost": self.emphasis_lost,
            "markup_lost": self.markup_lost,
            "penalty": self.penalty,
            "scope": "Зіставлено витягнені елементи; смисл і зв'язок чисел з твердженнями потребують ручної звірки.",
        }


def _unit(raw: str) -> str:
    lowered = raw.lower()
    if lowered.startswith("відсотк") or lowered == "%":
        return "%"
    if lowered in {"₴", "грн"}:
        return "грн"
    if lowered in {"$", "€"}:
        return lowered
    if lowered.startswith(("млн", "мільйон")):
        return "млн"
    if lowered.startswith(("млрд", "мільярд")):
        return "млрд"
    if lowered.startswith(("тис", "тисяч")):
        return "тис"
    return lowered


def _value(raw: str) -> str:
    value = re.sub(r"[ \u00A0]", "", raw).replace(",", ".").replace("−", "-")
    if value.startswith("+"):
        value = value[1:]
    if re.fullmatch(r"-?\d+", value):
        value = str(int(value))
    return value


def numeric_facts(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for match in NUMBER_RE.finditer(text):
        value = _value(match.group(0))
        end = match.end()
        units: list[str] = []
        for _ in range(2):
            unit_match = UNIT_RE.match(text, end)
            if not unit_match:
                break
            unit = _unit(unit_match.group(1))
            units.append(unit)
            end = unit_match.end()
            if unit in {"%", "грн", "$", "€"}:
                break
        if units:
            result["величина:" + value + " " + " ".join(units)] = text[match.start() : end].strip()
        else:
            result["число:" + value] = match.group(0)
    return result


def _sentence_starts(text: str) -> set[int]:
    starts = {0}
    for match in re.finditer(r"[.!?…:;—–]\s+|\n|^[ \t]*(?:[-*+•]|\d{1,3}[.)]|#{1,6})\s*", text, re.MULTILINE):
        starts.add(match.end())
    return starts


def _is_name(token: str, at_start: bool) -> bool:
    if not token[:1].isupper():
        return False
    if token.isascii():
        return True
    if token in NAME_STOPLIST:
        return False
    if at_start:
        return False
    return NAME_RE.fullmatch(token) is not None


def _add(facts: Facts, target: set[str], key: str, display: str) -> None:
    target.add(key)
    facts.display.setdefault(key, display)


def extract_facts(text: str) -> Facts:
    facts = Facts()
    body = normalise_apostrophes(text)

    for match in URL_RE.finditer(body):
        url = re.sub(r"^https?://(?:www\.)?", "", match.group(0).rstrip(".,;:").lower()).rstrip("/")
        _add(facts, facts.hard, "посилання:" + url, url)
    for match in CODE_RE.finditer(body):
        _add(facts, facts.hard, "код:" + match.group(1).strip(), match.group(1).strip())
    for match in QUOTE_RE.finditer(body):
        value = next(group for group in match.groups() if group is not None).strip()
        value = re.sub(r"\s+", " ", value)
        _add(facts, facts.hard, "цитата:" + value, value)
    for match in DATE_RE.finditer(body):
        _add(facts, facts.hard, "дата:" + match.group(0), match.group(0))

    body_without_dates = DATE_RE.sub(" ", body)
    for match in MONTH_RE.finditer(body_without_dates):
        _add(facts, facts.hard, "місяць:" + match.group(1).lower(), match.group(0))
    for key, display in numeric_facts(body_without_dates).items():
        _add(facts, facts.hard, key, display)

    for match in HEDGE_RE.finditer(body):
        phrase = re.sub(r"\s+", " ", match.group(0).lower())
        key = "може" if phrase.startswith("можлив") else phrase
        _add(facts, facts.hedges, "оговорка:" + key, phrase)
    for match in CLAIM_RE.finditer(body):
        phrase = match.group(0).lower()
        _add(facts, facts.claims, "квантор:" + phrase, match.group(0))
    for match in CLAIM_PHRASE_RE.finditer(body):
        phrase = match.group(0).lower()
        _add(facts, facts.claims, "квантор:" + phrase, match.group(0))

    starts = _sentence_starts(body)
    for match in TOKEN_RE.finditer(body):
        token = match.group(0)
        if token[0].isdigit():
            continue
        lower = token.lower()
        facts.words.add(lower)
        # «**Ціна:**» і «Причина:» — це підписи, а не власні назви.
        # Інакше видалення болд-декору виглядає як втрата трьох фактів.
        after = body[match.end() : match.end() + 1]
        before = body[max(0, match.start() - 2) : match.start()]
        label = after == ":" or before == "**"
        if lower in SOFT_NUMERALS:
            _add(facts, facts.soft, "кількість:" + lower, token)
        elif lower in HARD_NUMERALS:
            _add(facts, facts.hard, "число словами:" + lower, token)
        elif lower in CLAIM_WORDS:
            _add(facts, facts.claims, "квантор:" + lower, token)
        elif not label and lower not in CLAIM_WORDS and _is_name(token, match.start() in starts):
            _add(facts, facts.hard, "ім'я:" + lower, token)

    return facts


def markup_counts(text: str) -> tuple[dict[str, int], dict[str, int]]:
    structure = {name: len(pattern.findall(text)) for name, pattern in STRUCTURE_RE.items()}
    emphasis = {name: len(pattern.findall(text)) for name, pattern in EMPHASIS_RE.items()}
    return structure, emphasis


def _show(keys: list[str], facts: Facts) -> list[str]:
    return [facts.display.get(key, key) for key in keys]


def diff_facts(before: str, after: str) -> FactsDiff:
    b = extract_facts(before)
    a = extract_facts(after)

    lost_keys = sorted(b.hard - a.hard) + sorted(b.claims - a.claims) + sorted(b.hedges - a.hedges)
    added_keys = sorted(a.hard - b.hard) + sorted(a.claims - b.claims)
    soft_keys = sorted(a.soft - b.soft)

    before_structure, before_emphasis = markup_counts(before)
    after_structure, after_emphasis = markup_counts(after)
    markup_lost = [
        f"розмітка:{name} {before_structure[name]}→{after_structure[name]}"
        for name in before_structure
        if after_structure[name] < before_structure[name]
    ]
    emphasis_lost = [
        f"виділення:{name} {before_emphasis[name]}→{after_emphasis[name]}"
        for name in before_emphasis
        if after_emphasis[name] < before_emphasis[name]
    ]

    return FactsDiff(
        lost=_show(lost_keys, b),
        added=_show(added_keys, a),
        kept=len(b.hard & a.hard),
        soft_added=_show(soft_keys, a),
        claims_added=_show(sorted(a.claims - b.claims), a),
        emphasis_lost=emphasis_lost,
        markup_lost=markup_lost,
        lost_keys=lost_keys,
        added_keys=added_keys,
    )


def facts_verdict(diff: FactsDiff) -> str:
    if diff.added:
        return f"з'явилися елементи, яких немає в джерелі: {len(diff.added)}"
    if diff.lost:
        return f"втрачено елементів джерела: {len(diff.lost)}"
    if diff.claims_added or diff.soft_added or diff.emphasis_lost:
        return "з'явилися квантори або кількості; перевір контекст"
    return f"зіставлено елементів: {diff.kept}; змін не знайдено"


SOURCE_WORDS = (
    "за даними",
    "згідно",
    "відповідно до",
    "дослідження",
    "звіт",
    "вимір",
    "статистик",
    "опитуванн",
    "джерело",
    "за оцінкою",
)

RANGE_RE = re.compile(r"\bвід\s+(\d+(?:[.,]\d+)?)\s+до\s+(\d+(?:[.,]\d+)?)", re.IGNORECASE)
VAGUE_RE = re.compile(r"\b(?:понад|майже|близько|приблизно)\s+\d+(?:[.,]\d+)?\s*%?", re.IGNORECASE)
# «Перший крок» — це порядок дій, а не рекорд. Такі порядкові не
# вважаємо кванторами без джерела.
ORDINAL_STEP_RE = re.compile(r"^\s*(?:крок|раз|пункт|етап|черга|дія|спроба|варіант)\b", re.IGNORECASE)
ORDINAL_WORDS = {"перший", "перша", "перше", "перші", "другий", "друга", "друге", "другі"}


def _sentence_around(text: str, position: int) -> str:
    left = max(text.rfind(mark, 0, position) for mark in (".", "!", "?", "\n"))
    right_candidates = [index for index in (text.find(".", position), text.find("!", position), text.find("?", position), text.find("\n", position)) if index != -1]
    right = min(right_candidates) if right_candidates else len(text)
    return text[max(0, left + 1) : right]


def _has_source(sentence: str) -> bool:
    lowered = sentence.lower()
    return any(word in lowered for word in SOURCE_WORDS)


def ledger(text: str) -> dict:
    """Реєстр фактів без оригіналу: що є й що варто перевірити.

    Нічого не «перевіряє в інтернеті»: сумнівне позначає needs_review.
    """
    facts = extract_facts(text)
    entities = []
    for key in sorted(facts.hard):
        kind, _, value = key.partition(":")
        entities.append({"kind": kind, "value": facts.display.get(key, value)})
    for key in sorted(facts.claims):
        kind, _, value = key.partition(":")
        entities.append({"kind": kind, "value": facts.display.get(key, value)})

    risks = []

    for match in RANGE_RE.finditer(text):
        low = float(match.group(1).replace(",", "."))
        high = float(match.group(2).replace(",", "."))
        if low > high:
            risks.append(
                {
                    "kind": "діапазон навпаки",
                    "quote": match.group(0),
                    "needs_review": True,
                }
            )

    for match in VAGUE_RE.finditer(text):
        sentence = _sentence_around(text, match.start())
        if not _has_source(sentence):
            risks.append(
                {
                    "kind": "псевдоточність без джерела",
                    "quote": match.group(0),
                    "needs_review": True,
                }
            )

    for key in sorted(facts.claims):
        display = facts.display.get(key, "")
        if not display:
            continue
        position = text.lower().find(display.lower())
        if position == -1:
            continue
        if display.lower() in ORDINAL_WORDS and ORDINAL_STEP_RE.match(text[position + len(display) :]):
            continue
        sentence = _sentence_around(text, position)
        if not _has_source(sentence):
            risks.append(
                {
                    "kind": "квантор без джерела",
                    "quote": display,
                    "needs_review": True,
                }
            )
        if len(risks) >= 12:
            break

    return {
        "entities": entities[:60],
        "risks": risks[:12],
        "note": "Реєстр лише показує елементи. Зв'язок числа з твердженням перевіряє людина.",
    }


def sentence_spans(text: str) -> list[str]:
    return sentences(text)
