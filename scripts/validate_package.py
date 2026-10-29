#!/usr/bin/env python3
"""Перевірка пакета Humanizer-UA.

Запуск:
    python scripts/validate_package.py
    python scripts/validate_package.py --full
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "humanizer-ua"

REQUIRED = [
    "SKILL.md",
    "edit-log.md",
    "agents/openai.yaml",
    "references/catalog.md",
    "references/hard-bans.md",
    "references/surzhyk.md",
    "references/wordlist.md",
    "references/typography.md",
    "references/registers.md",
    "references/voice.md",
    "references/review.md",
    "references/audit.md",
    "references/scan.md",
    "scripts/scan.py",
    "scripts/scan_gate.py",
    "scripts/lint_skill.py",
    "scripts/check_examples.py",
    "scripts/install_smoke.py",
    "scripts/build_release_zip.py",
    "scripts/export_rules.py",
    "scripts/self_scan.py",
    "scripts/bump_version.py",
    "scripts/rules_ua.py",
    "scripts/test_scan.py",
    "scripts/test_rules.py",
    "scripts/humanizer_ua/__init__.py",
    "scripts/humanizer_ua/cli.py",
    "scripts/humanizer_ua/facts.py",
    "scripts/humanizer_ua/markers.py",
    "scripts/humanizer_ua/metrics.py",
    "scripts/humanizer_ua/rules.py",
    "scripts/humanizer_ua/scoring.py",
    "scripts/humanizer_ua/context.py",
    "scripts/humanizer_ua/norm.py",
    "scripts/humanizer_ua/score.py",
    "scripts/humanizer_ua/text.py",
    "scripts/humanizer_ua/version.py",
]

errors: list[str] = []
checks: list[str] = []


def ok(name: str) -> None:
    checks.append(name)
    print(f"PASS {name}")


def fail(name: str, message: str) -> None:
    errors.append(f"{name}: {message}")
    print(f"FAIL {name}: {message}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end]
    data: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line or line.startswith(" "):
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def check_files() -> None:
    missing = [name for name in REQUIRED if not (SKILL / name).exists()]
    root_missing = [
        name
        for name in (
            "commands/humanize.md",
            "commands/audit.md",
            "eval/run_eval.py",
            "eval/run_triggers.py",
            "eval/triggers.json",
        )
        if not (ROOT / name).exists()
    ]
    if missing or root_missing:
        fail("files", "немає: " + ", ".join(missing + root_missing))
    else:
        ok("files")


def check_frontmatter() -> None:
    text = read(SKILL / "SKILL.md")
    meta = frontmatter(text)
    if meta.get("name") != "humanizer-ua":
        fail("frontmatter", "name має бути humanizer-ua")
    elif not meta.get("description"):
        fail("frontmatter", "description порожній")
    elif meta.get("license") != "MIT":
        fail("frontmatter", "license має бути MIT")
    else:
        ok("frontmatter")

    match = re.search(r"version:\s*\"([^\"]+)\"", text)
    if not match:
        fail("version", "немає metadata.version")
        return
    version = match.group(1)
    changelog = read(ROOT / "CHANGELOG.md")
    if f"## {version}" not in changelog:
        fail("version", f"CHANGELOG не має ## {version}")
        return
    for manifest in (".claude-plugin/plugin.json", ".cursor-plugin/plugin.json"):
        data = json.loads(read(ROOT / manifest))
        if data.get("version") != version:
            fail("version", f"{manifest}: {data.get('version')} != {version}")
            return
    marketplace = json.loads(read(ROOT / ".claude-plugin" / "marketplace.json"))
    for plugin in marketplace.get("plugins", []):
        if plugin.get("version") != version:
            fail("version", f"marketplace: {plugin.get('version')} != {version}")
            return
    ok("version")


def check_skill_length() -> None:
    text = read(SKILL / "SKILL.md")
    words = len(re.findall(r"\S+", text))
    if words > 3000:
        fail("skill-length", f"{words} слів, максимум 3000")
    else:
        ok(f"skill-length ({words} слів)")


def check_links() -> None:
    text = read(SKILL / "SKILL.md")
    links = set(re.findall(r"(?:\(|`)(references/[^)`]+)", text))
    missing = [link for link in links if not (SKILL / link).exists()]
    if missing:
        fail("links", "биті: " + ", ".join(sorted(missing)))
    else:
        ok(f"links ({len(links)})")


def check_rules() -> None:
    sys.path.insert(0, str(SKILL / "scripts"))
    from rules_ua import HARD_BANS, MARKERS

    catalog = read(SKILL / "references" / "catalog.md")
    hard_bans = read(SKILL / "references" / "hard-bans.md")

    missing = [rule["id"] for rule in HARD_BANS if rule["id"] not in hard_bans]
    if missing:
        fail("rules-hard", "немає в hard-bans.md: " + ", ".join(missing))
    else:
        ok(f"rules-hard ({len(HARD_BANS)})")

    missing = [rule["id"] for rule in MARKERS if rule["id"] not in catalog]
    if missing:
        fail("rules-markers", "немає в catalog.md: " + ", ".join(missing))
    else:
        ok(f"rules-markers ({len(MARKERS)})")

    patched = [rule for rule in HARD_BANS + MARKERS if rule.get("pattern") or rule.get("patterns")]
    if len(patched) != len(HARD_BANS) + len(MARKERS):
        fail("rules-patterns", "є правило без pattern")
    else:
        ok("rules-patterns")


def check_dist() -> None:
    """dist/rules-ua.json має бути згенерований із поточних правил."""
    path = ROOT / "dist" / "rules-ua.json"
    if not path.exists():
        fail("dist", "немає dist/rules-ua.json")
        return

    sys.path.insert(0, str(SKILL / "scripts"))
    from humanizer_ua.norm import NORM_RULES
    from humanizer_ua.rules import GENRES, HARD_BANS, MARKERS, WEAK_IDS
    from humanizer_ua.version import VERSION

    expected = json.loads(
        json.dumps(
            {
                "version": VERSION,
                "genres": list(GENRES),
                "weak_ids": sorted(WEAK_IDS),
                "hard_bans": HARD_BANS,
                "norm": NORM_RULES,
                "markers": MARKERS,
            },
            ensure_ascii=False,
        )
    )
    actual = json.loads(read(path))
    if actual != expected:
        fail("dist", "dist/rules-ua.json застарів; запусти scripts/export_rules.py")
    else:
        ok("dist")


def check_catalog() -> None:
    catalog = read(SKILL / "references" / "catalog.md")
    entries = re.findall(r"(?m)^### ([A-H])([0-9]+)\. ", catalog)
    groups: dict[str, list[int]] = {}
    for letter, number in entries:
        groups.setdefault(letter, []).append(int(number))

    for letter in "ABCDEFGH":
        numbers = groups.get(letter, [])
        if numbers != list(range(1, len(numbers) + 1)):
            fail("catalog", f"група {letter}: номери {numbers}")
            return

    if len(entries) != 80:
        fail("catalog", f"{len(entries)} маркерів, очікується 80")
        return

    if "80 маркерів" not in catalog:
        fail("catalog", "у вступі немає «80 маркерів»")
        return

    ok(f"catalog ({len(entries)} маркерів)")


def check_package_layout() -> None:
    skill_files = [path for path in (ROOT / "skills").rglob("SKILL.md")]
    if len(skill_files) != 1 or skill_files[0].resolve() != (SKILL / "SKILL.md").resolve():
        fail("layout", "має бути рівно один skills/humanizer-ua/SKILL.md")
        return

    plugin = json.loads(read(ROOT / ".claude-plugin" / "plugin.json"))
    if plugin.get("skills") != ["./skills/humanizer-ua"]:
        fail("layout", f"plugin.skills = {plugin.get('skills')!r}")
        return

    meta = frontmatter(read(SKILL / "SKILL.md"))
    canonical = meta.get("description", "").split(". ")[0].strip()
    if not canonical.endswith("."):
        canonical += "."
    descriptions = {
        plugin.get("description", ""),
        json.loads(read(ROOT / ".cursor-plugin" / "plugin.json")).get("description", ""),
        *(
            item.get("description", "")
            for item in json.loads(read(ROOT / ".claude-plugin" / "marketplace.json")).get("plugins", [])
        ),
    }
    if len(descriptions) != 1 or not next(iter(descriptions)).startswith(canonical):
        fail("layout", "описи в маніфестах мають починатися з першого речення опису SKILL.md")
        return

    openai = read(SKILL / "agents" / "openai.yaml")
    if "interface:" not in openai or "display_name:" not in openai:
        fail("layout", "agents/openai.yaml має містити interface.display_name")
        return

    ok("layout")


def check_scanner() -> None:
    result = subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "scan.py"), "--version"],
        capture_output=True,
        text=True,
        timeout=20,
        encoding="utf-8",
    )
    if result.returncode != 0:
        fail("scanner", result.stderr.strip() or "не запускається")
        return
    declared = re.search(r'version:\s*"([^"]+)"', read(SKILL / "SKILL.md"))
    expected = f"humanizer-ua {declared.group(1)}" if declared else ""
    if expected and result.stdout.strip() != expected:
        fail("scanner", f"{result.stdout.strip()} != {expected}")
    else:
        ok(f"scanner ({result.stdout.strip()})")


def run_full() -> None:
    commands = [
        [sys.executable, "-m", "unittest", str(SKILL / "scripts" / "test_scan.py"), "-v"],
        [sys.executable, "-m", "unittest", str(SKILL / "scripts" / "test_rules.py"), "-v"],
        [sys.executable, str(SKILL / "scripts" / "lint_skill.py")],
        [sys.executable, str(SKILL / "scripts" / "check_examples.py")],
        [sys.executable, str(SKILL / "scripts" / "install_smoke.py")],
        [sys.executable, str(SKILL / "scripts" / "self_scan.py")],
        [sys.executable, str(SKILL / "scripts" / "scan_gate.py"), str(ROOT / "eval" / "corpus" / "human"), "--min-score", "90", "--quiet"],
        [sys.executable, str(ROOT / "eval" / "run_eval.py")],
        [sys.executable, str(ROOT / "eval" / "run_triggers.py")],
    ]
    for command in commands:
        print(f"\n$ {' '.join(command)}")
        result = subprocess.run(command, cwd=ROOT, timeout=120)
        if result.returncode != 0:
            errors.append("full: " + " ".join(command))


def main() -> int:
    parser = argparse.ArgumentParser(description="Перевірка пакета Humanizer-UA")
    parser.add_argument("--full", action="store_true", help="запустити тести й eval")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

    check_files()
    check_frontmatter()
    check_skill_length()
    check_links()
    check_rules()
    check_dist()
    check_catalog()
    check_package_layout()
    check_scanner()

    if args.full:
        run_full()

    print()
    if errors:
        print(f"RESULT: FAIL ({len(errors)})")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"RESULT: PASS ({len(checks)} перевірок)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
