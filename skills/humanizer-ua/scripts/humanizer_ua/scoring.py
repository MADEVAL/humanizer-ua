"""Шкали: норма, стиль, структура.

Бал не сума штрафів за слова. Рахуємо події: одне правило в одному абзаці —
одна подія. Далі подія переводиться в плотність на 1000 слів і насичується:
перше входження коштує помітно, десяте — майже нічого. Тому одне правило
не може обнулити текст, а десяток різних — може.
"""

from __future__ import annotations

SEVERITY_UNITS = {"error": 18.0, "warning": 10.0, "info": 5.0}

# Плотність (подій на 1000 слів), за якої правило коштує половину своєї
# ваги. Для error поріг нижчий: нормативна помилка важить уже з першого разу.
HALF_DENSITY = {"error": 1.0, "warning": 2.5, "info": 4.0}

# Ваги шкал за жанром. Норма важить більше там, де ціна помилки вища.
PROFILES = {
    "marketing": {"weights": (0.30, 0.50, 0.20), "clean": 85, "edit": 60},
    "expert": {"weights": (0.35, 0.45, 0.20), "clean": 85, "edit": 60},
    "business": {"weights": (0.40, 0.40, 0.20), "clean": 88, "edit": 65},
    "news": {"weights": (0.45, 0.35, 0.20), "clean": 88, "edit": 65},
    "academic": {"weights": (0.50, 0.30, 0.20), "clean": 90, "edit": 70},
    "legal": {"weights": (0.60, 0.20, 0.20), "clean": 95, "edit": 80},
    "docs": {"weights": (0.45, 0.35, 0.20), "clean": 88, "edit": 65},
    "fiction": {"weights": (0.30, 0.50, 0.20), "clean": 80, "edit": 50},
}

LAYERS = ("norm", "style", "structure")


def event_penalty(events: int, words: int, severity: str, confidence: float, max_events: int | None = None) -> float:
    """Штраф за правило з урахуванням плотності й уверенності."""
    if events <= 0:
        return 0.0
    if max_events is not None:
        events = min(events, max_events)
    density = events / max(words, 1) * 1000
    unit = SEVERITY_UNITS.get(severity, 10.0)
    half = HALF_DENSITY.get(severity, 2.5)
    saturation = 1 - 2 ** (-density / half)
    return round(unit * saturation * confidence, 2)


def sub_scores(items: list[dict]) -> dict[str, float]:
    """Три шкали 0–100. Кожна насичується окремо."""
    losses = {layer: 0.0 for layer in LAYERS}
    for item in items:
        if item.get("weak_alone"):
            continue
        layers = item.get("layers") or (item.get("layer", "style"),)
        share = item.get("penalty", 0.0) / len(layers)
        for layer in layers:
            losses[layer] = losses.get(layer, 0.0) + share
    return {layer: round(100 - min(100.0, losses[layer]), 1) for layer in LAYERS}


def composite(scores: dict[str, float], genre: str) -> int:
    """Зважена «чистота» за профілем жанру.

    Це зважене геометричне середнє, а не сума: провалена шкала тягне
    підсумок униз, навіть якщо дві інші ідеальні. Текст без жодної
    нормативної помилки, але з мертвим стилем, не стає «чистим» лише
    тому, що норма важить третину.

    Підлога 5 не дає одній шкалі обнулити оцінку повністю.
    """
    profile = PROFILES.get(genre, PROFILES["marketing"])
    weights = dict(zip(LAYERS, profile["weights"]))
    value = 1.0
    for layer, weight in weights.items():
        share = max(5.0, scores.get(layer, 100.0)) / 100.0
        value *= share ** weight
    return max(0, min(100, int(round(value * 100))))


def band(score: int, scores: dict[str, float], genre: str, errors: bool = False) -> str:
    """Полоса з жанровим порогом.

    Нормативна шкала має вето: текст із помилками не може вважатися чистим,
    навіть якщо стиль і структура ідеальні. Помилка з `error` теж блокує
    «чисто»: її треба виправити, а не зважити.
    """
    profile = PROFILES.get(genre, PROFILES["marketing"])
    if score >= profile["clean"]:
        label = "чисто"
    elif score >= profile["edit"]:
        label = "правка"
    else:
        label = "рерайт"

    norm = scores.get("norm", 100.0)
    if norm < 70:
        return "рерайт"
    if errors and label == "чисто":
        return "правка"
    if norm < 90 and label == "чисто":
        return "правка"
    return label


def fact_risk(penalty: int) -> int:
    """Факт-замок у шкалі 0–100."""
    return max(0, min(100, round(penalty / 40 * 100)))


def profile(genre: str) -> dict:
    return PROFILES.get(genre, PROFILES["marketing"])
