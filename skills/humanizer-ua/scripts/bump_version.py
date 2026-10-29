#!/usr/bin/env python3
"""Оновлює версію в усіх файлах пакета й додає запис у CHANGELOG."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
ROOT = SKILL.parent.parent


def replace_version(text: str, version: str) -> str:
    updated, count = re.subn(r'(?m)^(\s*version:\s*)"[^"]+"', rf'\1"{version}"', text)
    if count == 0:
        raise ValueError("не знайдено version у SKILL.md")
    return updated


def update_json(path: Path, version: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "plugins" in data:
        for plugin in data["plugins"]:
            plugin["version"] = version
    else:
        data["version"] = version
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Підняти версію Humanizer-UA")
    parser.add_argument("version", help="нова версія, наприклад 1.3.0")
    parser.add_argument("--date", default=dt.date.today().isoformat())
    parser.add_argument("--note", default="Оновлення.", help="рядок для CHANGELOG")
    args = parser.parse_args(argv)

    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", args.version):
        print("Версія має бути у форматі X.Y.Z", file=sys.stderr)
        return 2

    try:
        skill_path = SKILL / "SKILL.md"
        skill_path.write_text(replace_version(skill_path.read_text(encoding="utf-8"), args.version), encoding="utf-8")

        version_path = SKILL / "scripts" / "humanizer_ua" / "version.py"
        version_path.write_text(
            re.sub(r'(?m)^VERSION = "[^"]+"', f'VERSION = "{args.version}"', version_path.read_text(encoding="utf-8")),
            encoding="utf-8",
        )

        for manifest in (ROOT / ".claude-plugin" / "plugin.json", ROOT / ".cursor-plugin" / "plugin.json", ROOT / ".claude-plugin" / "marketplace.json"):
            update_json(manifest, args.version)

        changelog = ROOT / "CHANGELOG.md"
        text = changelog.read_text(encoding="utf-8")
        if f"## {args.version}" not in text:
            entry = f"## {args.version} — {args.date}\n\n- {args.note}\n\n"
            text = text.replace("# Changelog\n\n", "# Changelog\n\n" + entry, 1)
            changelog.write_text(text, encoding="utf-8")

        exported = subprocess.run(
            [sys.executable, str(SKILL / "scripts" / "export_rules.py")],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if exported.returncode != 0:
            raise ValueError(exported.stderr.strip() or "не вдалося оновити dist/rules-ua.json")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Помилка: {error}", file=sys.stderr)
        return 2

    print(f"RESULT: PASS bump-version ({args.version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
