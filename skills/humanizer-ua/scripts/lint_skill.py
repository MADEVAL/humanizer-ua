#!/usr/bin/env python3
"""Лінт скіла: структура, посилання, таблиці, ID, версія."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
ROOT = SKILL.parent.parent

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
    "scripts/build_release_zip.py",
    "scripts/export_rules.py",
    "scripts/self_scan.py",
    "scripts/bump_version.py",
    "scripts/rules_ua.py",
    "scripts/humanizer_ua/__init__.py",
    "scripts/humanizer_ua/cli.py",
    "scripts/humanizer_ua/facts.py",
    "scripts/humanizer_ua/markers.py",
    "scripts/humanizer_ua/metrics.py",
    "scripts/humanizer_ua/score.py",
    "scripts/humanizer_ua/text.py",
    "scripts/humanizer_ua/version.py",
]

errors: list[str] = []


def fail(message: str) -> None:
    errors.append(message)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_files() -> None:
    for name in REQUIRED:
        if not (SKILL / name).exists():
            fail(f"немає файлу: {name}")


def check_frontmatter() -> None:
    text = read(SKILL / "SKILL.md")
    if not text.startswith("---\n"):
        fail("SKILL.md має починатися з YAML frontmatter")
        return
    end = text.find("\n---", 3)
    if end == -1:
        fail("frontmatter не закритий")
        return
    block = text[3:end]
    for field in ("name: humanizer-ua", "license: MIT"):
        if field not in block:
            fail(f"frontmatter: немає {field}")
    if not re.search(r"(?m)^description:\s*\S", block):
        fail("frontmatter: порожній description")
    version = re.search(r'version:\s*"([0-9]+\.[0-9]+\.[0-9]+)"', block)
    if not version:
        fail("frontmatter: немає metadata.version")
        return
    changelog = read(ROOT / "CHANGELOG.md")
    if f"## {version.group(1)}" not in changelog:
        fail(f"CHANGELOG не має ## {version.group(1)}")


def check_length() -> None:
    words = len(re.findall(r"\S+", read(SKILL / "SKILL.md")))
    if words > 3000:
        fail(f"SKILL.md: {words} слів, максимум 3000")


def check_links() -> None:
    text = read(SKILL / "SKILL.md")
    links = set(re.findall(r"(?:\(|`)(references/[^)`]+)", text))
    for link in links:
        if not (SKILL / link).exists():
            fail(f"бите посилання: {link}")
    for path in (SKILL / "references").glob("*.md"):
        if f"references/{path.name}" not in text:
            fail(f"довідник не згаданий у SKILL.md: {path.name}")


def check_catalog() -> None:
    catalog = read(SKILL / "references" / "catalog.md")
    entries = re.findall(r"(?m)^### ([A-H])([0-9]+)\. ", catalog)
    groups: dict[str, list[int]] = {}
    for letter, number in entries:
        groups.setdefault(letter, []).append(int(number))
    for letter in "ABCDEFGH":
        numbers = groups.get(letter, [])
        if numbers != list(range(1, len(numbers) + 1)):
            fail(f"каталог, група {letter}: номери {numbers}")
    if len(entries) != 63:
        fail(f"каталог: {len(entries)} маркерів, очікується 63")
    if "63 маркери" not in catalog:
        fail("каталог: у вступі немає «63 маркери»")


def check_hard_bans() -> None:
    text = read(SKILL / "references" / "hard-bans.md")
    ids = re.findall(r"\*\*(HB[0-9]{2})\*\*", text)
    expected = [f"HB{number:02d}" for number in range(1, 31)]
    if ids != expected:
        fail(f"hard-bans: ID {ids[:5]}... не збігаються з HB01–HB30")


def check_rules() -> None:
    sys.path.insert(0, str(SKILL / "scripts"))
    from humanizer_ua.rules import HARD_BANS, MARKERS

    ids = [rule["id"] for rule in HARD_BANS + MARKERS]
    if len(ids) != len(set(ids)):
        fail("правила: дублікати ID")
    catalog = read(SKILL / "references" / "catalog.md")
    hard = read(SKILL / "references" / "hard-bans.md")
    for rule in HARD_BANS:
        if rule["id"] not in hard:
            fail(f"правило {rule['id']} не задокументоване в hard-bans.md")
    for rule in MARKERS:
        if rule["id"] not in catalog:
            fail(f"правило {rule['id']} не задокументоване в catalog.md")


def check_placeholders() -> None:
    paths = [SKILL / "SKILL.md", *(SKILL / "references").glob("*.md"), *(ROOT / "commands").glob("*.md")]
    for path in paths:
        # catalog.md навмисно цитує службові нотатки як приклад маркера.
        if path.name == "catalog.md":
            continue
        text = read(path)
        for marker in ("TODO", "FIXME", "TBD", "[вставити"):
            if marker in text:
                fail(f"{path.name}: залишок «{marker}»")


def check_tables() -> None:
    for path in [SKILL / "SKILL.md", *(SKILL / "references").glob("*.md")]:
        lines = read(path).splitlines()
        block: list[tuple[int, str]] = []

        def flush() -> None:
            if len(block) < 2:
                block.clear()
                return
            expected = block[0][1].count("|")
            for number, line in block[1:]:
                if re.fullmatch(r"\s*\|?[\s:|-]+\|?\s*", line):
                    continue
                if line.count("|") != expected:
                    fail(f"{path.name}:{number}: у таблиці {line.count('|')} труб, очікується {expected}")
            block.clear()

        for number, line in enumerate(lines, start=1):
            if line.strip().startswith("|"):
                block.append((number, line))
            else:
                flush()
        flush()


def check_manifests() -> None:
    plugin = json.loads(read(ROOT / ".claude-plugin" / "plugin.json"))
    cursor = json.loads(read(ROOT / ".cursor-plugin" / "plugin.json"))
    marketplace = json.loads(read(ROOT / ".claude-plugin" / "marketplace.json"))
    for name, data in (("plugin", plugin), ("cursor", cursor)):
        if not data.get("description"):
            fail(f"{name}: порожній description")
    if plugin.get("skills") != ["./skills/humanizer-ua"]:
        fail(f"plugin.skills = {plugin.get('skills')!r}")
    if not marketplace.get("plugins"):
        fail("marketplace: немає plugins")

    openai = read(SKILL / "agents" / "openai.yaml")
    if "interface:" not in openai or "display_name:" not in openai:
        fail("agents/openai.yaml: немає interface.display_name")


def check_commands() -> None:
    for name in ("humanize.md", "audit.md"):
        path = ROOT / "commands" / name
        if not path.exists():
            fail(f"немає команди: commands/{name}")
            continue
        text = read(path)
        if not text.startswith("---\n") or "description:" not in text or "argument-hint:" not in text:
            fail(f"commands/{name}: неповний frontmatter")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    check_files()
    check_frontmatter()
    check_length()
    check_links()
    check_catalog()
    check_hard_bans()
    check_rules()
    check_placeholders()
    check_tables()
    check_manifests()
    check_commands()

    if errors:
        print(f"RESULT: FAIL ({len(errors)})")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("RESULT: PASS lint-skill")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
