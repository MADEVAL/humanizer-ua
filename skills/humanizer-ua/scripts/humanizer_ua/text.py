"""Текстові утиліти: читання, маскування, слова, речення, абзаци."""

from __future__ import annotations

from pathlib import Path
import codecs
import re
import sys

WORD_RE = re.compile(
    r"[А-Яа-яІіЇїЄєҐґA-Za-z0-9]+(?:['’ʼ-][А-Яа-яІіЇїЄєҐґA-Za-z0-9]+)*"
)
SENTENCE_RE = re.compile(r"(?<=[.!?…])\s+")
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")
RUSSIAN_LETTERS_RE = re.compile(r"[ёыэъЁЫЭЪ]")
CYRILLIC_RE = re.compile(r"[А-Яа-яІіЇїЄєҐґ]")
ENCODINGS = ("auto", "utf-8", "utf-8-sig", "cp1251", "utf-16")


def normalise_newlines(text: str) -> str:
    """CRLF і старий Mac CR зводяться до LF.

    Без цього frontmatter із Windows не маскується, а рядки таблиць
    і абзаци розпізнаються інакше, ніж на Linux.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _looks_like_text(text: str) -> bool:
    """Відсіює бінарний вміст і UTF-16, прочитаний як один байт на символ."""
    if "\x00" in text:
        return False
    controls = sum(1 for char in text if ord(char) < 32 and char not in "\n\r\t")
    return controls <= max(1, len(text) // 200)


def _decode_auto(data: bytes) -> str:
    if data.startswith(codecs.BOM_UTF16_LE) or data.startswith(codecs.BOM_UTF16_BE):
        return data.decode("utf-16")
    if data.startswith(codecs.BOM_UTF8):
        return data.decode("utf-8-sig")

    for candidate in ("utf-8-sig", "cp1251"):
        try:
            text = data.decode(candidate)
        except UnicodeDecodeError:
            continue
        if _looks_like_text(text):
            return text

    if b"\x00" in data:
        for candidate in ("utf-16-le", "utf-16-be"):
            try:
                text = data.decode(candidate)
            except UnicodeDecodeError:
                continue
            if _looks_like_text(text):
                return text

    raise ValueError("не вдалося визначити кодування; вкажи --encoding (utf-8, cp1251 або utf-16)")


def read_text(path: str, encoding: str = "auto") -> str:
    """Читає файл або stdin. Auto: UTF-8 (з BOM), UTF-16, потім Windows-1251."""
    if encoding not in ENCODINGS:
        raise ValueError(f"Непідтримуване кодування: {encoding}")

    if path in ("-", ""):
        data = sys.stdin.buffer.read()
    else:
        data = Path(path).read_bytes()

    if encoding == "auto":
        return normalise_newlines(_decode_auto(data))

    try:
        text = data.decode(encoding)
    except UnicodeDecodeError as error:
        raise ValueError(f"файл не читається як {encoding}: {error}") from error
    return normalise_newlines(text)


def _hide(match: re.Match[str]) -> str:
    """Замінює фрагмент невидимими символами, зберігаючи рядки.

    Пробіли тут не годяться: вони створюють фальшивий «пробіл перед
    розділовим знаком» після цитати або inline-коду.
    """
    return _hide_text(match.group(0))


def _hide_text(text: str) -> str:
    return "".join("\n" if ch == "\n" else "\u200b" for ch in text)


PROTECTED_PATTERNS = (
    r"\A---\r?\n.*?\r?\n---(?:\r?\n|\Z)",
    r"```.*?```",
    r"~~~.*?~~~",
    r"`[^`\n]*`",
    r"https?://\S+",
)

QUOTE_PATTERNS = (
    r"«[^»]*»",
    r"„[^“]*“",
    r"“[^”]*”",
    r'"[^"\n]*"',
)


def mask_segments(text: str) -> str:
    """Маскує код, URL, цитати й YAML frontmatter."""
    masked = text
    for pattern in PROTECTED_PATTERNS + QUOTE_PATTERNS:
        masked = re.sub(pattern, _hide, masked, flags=re.DOTALL)
    return masked


def mask_code_only(text: str) -> str:
    """Маскує код, URL і frontmatter, але лишає цитати.

    Потрібно нормативному шару: лапки, апострофи й тире всередині цитат
    теж треба бачити, інакше правило ніколи не спрацює.
    """
    masked = text
    for pattern in PROTECTED_PATTERNS:
        masked = re.sub(pattern, _hide, masked, flags=re.DOTALL)
    return masked


TECH_LINE_RE = re.compile(
    r"^(?:<|Rewrite|\s*(?:sudo|apt|pip|npm|docker|git|curl|wget)\s)|"
    r"%\{|->|=>|;\s*$|\};|<?php|\bIfModule\b|\bserver\s*\{|\blocation\s+/"
)


def mask_tables(text: str) -> str:
    """Маскує рядки таблиць, коду з відступом і технічні рядки.

    Це дані, а не проза: подвійні пробіли, дефіси й лапки там не помилка.
    """
    lines = []
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        technical = bool(TECH_LINE_RE.search(stripped)) and len(stripped.split()) >= 3
        if stripped.startswith("|") or line.startswith("    ") or technical:
            lines.append(_hide_text(line))
        else:
            lines.append(line)
    return "".join(lines)


def count_words(text: str) -> int:
    return len(WORD_RE.findall(text))


def sentences(text: str) -> list[str]:
    parts = [part.strip() for part in SENTENCE_RE.split(text)]
    return [part for part in parts if count_words(part) >= 3]


def line_of(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def paragraph_ids(text: str) -> list[int]:
    """Повертає індекс абзацу для кожного рядка (0-based)."""
    ids: list[int] = []
    current = 0
    for line in text.splitlines():
        if not line.strip():
            current += 1
        ids.append(current)
    return ids


def paragraph_texts(text: str) -> list[str]:
    blocks = re.split(r"\n\s*\n", text)
    return [block.strip() for block in blocks if block.strip()]


def normalise_apostrophes(text: str) -> str:
    return text.replace("’", "'").replace("ʼ", "'")


def paragraph_spans(text: str) -> list[tuple[int, int]]:
    """Повертає зміщення (початок, кінець) кожного абзацу."""
    spans: list[tuple[int, int]] = []
    position = 0
    for match in re.finditer(r"\n[ \t]*\n", text):
        if text[position : match.start()].strip():
            spans.append((position, match.start()))
        position = match.end()
    if text[position:].strip():
        spans.append((position, len(text)))
    return spans


def paragraph_at(text: str, position: int, spans: list[tuple[int, int]] | None = None) -> int:
    """Індекс абзацу для зміщення."""
    spans = spans if spans is not None else paragraph_spans(text)
    for index, (start, end) in enumerate(spans):
        if start <= position <= end:
            return index
    return max(0, len(spans) - 1)


def sentence_bounds(text: str, position: int) -> tuple[int, int]:
    """Межі речення навколо зміщення."""
    start = 0
    for match in re.finditer(r"(?<=[.!?…])\s+", text):
        if match.end() <= position:
            start = match.end()
        else:
            return start, match.start()
    return start, len(text)


# Українські та російські службові слова. Спільні для двох мов не беремо:
# «не», «на», «з/с», «до», «для» нічого не розрізняють.
UK_STOPWORDS = {
    "і", "й", "та", "що", "це", "цей", "ця", "ці", "як", "який", "яка",
    "які", "яке", "є", "бути", "буде", "щоб", "але", "або", "також",
    "його", "її", "їх", "ми", "ви", "він", "вона", "вони", "після",
    "через", "можна", "потрібно", "треба", "дуже", "ще", "вже", "коли",
    "тому", "якщо", "лише", "тільки", "між", "під", "над", "при", "про",
}
RU_STOPWORDS = {
    "и", "что", "это", "этот", "эта", "эти", "как", "который", "которая",
    "которые", "есть", "будет", "чтобы", "но", "или", "также", "его",
    "её", "их", "мы", "вы", "он", "она", "они", "после", "через", "можно",
    "нужно", "надо", "очень", "ещё", "уже", "когда", "поэтому", "если",
    "только", "между", "под", "над", "при", "про",
}
UK_LETTERS = set("іїєґІЇЄҐ")
RU_LETTERS = set("ыэъёЫЭЪЁ")

STOPWORD_RE = re.compile(r"[А-Яа-яЁёІіЇїЄєҐґ]+")
LATIN_WORD_RE = re.compile(r"[A-Za-z][A-Za-z-]*")


def has_cyrillic(text: str) -> bool:
    return CYRILLIC_RE.search(text) is not None


def cyrillic_letter_share(text: str) -> float:
    """Частка кирилиці серед авторської прози.

    Латинські слова з великої літери — це зазвичай бренди (ChatGPT, Google),
    тому вони не розбавляють українську. Код, URL і цитати маскуються:
    англомовна цитата не робить український текст «неукраїнським».
    """
    cyrillic = len(CYRILLIC_RE.findall(text))
    latin = sum(
        len(token)
        for token in LATIN_WORD_RE.findall(mask_segments(text))
        if token[0].islower()
    )
    total = cyrillic + latin
    return cyrillic / total if total else 0.0


def language_share(text: str) -> float:
    """Доля українських ознак серед українських і російських.

    1.0 — чиста українська, 0.0 — чиста російська. Текст без кирилиці
    (англійська, польська, латиниця) — 0.0, а не 1.0: інакше мовний
    страж пропускає будь-який неукраїнський текст як чистий.
    """
    if not has_cyrillic(text):
        return 0.0
    uk = 0
    ru = 0
    for match in STOPWORD_RE.finditer(text):
        token = match.group(0).lower()
        if token in UK_STOPWORDS:
            uk += 1
        elif token in RU_STOPWORDS:
            ru += 1
        uk += sum(1 for char in token if char in UK_LETTERS) * 0.5
        ru += sum(1 for char in token if char in RU_LETTERS) * 0.5
    if uk + ru == 0:
        return 1.0
    return uk / (uk + ru)


def is_ukrainian(text: str, threshold: float = 0.8) -> bool:
    if not has_cyrillic(text):
        return False
    if cyrillic_letter_share(text) < 0.5:
        return False
    if count_words(text) < 5:
        return language_share(text) >= 0.5
    return language_share(text) >= threshold
