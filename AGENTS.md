# Guide for agents

This repository contains the `humanizer-ua` skill: a Ukrainian text editor for agent skills.

## Rules

- `skills/humanizer-ua/SKILL.md` is the product. Keep it short; every word is read on each use.
- Reference files explain one topic each. Do not duplicate the whole catalog in `SKILL.md`.
- Rule IDs are stable: `HB01–HB30` for hard bans, `A1–H6` for catalog markers. Do not renumber. Adding a pattern means a new ID in its group, never a shift of the others.
- If you add a scanner rule, add it to `references/hard-bans.md` or `references/catalog.md`, add a test, and update `CHANGELOG.md`.
- Keep versions in sync: `SKILL.md` (`metadata.version`), `CHANGELOG.md`, `.claude-plugin/plugin.json`, `.cursor-plugin/plugin.json`.
- Write in Ukrainian for skill content. Use plain language, active voice, short sentences.

## Checks

Quick check: `make check` runs the same full suite as `validate_package.py --full`.

```bash
python scripts/validate_package.py --full
python -m unittest skills/humanizer-ua/scripts/test_scan.py -v
python -m unittest skills/humanizer-ua/scripts/test_rules.py -v
python skills/humanizer-ua/scripts/lint_skill.py
python skills/humanizer-ua/scripts/check_examples.py
python skills/humanizer-ua/scripts/install_smoke.py
python skills/humanizer-ua/scripts/self_scan.py
python skills/humanizer-ua/scripts/scan_gate.py eval/corpus/human --min-score 90
python eval/run_eval.py
python eval/run_triggers.py
```

## Adding a marker

1. Check that no existing marker covers it.
2. Add an entry to `references/catalog.md` with ID, strength, genre note, and a before/after pair that does not invent facts.
3. If the marker has a stable phrase, add a rule to `scripts/humanizer_ua/rules.py` and, if it is a hard ban, a row to `references/hard-bans.md`.
4. Add a positive example to `scripts/test_rules.py` and, if the behavior is new, a test to `scripts/test_scan.py`.
5. Run the checks.
6. Add a `CHANGELOG.md` note.

## Changing the scanner

- The scanner is deterministic. No network, no models, no third-party packages.
- Keep `scan.py` independent from the agent runtime.
- Mask code, URLs, and quotes before matching. Do not flag text inside them.
- Report line numbers from the original text.
- Keep `--json` stable; integrations depend on it.
- Do not call the score “AI probability”.

## Language

- Use «» for quotes.
- Use ’ for apostrophes in prose.
- Use — with spaces for dashes; – without spaces for ranges.
- Use sentence case in headings.
- Russian letters (`ё`, `ы`, `э`, `ъ`) are errors in Ukrainian text.
