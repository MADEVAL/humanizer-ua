"""Метрики ритму, структури й оформлення.

Метрика — це спостереження, а не привід. Вона не знає контексту, тому
працює лише там, де контекст не потрібен: ритм, розмітка, повтор.
Типографіку перевіряють правила шару N, а не метрики.
"""

from __future__ import annotations

from collections import Counter
import re
import statistics

from .rules import DECOR_EXEMPT, HEDGES
from .text import EMOJI_RE, WORD_RE, count_words, sentences

# Англійські слова, які не є «засміченням»: назви продуктів, технологій
# і усталені терміни. Лічити їх як чужу лексику — хибне спрацювання.
ENGLISH_ALLOWED = {
    "wordpress", "woocommerce", "cloudflare", "nginx", "apache", "docker",
    "kubernetes", "linux", "windows", "macos", "android", "ios", "github",
    "gitlab", "redis", "memcached", "mysql", "postgresql", "postgres",
    "laravel", "magento", "bootstrap", "javascript", "typescript", "python",
    "php", "html", "css", "json", "yaml", "xml", "sql", "api", "cli", "sdk",
    "http", "https", "dns", "asn", "url", "uri", "ssh", "ftp", "tcp", "udp",
    "ssl", "tls", "cdn", "vpn", "cpu", "ram", "ssd", "hdd", "gpu", "ui",
    "ux", "seo", "sem", "cms", "crm", "erp", "smtp", "imap", "jwt", "oauth",
    "jsonl", "csv", "sarif", "markdown", "frontend", "backend", "devops",
}


def _metric(ident: str, label: str, value: float, limit: float, penalty: int, detail: str, layer: str = "style") -> dict:
    return {
        "id": ident,
        "label": label,
        "value": round(value, 2),
        "limit": round(limit, 2),
        "penalty": penalty,
        "detail": detail,
        "layer": layer,
        "kind": "metric",
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


def _title_case_headings(raw: str) -> int:
    """Заголовки Title Case, де капіталізовані саме звичайні слова.

    Заголовок із назв продуктів («PHP, Laravel, WordPress») не рахуємо:
    там великі літери ставить бренд, а не шаблон.
    """
    flagged = 0
    for line in raw.splitlines():
        heading = re.match(r"^#{1,6}\s+(.+)$", line)
        if not heading:
            continue
        title = heading.group(1).strip()
        if title.isupper():
            continue
        words = [
            word
            for word in WORD_RE.findall(title)
            if len(word) > 1 and not word.isascii() and not any(char.isdigit() for char in word)
        ]
        if len(words) < 3:
            continue
        capitalized = sum(1 for word in words if word[0].isupper())
        if capitalized / len(words) >= 0.6:
            flagged += 1
    return flagged


def _english_words(masked: str, words: int, genre: str) -> float:
    """Частка англійських слів, які не є назвами продуктів чи термінами."""
    limit = 8.0 if genre in ("docs", "expert") else 3.0
    tokens = re.findall(r"\b[A-Za-z][A-Za-z-]{3,}\b", masked)
    # Велика літера на початку — це зазвичай бренд або власна назва
    # (ChatGPT, Google, Claude), а не «засмічення» англійською.
    foreign = [
        token
        for token in tokens
        if token[0].islower() and token.lower() not in ENGLISH_ALLOWED
    ]
    if not tokens or words < 50:
        return 0.0
    share = len(foreign) / max(words, 1) * 100
    return share if share > limit else 0.0


def collect_metrics(raw: str, masked: str, words: int, genre: str) -> list[dict]:
    metrics: list[dict] = []
    safe_words = max(words, 1)
    lengths = [count_words(sentence) for sentence in sentences(masked)]

    # Тире як стилістичний прийом. Самотнє тире — норма, дефіс замість
    # тире ловить N01, а не ця метрика. У художньому тексті тире — це
    # пунктуація діалогу, тому метрику не застосовуємо.
    if genre != "fiction":
        dash_count = len(re.findall(r"(?<=\s)[—–](?=\s)", masked))
        dash_limit = max(2.0, words / 120)
        if dash_count > dash_limit:
            metrics.append(
                _metric("dash", "Багато тире", dash_count, dash_limit, min(10, int(round((dash_count - dash_limit) * 3))), f"{dash_count} на {words} слів")
            )

    # Болд
    bold_count = len(re.findall(r"\*\*[^*\n]{1,120}\*\*", raw))
    bold_limit = max(2.0, words / 500)
    if bold_count > bold_limit and genre not in DECOR_EXEMPT:
        metrics.append(_metric("bold", "Болд-декор", bold_count, bold_limit, 4, f"{bold_count} виділень", "structure"))

    # Емодзі
    emoji_count = len(EMOJI_RE.findall(raw))
    if emoji_count and genre not in DECOR_EXEMPT:
        metrics.append(_metric("emoji", "Емодзі-декор", emoji_count, 0, min(8, emoji_count * 2), f"{emoji_count} емодзі", "structure"))

    # Заголовки Title Case
    title_case = _title_case_headings(raw)
    if title_case and genre not in DECOR_EXEMPT:
        metrics.append(_metric("title_case", "Title Case у заголовках", title_case, 0, 4, f"{title_case} заголовків", "structure"))

    # Список із болд-лейблами
    bold_labels = len(re.findall(r"^\s*[-*]\s+\*\*[^*\n]+:\*\*", raw, flags=re.MULTILINE))
    if bold_labels >= 2 and genre not in DECOR_EXEMPT:
        metrics.append(_metric("bold_labels", "Список із болд-лейблами", bold_labels, 1, 4, f"{bold_labels} пунктів", "structure"))

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
    if max_run >= 3 and genre != "fiction":
        metrics.append(_metric("repeated_openings", "Однотипні початки", max_run, 2, 4, f"{max_run} речень підряд", "structure"))

    # Ритм: коефіцієнт варіації довжини речень
    if len(lengths) >= 8 and genre != "fiction":
        cv = _cv(lengths)
        if cv < 0.30:
            metrics.append(
                _metric("cv_length", "Рівномірна довжина речень", cv, 0.30, min(18, int(round((0.30 - cv) / 0.30 * 30))), f"CV {cv:.2f}")
            )

    # Ритм абзаців
    paragraphs = [p for p in re.split(r"\n\s*\n", masked) if count_words(p) >= 5]
    if len(paragraphs) >= 4 and genre != "fiction":
        para_cv = _cv([count_words(p) for p in paragraphs])
        if para_cv < 0.30:
            metrics.append(
                _metric("paragraph_cv", "Рівні абзаци", para_cv, 0.30, 6, f"CV {para_cv:.2f}", "structure")
            )

    # Рвана медитативність: ланцюг обірваних речень
    runs, longest = _staccato_runs(masked)
    if runs and genre != "fiction":
        metrics.append(
            _metric("staccato", "Ланцюг обірваних речень", runs, 0, min(12, runs * 4), f"найдовший {longest}")
        )

    # Плотнісні метрики на короткому тексті — шум: три іменники на
    # п'ятнадцять слів дають «20 на 100 слів». Документ обіцяє не
    # застосовувати метрики до текстів коротших за 50 слів.
    if words >= 50:
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

    # Горизонтальні лінії
    hrs = sum(1 for line in raw.splitlines() if line.strip() == "---")
    if hrs > 2 and genre not in DECOR_EXEMPT:
        metrics.append(_metric("hr", "Зайві розділювачі", hrs, 2, 3, f"{hrs} ліній", "structure"))

    # Англійські слова: назви продуктів і терміни не рахуються
    english_share = _english_words(masked, words, genre)
    if english_share:
        metrics.append(_metric("english", "Багато англійських слів", english_share, 3.0, 3, ""))

    # Хеджування: лише нагромадження оговорок, не умови й модальність
    if words >= 50:
        hedge_count = count_hedges(masked)
        hedge_density = hedge_count / safe_words * 1000
        if hedge_count >= 3 and hedge_density > 4:
            metrics.append(_metric("hedges", "Нагромадження оговорок", round(hedge_density, 1), 4, 4, f"{hedge_count} оговорок"))

    # Листикл
    lines = raw.splitlines()
    list_items = len([line for line in lines if re.match(r"^\s*(?:[-*+•]|\d{1,3}[.)])\s+\S", line)])
    non_empty = len([line for line in lines if line.strip()])
    if list_items >= 5 and non_empty and list_items / non_empty > 0.6:
        metrics.append(_metric("listicle", "Список замість прози", list_items, 4, 4, f"{list_items} пунктів", "structure"))

    # Повтор фраз між абзацами: спостереження без штрафу
    phrases = _repeated_phrases(masked)
    if phrases:
        metrics.append(_metric("repeats", "Повтор фраз", len(phrases), 0, 0, "; ".join(f"«{p}»" for p in phrases)))

    return metrics
