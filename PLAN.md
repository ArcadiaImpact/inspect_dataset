# inspect-dataset: Plan

A dataset quality scanner for AI evaluation datasets. Companion to
[inspect-scout](https://github.com/meridian-labs/inspect-scout), which scans
agent trajectories — inspect-dataset scans the underlying datasets themselves.

**Organisation:** Arcadia  
**Status:** v0.1 complete, v0.1.1 in development

---

## Problem

When building evaluation benchmarks, verifying that every sample is valid is
slow and often done poorly. Common issues that slip through:

- Ground-truth answers that are too long to be reproduced verbatim by exact-match scorers
- Duplicate questions (inflated sample counts, biased metrics)
- Formatting inconsistencies in answers (case, punctuation, length outliers)
- Class imbalance (e.g. 90% "yes" in a yes/no benchmark)
- Answers leaked in the question text
- Questions that are unanswerable given the provided context

inspect-scout provides a complementary signal: samples that *all* models
consistently fail on are strong candidates for bad labels.

---

## Design

### Two modes

| Mode | Input | Use case |
| ---- | ----- | -------- |
| **Static** | Dataset (HuggingFace / CSV / JSON) | Pre-eval quality pass |
| **Eval-informed** | Dataset + inspect-scout parquet results | Post-eval deep audit |

v0.1 implements static mode only.

### Scanner interface

```python
# A scanner is a plain function: list of records → list of findings
def my_scanner(records: list[dict[str, Any]], fields: FieldMap) -> list[Finding]:
    ...
```

- `records`: raw dataset rows as dicts
- `fields`: resolved field mapping (question, answer, id fields)
- Returns zero or more `Finding` objects, one per flagged sample

Scanners are collected in a registry. The CLI runs all (or a named subset).

### Core types

```python
@dataclass
class Finding:
    scanner: str               # which scanner produced this
    severity: Severity         # "low" | "medium" | "high"
    category: Category         # "label_quality" | "question_quality" | "distribution" | "format" | "leakage"
    explanation: str
    sample_id: str | int | None
    sample_index: int
    metadata: dict[str, Any]   # scanner-specific extras (e.g. word count, duplicate_of)

@dataclass
class FieldMap:
    question: str   # field name for the question/prompt
    answer: str     # field name for the ground-truth answer
    id: str | None  # field name for the sample id (optional)
```

### Output (v0.1)

```text
<output-dir>/
    answer_length.json
    duplicate_questions.json
    inconsistent_format.json
    answer_distribution.json
    scan_summary.json       # counts by scanner/severity/category
    REPORT.md               # human-readable markdown
```

---

## Phased Roadmap

### v0.1 — Static scanners, CLI, JSON + markdown output ✓

### v0.1.1 — Scanner improvements from VQA-RAD audit ← **current**

Findings from auditing `flaviagiammarino/vqa-rad` (451 test samples) exposed three
gaps in the built-in scanners and one needed improvement:

- [ ] **`duplicate_questions` severity split** — the scanner currently flags all
  duplicate questions as HIGH. In multimodal datasets, the same question is often
  asked about different images with different answers (valid). Split into:
  - Same question + same answer → HIGH (likely a real duplicate / copy-paste error)
  - Same question + different answers → LOW (informational; image context differentiates)
  This requires an `--image-field` option so the scanner can check whether the image
  also differs.
- [ ] **`forced_choice_leakage` scanner** — flag questions that contain " or " where
  the answer is one of the explicitly offered options (e.g. *"is this an MRI or a CT
  scan?" → "mri"*). A model can exploit the question phrasing without visual
  understanding. Category: `leakage`, severity: `medium`.
- [ ] **`encoding_issues` scanner** — flag questions or answers containing
  non-printable or non-ASCII characters (tabs, nulls, control characters, etc.).
  Found one real instance in VQA-RAD: `'skull \tcartilage and medulla'` (tab char).
  Category: `format`, severity: `low`.
- [ ] **`binary_question_ratio` scanner** — flag datasets where a high proportion of
  questions are binary (yes/no answers), even if no single answer dominates above the
  85% imbalance threshold. VQA-RAD is 56% yes/no; a naive "always say no" strategy
  scores 29.5%. Complements `answer_distribution`. Category: `distribution`,
  severity: `low`.

### v0.1 — Static scanners, CLI, JSON + markdown output

- [x] Project scaffold (uv, pyproject.toml)
- [x] Core types: `Finding`, `FieldMap`, `Severity`, `Category`
- [x] Scanner runner: `run_scanners(records, fields, scanners) -> ScanRun`
- [x] Loaders: HuggingFace dataset, field auto-detection
- [x] Scanners:
  - [x] `answer_length` — answers above N words (exact-match proxy weakness)
  - [x] `duplicate_questions` — exact duplicate question text (known limitation: false positives on multimodal datasets where the same question is asked about different images — fix planned: `--image-field` option)
  - [x] `inconsistent_format` — case / punctuation / length outliers
  - [x] `answer_distribution` — class imbalance detection
- [x] Report generator: rich terminal output + REPORT.md
- [x] CLI: `inspect-dataset scan <dataset> [options]`
- [x] Tests: unit tests for each scanner
- [x] README

### v0.2 — LLM scanners (planned)

- [ ] `ambiguity` — LLM: "is this question unambiguous?"
- [ ] `label_correctness` — LLM: "is this answer correct?"
- [ ] `answerability` — LLM: "can this be answered from the provided context?"
- [ ] `--model` CLI flag
- [ ] Async scanner runner

### v0.3 — Eval-informed scanners (inspect-scout integration, planned)

- [ ] `universal_failure` — all models fail → bad label candidate
- [ ] `universal_success` — all models succeed → leakage candidate
- [ ] `high_variance` — models disagree sharply → ambiguity candidate
- [ ] `model_contradicts_label` — model answer matches label but scorer gave 0
- [ ] `--scout-results` CLI flag accepts inspect-scout parquet directory

### v0.4 — Interactive review + export (planned)

- [ ] `inspect-dataset review findings/` — step through flagged samples
- [ ] `clean_ids.txt` export — sample IDs that passed all scanners
- [ ] Re-run eval filtered to clean samples for quality-adjusted score

---

## CLI Design

```bash
# Scan a HuggingFace dataset (static)
inspect-dataset scan flaviagiammarino/vqa-rad \
  --split test \
  --answer-field answer \
  --question-field question \
  -o findings/

# Limit to specific scanners
inspect-dataset scan ... --scanners answer_length,duplicate_questions

# Custom max answer words threshold
inspect-dataset scan ... --max-answer-words 6

# View report from saved findings
inspect-dataset report findings/

# (v0.3) Enrich with inspect-scout results
inspect-dataset scan ... --scout-results scout_results/
```

---

## Integration with inspect-scout

```text
Dataset ──► inspect-dataset (static) ──► findings/
                                              │
Eval run ──► inspect-scout ──► scout_results/─┘
                                              │
                                    inspect-dataset (eval-informed)
                                              │
                                    REPORT.md + clean_ids.txt
```

The `clean_ids.txt` output feeds back into eval workflows — re-run the eval
filtered to clean samples only for a quality-adjusted benchmark score.

---

## Directory Structure (target)

```text
inspect-dataset/
    src/inspect_dataset/
        __init__.py
        _types.py           # Finding, FieldMap, Severity, Category
        scanner.py          # run_scanners(), ScanRun
        loader.py           # HF + CSV/JSON loading, field auto-detection
        report.py           # terminal + markdown report generation
        cli.py              # click CLI entry point
        scanners/
            __init__.py     # BUILTIN_SCANNERS registry
            answer_length.py
            duplicate_questions.py
            inconsistent_format.py
            answer_distribution.py
    tests/
        test_answer_length.py
        test_duplicate_questions.py
        test_inconsistent_format.py
        test_answer_distribution.py
    PLAN.md
    README.md
    pyproject.toml
```
