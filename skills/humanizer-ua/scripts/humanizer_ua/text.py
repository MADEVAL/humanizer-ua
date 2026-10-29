"""Текстові утиліти: читання, маскування, слова, речення, абзаци."""

from __future__ import annotations

from pathlib import Path
import re
import sys

WORD_RE = re.compile(
    r"[А-Яа-яІіЇїЄєҐґA-Za-z0-9]+(?:['’ʼ-][А-Яа-яІіЇїЄєҐґA-Za-z0-9]+)*"
)
SENTENCE_RE = re.compile(r"(?<=[.!?…])\s+")
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")
RUSSIAN_LETTERS_RE = re.compile(r"[ёыэъЁЫЭЪ]")


def read_text(path: str, encoding: str = "auto") -> str:
    """Читає файл або stdin. Auto пробує UTF-8, потім Windows-1251."""
    if encoding not in ("auto", "utf-8", "utf-8-sig", "cp1251"):
        raise ValueError(f"Непідтримуване кодування: {encoding}")

    if path in ("-", ""):
        data = sys.stdin.buffer.read()
    else:
        data = Path(path).read_bytes()

    candidates = ["utf-8-sig", "cp1251"] if encoding == "auto" else [encoding]

    last_error: UnicodeDecodeError | None = None
    for candidate in candidates:
        try:
            return data.decode(candidate)
        except UnicodeDecodeError as error:
            last_error = error
    if last_error:
        return data.decode("utf-8", errors="replace")
    return data.decode("utf-8", errors="replace")


def _blank(match: re.Match[str]) -> str:
    """Замінює фрагмент пробілами, зберігаючи рядки."""
    return "".join("\n" if ch == "\n" else " " for ch in match.group(0))


def mask_segments(text: str) -> str:
    """Маскує код, URL, цитати й YAML frontmatter."""
    patterns = (
        r"\A---\n.*?\n---\n",
        r"```.*?```",
        r"~~~.*?~~~",
        r"`[^`\n]*`",
        r"https?://\S+",
        r"«[^»]*»",
        r"„[^“]*“",
        r"“[^”]*”",
        r'"[^"\n]*"',
    )
    masked = text
    for pattern in patterns:
        masked = re.sub(pattern, _blank, masked, flags=re.DOTALL)
    return masked


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
