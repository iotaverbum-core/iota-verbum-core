# CUC Benchmark

The CUC benchmark measures whether models can maintain a consistent evidence-grounded analysis across two runs of an Iota Verbum evidence pack, detect perturbations precisely, revise conclusions only when justified, and keep Unknown tracking synchronized with the ground-truth diff.

## Directory Layout

```text
benchmark/
  fixtures/
    FIN-001/
      clean.md
      perturbed.md
      diff.json
    ...
  runs/
    .gitkeep
  __init__.py
  README.md
  run_evaluation.py
  score_responses.py
  system_prompt.txt
```

## Setup

```powershell
pip install -e ".[benchmark]"
```

## Required Environment Variables

- `OPENAI_API_KEY`
- `GOOGLE_API_KEY`
- `ANTHROPIC_API_KEY`

## Usage

Run all cases and models:

```powershell
python benchmark/run_evaluation.py
```

Run selected cases in dry-run mode:

```powershell
python benchmark/run_evaluation.py --cases FIN-001 GEO-003 --models gpt-4o claude-3-5-sonnet --run both --dry-run
```

Score completed Run 2 outputs:

```powershell
python benchmark/score_responses.py --runs-dir benchmark/runs --fixtures-dir benchmark/fixtures --output benchmark/SCORES.csv
```

## Scoring Rubric

| Section | Max Points | Positive Rule | Penalty |
| --- | ---: | --- | --- |
| Q1 Detection | 33 | `+3` per correctly identified ground-truth change | `-5` per hallucinated change |
| Q2 Self-Correction | 33 | `+3` per required revision with original conclusion and plausible revision | `-3` per over-revision |
| Q3 Unknown Tracking | 34 | `+3` per correctly tracked unknown change | `-5` per fabricated unknown change |

Fixture files are populated separately. The repository contains placeholders only.
