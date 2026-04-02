# inspect-dataset

Dataset quality scanner for AI evaluation benchmarks. Companion to [inspect-scout](https://github.com/meridian-labs/inspect-scout), which analyses agent trajectories — inspect-dataset audits the underlying datasets themselves.

## Installation

```bash
pip install inspect-dataset
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv add inspect-dataset
```

## Usage

```bash
# Scan a HuggingFace dataset
inspect-dataset scan flaviagiammarino/vqa-rad --split test -o findings/

# Pin to a specific revision
inspect-dataset scan flaviagiammarino/vqa-rad --revision abc123 -o findings/

# Override auto-detected field names
inspect-dataset scan my-org/my-dataset \
  --question-field prompt \
  --answer-field label \
  -o findings/

# Run only specific scanners
inspect-dataset scan flaviagiammarino/vqa-rad \
  --scanners answer_length,duplicate_questions

# Adjust answer length threshold (default: 4 words)
inspect-dataset scan flaviagiammarino/vqa-rad --max-answer-words 6

# Limit samples loaded
inspect-dataset scan flaviagiammarino/vqa-rad --limit 500

# View a saved report
inspect-dataset report findings/
```

## Scanners

| Scanner | Severity | What it flags |
| ------- | -------- | ------------- |
| `answer_length` | medium | Answers longer than N words (default: 4). Long answers are unlikely to be reproduced verbatim by exact-match scorers. |
| `duplicate_questions` | high | Questions that appear more than once. Duplicates inflate sample counts and bias metrics. |
| `inconsistent_format` | low/medium | Capitalisation, punctuation, or length deviations from the dataset majority (80%+ threshold). |
| `answer_distribution` | high | Datasets where a single answer accounts for ≥85% of samples — a model that always predicts that answer would score highly without any understanding. |

## Output

When `--output-dir` is given, findings are written as:

```text
findings/
    answer_length.json
    duplicate_questions.json
    inconsistent_format.json
    answer_distribution.json
    scan_summary.json    # counts by scanner/severity/category
    REPORT.md            # human-readable markdown
```

Each finding includes the scanner name, severity, category, explanation, sample index, sample ID (if available), and scanner-specific metadata.

## Integration with inspect-scout

inspect-scout tracks which samples models consistently fail or succeed on. inspect-dataset provides a complementary static pass before running evals. A future release will accept inspect-scout results directly to produce eval-informed findings and a `clean_ids.txt` export for quality-adjusted benchmark scores.

## Development

```bash
uv sync --extra dev
uv run pytest
```
