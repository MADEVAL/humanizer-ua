"""Метрики ритму, структури й оформлення."""

from __future__ import annotations

from collections import Counter
import re
import statistics

from .rules import DECOR_EXEMPT, HEDGES
from .text import EMOJI_RE, WORD_RE, count_words, sentences


def _metric(ident: str, label: str, value: float, limit: float, penalty: int, detail: str) -> dict:
    return {
        "id": ident,
        "label": label,
        "value": round(value, 2),
        "limit": round(limit, 2),
        "penalty": penalty,
        "detail": detail,
    }


def count_hedges(text: str) -> int:
    total = 0
    for hedge in HEDGES:
        total += len(re.findall(rf"\b{re.escape(hedge)}\b", text, flags=re.IGNORECASE))
    return total


def _cv(values: list[int]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    if not mean:
        return 0.0
    return statistics.pstdev(values) / mean


def _staccato_runs(text: str) -> tuple[int, int]:
    lengths = [count_words(sentence) for sentence in sentences(text)]
    runs = 0
    longest = 0
    current = 0
    for length in lengths:
        if length <= 3:
            current += 1
            longest = max(longest, current)
        else:
            if current >= 3:
                runs += 1
            current = 0
    if current >= 3:
        runs += 1
    return runs, longest


def _repeated_phrases(text: str, size: int = 4, limit: int = 3) -> list[str]:
    words = [word.lower() for word in WORD_RE.findall(text)]
    if len(words) < size * 2:
        return []
    counter: Counter = Counter(tuple(words[i : i + size]) for i in range(len(words) - size + 1))
    repeated = [phrase for phrase, count in counter.most_common(limit * 3) if count >= 2]
    return [" ".join(phrase) for phrase in repeated[:limit]]


def collect_metrics(raw: str, masked: str, words: int, genre: str) -> list[dict]:
    metrics: list[dict] = []
    safe_words = max(words, 1)
    lengths = [count_words(sentence) for sentence in sentences(masked)]

    # Тире
    dash_count = len(re.findall(r"(?<=\s)[—–](?=\s)", masked))
    dash_limit = max(1.0, words / 120)
    if dash_count > dash_limit:
        metrics.append(
            _metric("dash", "Багато тире", dash_count, dash_limit, min(12, int(round((dash_count - dash_limit) * 3))), f"{dash_count} на {words} слів")
        )

    # Болд
    bold_count = len(re.findall(r"\*\*[^*\n]{1,120}\*\*", raw))
    bold_limit = max(2.0, words / 500)
    if bold_count > bold_limit and genre not in DECOR_EXEMPT:
        metrics.append(_metric("bold", "Болд-декор", bold_count, bold_limit, 4, f"{bold_count} виділень"))

    # Емодзі
    emoji_count = len(EMOJI_RE.findall(raw))
    if emoji_count and genre not in DECOR_EXEMPT:
        metrics.append(_metric("emoji", "Емодзі-декор", emoji_count, 0, min(8, emoji_count * 2), f"{emoji_count} емодзі"))

    # Заголовки Title Case
    title_case = 0
    for line in raw.splitlines():
        heading = re.match(r"^#{1,6}\s+(.+)$", line)
        if not heading:
            continue
        title = heading.group(1).strip()
        heading_words = [w for w in WORD_RE.findall(title) if len(w) > 1]
        if len(heading_words) < 3:
            continue
        capitalized = sum(1 for w in heading_words if w[0].isupper())
        if capitalized / len(heading_words) >= 0.6 and not title.isupper():
            title_case += 1
    if title_case and genre not in DECOR_EXEMPT:
        metrics.append(_metric("title_case", "Title Case у заголовках", title_case, 0, 4, f"{title_case} заголовків"))

    # Список із болд-лейблами
    bold_labels = len(re.findall(r"^\s*[-*]\s+\*\*[^*\n]+:\*\*", raw, flags=re.MULTILINE))
    if bold_labels >= 2 and genre not in DECOR_EXEMPT:
        metrics.append(_metric("bold_labels", "Список із болд-лейблами", bold_labels, 1, 4, f"{bold_labels} пунктів"))

    # Однотипні початки
    starts = []
    for sentence in sentences(masked):
        match = WORD_RE.search(sentence)
        if match:
            starts.append(match.group(0).lower())
    run = 1
    max_run = 1
    for previous, current in zip(starts, starts[1:]):
        if previous == current:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 1
    if max_run >= 3:
        metrics.append(_metric("repeated_openings", "Однотипні початки", max_run, 2, 4, f"{max_run} речень підряд"))

    # Ритм: коефіцієнт варіації довжини речень
    if len(lengths) >= 8:
        cv = _cv(lengths)
        if cv < 0.30:
            metrics.append(
                _metric("cv_length", "Рівномірна довжина речень", cv, 0.30, min(18, int(round((0.30 - cv) / 0.30 * 30))), f"CV {cv:.2f}")
            )

    # Ритм абзаців
    paragraphs = [p for p in re.split(r"\n\s*\n", masked) if count_words(p) >= 5]
    if len(paragraphs) >= 4:
        para_cv = _cv([count_words(p) for p in paragraphs])
        if para_cv < 0.30:
            metrics.append(
                _metric("paragraph_cv", "Рівні абзаци", para_cv, 0.30, 6, f"CV {para_cv:.2f}")
            )

    # Рвана медитативність: ланцюг обірваних речень
    runs, longest = _staccato_runs(masked)
    if runs:
        metrics.append(
            _metric("staccato", "Ланцюг обірваних речень", runs, 0, min(12, runs * 4), f"найдовший {longest}")
        )

    # Номіналізації
    nominalizations = len(re.findall(r"\b[А-Яа-яІіЇїЄєҐґ]+(?:ння|ття|ість|ція|ання|ення|ування)\b", masked, flags=re.IGNORECASE))
    per_100 = nominalizations / safe_words * 100
    if per_100 > 8:
        metrics.append(_metric("nominalization", "Нагромадження віддієслівних іменників", per_100, 8, 6, f"{per_100:.1f} на 100 слів"))

    # Пасив
    passive = len(re.findall(r"\b[А-Яа-яІіЇїЄєҐґ]+(?:ється|ються|вся|лася|лися|лося)\b", masked, flags=re.IGNORECASE))
    passive_per_100 = passive / safe_words * 100
    if passive_per_100 > 10 and genre not in {"academic", "legal", "news"}:
        metrics.append(_metric("passive", "Пасив", passive_per_100, 10, 3, f"{passive_per_100:.1f} на 100 слів"))

    # «Який»
    yakyi = len(re.findall(r"\bяк(?:ий|а|е|і|ого|ому|им|их)\b", masked, flags=re.IGNORECASE))
    yakyi_per_100 = yakyi / safe_words * 100
    if yakyi_per_100 > 4:
        metrics.append(_metric("yakyi", "Ланцюги «який»", yakyi_per_100, 4, 4, f"{yakyi_per_100:.1f} на 100 слів"))

    # ASCII-апостроф
    ascii_apostrophe = len(re.findall(r"[А-Яа-яІіЇїЄєҐґ]'[А-Яа-яІіЇїЄєҐґ]", raw))
    if ascii_apostrophe:
        metrics.append(_metric("ascii_apostrophe", "ASCII-апостроф", ascii_apostrophe, 0, 3, "заміни на ’"))

    # Прямі й англійські лапки
    bad_quotes = len(re.findall(r'"[^"\n]{1,120}"', raw)) + len(re.findall(r"“[^”]{1,120}”", raw))
    if bad_quotes:
        metrics.append(_metric("quotes", "Неукраїнські лапки", bad_quotes, 0, 3, "використовуй «»"))

    # Формат чисел
    bad_numbers = (
        len(re.findall(r"\d%", raw))
        + len(re.findall(r"\d(?:грн|кг|км|см|мм|гб|мб|тб)\b", raw, flags=re.IGNORECASE))
        + len(re.findall(r"\d{4}р\.", raw))
    )
    if bad_numbers:
        metrics.append(_metric("numbers", "Формат чисел", bad_numbers, 0, 3, "пробіл перед одиницею"))

    # Російські літери
    russian = len(re.findall(r"[ёыэъЁЫЭЪ]", raw))
    if russian:
        metrics.append(_metric("russian_letters", "Російські літери", russian, 0, 12, "виправ як орфографію"))

    # Подвійні пробіли й пробіл перед пунктуацією
    double_spaces = 0
    for line in masked.splitlines():
        if line[:1].isspace() or line.lstrip().startswith("|"):
            continue
        double_spaces += len(re.findall(r"\S  +\S", line))
    if double_spaces:
        metrics.append(_metric("double_spaces", "Подвійні пробіли", double_spaces, 0, 2, "один пробіл"))

    space_before_punct = len(re.findall(r"\s+[,.;:!?](?=\s|$)", masked))
    if space_before_punct:
        metrics.append(_metric("space_before_punct", "Пробіл перед розділовим знаком", space_before_punct, 0, 2, ""))

    # Горизонтальні лінії
    hrs = sum(1 for line in raw.splitlines() if line.strip() == "---")
    if hrs > 2 and genre not in DECOR_EXEMPT:
        metrics.append(_metric("hr", "Зайві розділювачі", hrs, 2, 3, f"{hrs} ліній"))

    # Англійські слова
    english = len(re.findall(r"\b[A-Za-z]{4,}\b", masked))
    if words >= 50 and english / safe_words > 0.03:
        metrics.append(_metric("english", "Багато англійських слів", english / safe_words * 100, 3, 3, ""))

    # Хеджування
    hedge_count = count_hedges(masked)
    if hedge_count >= 5:
        metrics.append(_metric("hedges", "Нагромадження оговорок", hedge_count, 4, 4, f"{hedge_count} оговорок"))

    # Листикл
    lines = raw.splitlines()
    list_items = len([line for line in lines if re.match(r"^\s*(?:[-*+•]|\d{1,3}[.)])\s+\S", line)])
    non_empty = len([line for line in lines if line.strip()])
    if list_items >= 5 and non_empty and list_items / non_empty > 0.6:
        metrics.append(_metric("listicle", "Список замість прози", list_items, 4, 4, f"{list_items} пунктів"))

    # Повтор фраз між абзацами: спостереження без штрафу
    phrases = _repeated_phrases(masked)
    if phrases:
        metrics.append(_metric("repeats", "Повтор фраз", len(phrases), 0, 0, "; ".join(f"«{p}»" for p in phrases)))

    return metrics
