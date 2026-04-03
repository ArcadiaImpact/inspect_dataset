# inspect-dataset: Plan

A dataset quality scanner for AI evaluation datasets. Companion to
[inspect-scout](https://github.com/meridian-labs/inspect-scout), which scans
agent trajectories — inspect-dataset scans the underlying datasets themselves.

**Organisation:** Arcadia  
**Status:** v0.2.0 complete

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

### v0.1.1 — Scanner improvements from VQA-RAD audit ✓

Findings from auditing `flaviagiammarino/vqa-rad` (451 test samples) exposed three
gaps in the built-in scanners and one needed improvement:

- [x] **`duplicate_questions` severity split** — the scanner currently flags all
  duplicate questions as HIGH. In multimodal datasets, the same question is often
  asked about different images with different answers (valid). Split into:
  - Same question + same answer → HIGH (likely a real duplicate / copy-paste error)
  - Same question + different answers → LOW (informational; image context differentiates)
  This requires an `--image-field` option so the scanner can check whether the image
  also differs.
- [x] **`forced_choice_leakage` scanner** — flag questions that contain " or " where
  the answer is one of the explicitly offered options (e.g. *"is this an MRI or a CT
  scan?" → "mri"*). A model can exploit the question phrasing without visual
  understanding. Category: `leakage`, severity: `medium`.
- [x] **`encoding_issues` scanner** — flag questions or answers containing
  non-printable or non-ASCII characters (tabs, nulls, control characters, etc.).
  Found one real instance in VQA-RAD: `'skull \tcartilage and medulla'` (tab char).
  Category: `format`, severity: `low`.
- [x] **`binary_question_ratio` scanner** — flag datasets where a high proportion of
  questions are binary (yes/no answers), even if no single answer dominates above the
  85% imbalance threshold. VQA-RAD is 56% yes/no; a naive "always say no" strategy
  scores 29.5%. Complements `answer_distribution`. Category: `distribution`,
  severity: `low`.

### v0.1 — Tasks

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

### v0.1.2 — inspect.Task / inspect.Dataset input ✓

`inspect_ai` Task objects (e.g. from `inspect_evals`) are now accepted as a
scan source alongside HuggingFace slugs. Four spec formats are supported:

```bash
inspect-dataset scan inspect_evals/gpqa_diamond      # package/task (recommended)
inspect-dataset scan inspect_evals.gpqa@gpqa_diamond # module@fn
inspect-dataset scan path/to/task.py@task_fn         # file@fn (via inspect_ai)
inspect-dataset scan flaviagiammarino/vqa-rad        # HF slug (unchanged)
```

`inspect.Sample` fields are mapped to the internal `Record`/`FieldMap` format:

| `inspect.Sample` field | maps to |
| ---------------------- | ------- |
| `input` (str or last user ChatMessage) | `question` |
| `target` (first element if list) | `answer` |
| `id` | sample id |
| `metadata` | merged into record |
| `files` | stored under `__files__` for view server |

The `package/task` path imports `package.task_name` directly and scans for
`@task`-decorated callables, bypassing the inspect_ai entry-point loader
(which requires all optional eval dependencies to be installed). Detection of
task specs vs HF slugs uses `importlib.util.find_spec` — if the left side of
`/` is an installed Python package, it's treated as a task spec.

- [x] `loader.py`: `load_inspect_task()`, `load_task_from_spec()` — converts
  `inspect.Sample` to `Record`; handles `str` input, `list[ChatMessage]`,
  `list[ContentBlock]`, and dict messages
- [x] `loader.py`: `files` preserved under `__files__` for view server
- [x] CLI: `find_spec`-based heuristic detects task specs vs HF slugs;
  `module@fn` and `package/task` both routed correctly
- [ ] `scan_summary.json`: record source type and import path (needed for view
  server to reload samples on demand) — deferred to v0.4
- [ ] View server: serve `__files__` bytes for inline rendering — deferred to v0.4

### v0.2 — LLM scanners ✓

Three LLM-powered scanners that use `inspect_ai`'s model API. Enabled via
`--model` (e.g. `--model openai/gpt-4o-mini`). Without `--model`, only static
scanners run — existing behaviour is unchanged.

Architecture additions:

- `_llm.py`: model resolution via `inspect_ai.model.get_model()`, concurrent
  batch evaluation with semaphore-based rate limiting, structured YES/NO
  judgment parsing
- `LLMScannerDef`: async counterpart to `ScannerDef`; factory pattern
  (`_make_scanner(model_name)`) so the model is bound at CLI time
- `run_scanners_async()`: runs sync scanners sequentially then async scanners
  concurrently via `asyncio.gather`

Scanners:

- [x] `ambiguity` — LLM: "is this question ambiguous or underspecified?"
  Category: `question_quality`, severity: `medium`
- [x] `label_correctness` — LLM: "is this answer incorrect?"
  Category: `label_quality`, severity: `high`
- [x] `answerability` — LLM: "can this be answered from the provided context?"
  Auto-detects context columns (`context`, `passage`, `paragraph`, etc.).
  Category: `question_quality`, severity: `medium`
- [x] `--model` CLI flag
- [x] Async scanner runner (`run_scanners_async`)
- [x] LLM scanner registry (`LLM_SCANNER_FACTORIES`) + CLI wiring
- [x] Tests for all three scanners (mocked LLM calls)

### v0.3 — Eval-informed scanners (inspect-scout integration, planned)

- [ ] `universal_failure` — all models fail → bad label candidate
- [ ] `universal_success` — all models succeed → leakage candidate
- [ ] `high_variance` — models disagree sharply → ambiguity candidate
- [ ] `model_contradicts_label` — model answer matches label but scorer gave 0
- [ ] `--scout-results` CLI flag accepts inspect-scout parquet directory

### v0.4 — Interactive dataset explorer (planned)

A local web UI for triaging findings — findings-first navigation rather than
data-first. The goal is to let a researcher work through flagged samples quickly,
dismiss false positives, and export a clean sample list.

#### Motivation

The HuggingFace dataset viewer lets you browse and SQL-query a dataset, but it
has no concept of quality findings. The `inspect-dataset report` command gives a
static summary. Neither lets you *triage*: step through each flagged sample,
look at the raw record, decide keep/dismiss, and track your decisions.

#### Existing infrastructure to leverage

The `inspect` log viewer (`@meridianlabs/log-viewer`, source at
`inspect_ai/src/inspect_ai/_view/www/`) uses the same pattern we'd follow:

- **Python backend**: aiohttp (or FastAPI) server, launched by a CLI command,
  opens a browser tab, serves a React SPA + REST API on localhost
- **Frontend stack**: React 19, Bootstrap 5, ag-grid for tables, Zustand for
  state, Vite build — all published as an npm library
- **Server pattern**: port-file management, kills stale servers, optional auth
  token for IDE integration

inspect-scout's `view` command wraps the same infrastructure for scout results.
We should follow the identical pattern so the three tools feel like a family.

The UI has two complementary modes, toggled by a top-level tab:

- **Findings view** — findings-first triage: work through every flagged sample,
  confirm or dismiss, export a clean list
- **Samples view** — dataset-first browsing: see every sample in a table with
  findings overlaid as badges; useful for spot-checking and exploring the raw data

#### Design

```bash
inspect-dataset view findings/
```

Launches a local webserver (default port 7576) and opens a browser.

**Findings tab — three-panel layout:**

```text
┌─────────────────────────────────────────────────────────────────┐
│  inspect-dataset  │  flaviagiammarino/vqa-rad  │  451 samples   │
│  [Findings ●]  [Samples]                                        │
│  83 findings  ·  0 dismissed  ·  0 confirmed                    │
├──────────────┬──────────────────────────────┬────────────────────┤
│  SCANNERS    │  FINDING                     │  SAMPLE            │
│              │                              │                    │
│ ● dup_q  37  │  [▲ MEDIUM]                 │  idx: 83           │
│ ● fcl    14  │  Same Q, diff images,        │  Q: is this an    │
│ ● ans_ln 20  │  same answer "no"            │     mri?          │
│ ● enc     2  │  indices: [83, 206]          │  A: no            │
│ ● dist    9  │                              │  image: [thumb]   │
│              │  ─────────────────────────── │                    │
│              │  [▲ MEDIUM]  ...             │  ──────────────── │
│              │  [▲ MEDIUM]  ...             │  [CONFIRM]        │
│              │                              │  [DISMISS]        │
│              │                              │  [SKIP]           │
└──────────────┴──────────────────────────────┴────────────────────┘
```

**Samples tab — dataset browser:**

```text
┌─────────────────────────────────────────────────────────────────┐
│  inspect-dataset  │  flaviagiammarino/vqa-rad  │  451 samples   │
│  [Findings]  [Samples ●]                                        │
│  Search: [________________]  Filter: [All ▼] [Any severity ▼]  │
├──────┬─────────────────────────────────┬──────────┬─────────────┤
│  idx │  question                       │  answer  │  findings   │
├──────┼─────────────────────────────────┼──────────┼─────────────┤
│    6 │  is the colon more prominent…   │  left    │  ▲ fcl      │
│   11 │  what structures are visible…   │  skull…  │  ● enc      │
│   83 │  is this an mri?                │  no      │  ▲ dup_q    │
│   86 │  is this an mri or a ct scan?   │  mri     │  ▲ fcl      │
│   … │  …                              │  …       │             │
└──────┴─────────────────────────────────┴──────────┴─────────────┘
                                                  [click row → detail panel]
```

ag-grid table, virtualised for large datasets. Findings column shows severity
badges; clicking a row opens the full sample detail in a side panel. Rows with
no findings are dimmed but visible — this is what makes it different from the
HF viewer: you see everything with findings overlaid.

**Key interactions:**

- Filter findings by scanner, severity, category, or triage status
- Click a finding → loads the sample record in the right panel
- For duplicate groups, show *all* members side-by-side
- Image fields rendered inline (HF `Image` feature / `inspect.Sample` files)
- Keyboard shortcuts: `c` confirm, `d` dismiss, `n/p` next/prev
- Decisions persisted to `findings/triage.json`

**REST API (aiohttp backend):**

| Endpoint | Description |
| -------- | ----------- |
| `GET /api/findings` | All findings from the output directory |
| `GET /api/summary` | Scanner/severity counts |
| `GET /api/sample/{idx}` | Raw record from the dataset |
| `POST /api/triage` | Save a confirm/dismiss decision |
| `GET /api/triage` | Current triage state |
| `GET /api/export` | Download `clean_ids.txt` |

The backend streams the dataset on demand (no full load into memory) by
re-opening the HF dataset with the same parameters recorded in
`scan_summary.json`.

#### Implementation tasks

- [ ] `inspect-dataset view findings/` CLI command (click, mirrors inspect's
  `view start` pattern)
- [ ] aiohttp server with the endpoints above; port-file management
- [ ] React SPA (Vite, Bootstrap 5, ag-grid) — two-tab layout
- [ ] Findings tab: finding list with filter/sort; sample detail panel
- [ ] Samples tab: ag-grid table of all records with findings badges; side panel
- [ ] Sample panel: renders question/answer/image fields; side-by-side for
  duplicate groups; handles both HF `Image` and `inspect.Sample` `files`
- [ ] Triage actions (confirm/dismiss/skip) persisted to `triage.json`
- [ ] `clean_ids.txt` export — sample IDs with no confirmed findings
- [ ] Keyboard shortcut layer

#### Reuse opportunities

- Lift the aiohttp server scaffold directly from
  `inspect_ai/src/inspect_ai/_view/server.py` — port management, static file
  serving, browser-open logic
- Use the same Bootstrap 5 + ag-grid versions for visual consistency with the
  inspect family
- Consider whether the `@meridianlabs/log-viewer` library's `MetadataPanel` or
  `JsonPanel` components can be imported for the raw-record display rather than
  re-implementing them

---

## CLI Design

```bash
# Scan a HuggingFace dataset
inspect-dataset scan flaviagiammarino/vqa-rad \
  --split test \
  --answer-field answer \
  --question-field question \
  -o findings/

# Scan an inspect_ai Task — package/task (recommended)
inspect-dataset scan inspect_evals/gpqa_diamond -o findings/

# Or with explicit module@fn syntax
inspect-dataset scan inspect_evals.gpqa@gpqa_diamond -o findings/

# Limit to specific scanners
inspect-dataset scan ... --scanners answer_length,duplicate_questions

# Custom max answer words threshold
inspect-dataset scan ... --max-answer-words 6

# View report from saved findings
inspect-dataset report findings/

# Interactive dataset explorer (v0.4)
inspect-dataset view findings/

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
