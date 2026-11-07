# Humanizer-UA

\[ [Українська](README.md) | **English** \]

More skills: [skills.sh/madeval](https://www.skills.sh/madeval)

Ukrainian text that sounds like a person.

An agent skill that edits Ukrainian prose: removes AI fingerprints, bureaucratese, surzhyk, Russianisms, and calques while keeping meaning, facts, and the author's voice. **Skill class:** lean - a compact routing file plus on-demand references.

[github.com/MADEVAL/humanizer-ua](https://github.com/MADEVAL/humanizer-ua) - author: [Yevhen Leonidov](https://github.com/MADEVAL)

## What it does

- Removes 30 hard bans and 12 norm-layer errors, and works with an 80-marker catalog in eight groups.
- Enforces a fact lock: numbers, dates, names, quotes, conditions, and modality do not change.
- Edits locally: a problem in one sentence does not trigger a rewrite of the whole text.
- Respects genre: marketing, expert, business letter, news, academic, documentation, legal, fiction.
- Ships a dependency-free scanner with three separate scales (norm, style, structure).
- Does not penalize a weak marker when the paragraph has no other signals.
- Checks itself: eval corpus, rubric, trigger tests, and a CI gate.

## Modes

| Mode | When | What to do |
|---|---|---|
| **Edit** (default) | "humanize", "rewrite", "proofread" | Full cycle, return the clean text |
| **Audit** | "check", "find markers" | Diagnostics only, do not change the text |
| **Targeted fix** | "remove only bureaucratese" | Work on the named category, leave the rest |
| **Own draft** | silently, before sending | Check your own Ukrainian text against `references/hard-bans.md` |
| **Voice from samples** | the author supplied 2-3 texts | Build a voice profile with `references/voice.md` |

## Install

```bash
git clone https://github.com/MADEVAL/humanizer-ua.git
cd humanizer-ua
python install.py --target all
```

Or copy the skill folder by hand:

```bash
mkdir -p ~/.claude/skills ~/.config/opencode/skills
cp -r skills/humanizer-ua ~/.claude/skills/
cp -r skills/humanizer-ua ~/.config/opencode/skills/
```

The skill folder is `skills/humanizer-ua/`; the repository root also holds the eval harness, commands, and plugin manifests.

## Scanner

```bash
python3 skills/humanizer-ua/scripts/scan.py article.txt --genre marketing
cat article.txt | python3 skills/humanizer-ua/scripts/scan.py - --genre business
```

Three scales plus a separate fact-risk score. Genre thresholds: `marketing` 85, `docs` and `news` 88, `academic` 90, `legal` 95. No dependencies, no network.

The score is the scanner's rules, not a probability of AI authorship, and not a verdict. It checks 33 of the 80 markers automatically; the rest are reviewed by the agent.

## Requirements

- Plain Markdown for the skill itself.
- Python 3.9+ only for the optional scanner, tests, and eval harness.

## GitHub Description

```
Ukrainian text editing: removes AI fingerprints, bureaucratese, surzhyk, Russianisms, and calques while keeping meaning, facts, and the author's voice.
```

## GitHub Tags

`ai` `ai-agents` `ukrainian` `humanizer` `editing` `prompt-engineering` `ai-writing`

Skills.sh: https://www.skills.sh/madeval/humanizer-ua

## License

MIT.
