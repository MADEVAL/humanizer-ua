#!/usr/bin/env python3
"""Перевіряє, що скопійований скіл працює без репозиторію навколо."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / "scripts"))

from humanizer_ua.version import VERSION  # noqa: E402


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding="utf-8", timeout=120)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    temp = Path(tempfile.mkdtemp(prefix="humanizer-ua-"))
    target = temp / "humanizer-ua"
    try:
        shutil.copytree(
            SKILL,
            target,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
        )

        version = run([sys.executable, "scripts/scan.py", "--version"], target)
        expected = f"humanizer-ua {VERSION}"
        if version.returncode != 0 or version.stdout.strip() != expected:
            print(f"RESULT: FAIL install-smoke (version: {version.stdout.strip()!r}, stderr: {version.stderr.strip()!r})")
            return 1

        for test in ("scripts/test_scan.py", "scripts/test_rules.py"):
            result = run([sys.executable, "-m", "unittest", test, "-q"], target)
            if result.returncode != 0:
                print(f"RESULT: FAIL install-smoke ({test})")
                print(result.stderr)
                return 1

        print(f"RESULT: PASS install-smoke ({VERSION})")
        return 0
    finally:
        shutil.rmtree(temp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
