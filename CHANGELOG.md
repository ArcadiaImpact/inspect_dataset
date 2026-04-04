# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-04-04

### Added

- **Interactive dataset explorer** (`inspect-dataset view <findings_dir>`):
  - aiohttp backend serving API endpoints and a single-page app.
  - Findings tab with scanner sidebar, severity/triage filters, and detail panel.
  - Samples tab with AG Grid table showing per-sample finding badges.
  - Triage actions (confirm/dismiss) with persistence to `triage.json`.
  - Keyboard shortcuts: `c` confirm, `d` dismiss, `n`/`p` next/prev finding.
  - `clean_ids.txt` export of sample IDs with no confirmed findings.
  - SPA-aware static serving with cache-busting headers (mirrors `inspect_ai` pattern).
- Frontend built with Vite, React, TypeScript, Bootstrap 5, AG Grid, Zustand.
- Playwright end-to-end tests for the view server (10 tests).
- `inspect-dataset tasks` command to list all registered `inspect_ai` tasks.
- `inspect-dataset scanners` command to list all registered scanners.
- `INSPECT_DATASET_MODEL` environment variable support for setting the default
  LLM model; `.env` files in cwd and home directory are loaded automatically.
- `aiohttp` added as a core dependency.
- `playwright` and `pytest-playwright` added to dev dependencies.

## [0.2.0] - 2026-04-03

### Added

- **LLM-powered scanners** enabled via `--model` (e.g. `--model openai/gpt-4o-mini`):
  - `ambiguity` — flags questions that are ambiguous or underspecified.
  - `label_correctness` — flags samples where the ground-truth answer appears incorrect.
  - `answerability` — flags questions unanswerable from the provided context
    (auto-detects context columns like `context`, `passage`, `paragraph`).
- Async scanner infrastructure: `LLMScannerDef`, `run_scanners_async()`.
- LLM helper module (`_llm.py`) with concurrent batch evaluation, semaphore-based
  rate limiting, and structured YES/NO judgment parsing via `inspect_ai` model API.
- `--model` CLI flag to enable LLM scanners.
- LLM scanner registry (`LLM_SCANNER_FACTORIES`) with CLI wiring.
- Tests for all three LLM scanners with mocked LLM calls.

## [0.1.2] - 2026-04-02

### Added

- `inspect_ai` Task/Dataset input support — scan `inspect_evals` tasks directly:
  - `inspect-dataset scan inspect_evals/gpqa` (package/task)
  - `inspect-dataset scan inspect_evals.gpqa@gpqa_diamond` (module@fn)
  - `inspect-dataset scan path/to/task.py@task_fn` (file@fn)
- `load_inspect_task()` and `load_task_from_spec()` in `loader.py` — converts
  `inspect.Sample` to internal `Record`/`FieldMap` format.
- Direct module import for `package/task` specs, bypassing the inspect_ai
  entry-point loader (avoids requiring all optional eval dependencies).
- Task spec vs HuggingFace slug detection via `importlib.util.find_spec`.
- `inspect_ai` added as optional dependency under `[inspect]` extras group.

## [0.1.1] - 2026-04-01

### Added

- `forced_choice_leakage` scanner — flags questions offering explicit options
  via "or" where the answer matches one of the options.
- `encoding_issues` scanner — flags non-printable or control characters in
  questions and answers.
- `binary_question_ratio` scanner — flags datasets where >50% of answers are
  yes/no.
- `--image-field` CLI option for multimodal duplicate detection.

### Changed

- `duplicate_questions` severity split: same question + same answer → HIGH;
  same question + different answers → LOW. With `--image-field`, uses
  (question, image) identity for grouping.

### Fixed

- `inconsistent_format`: false positive on answers ending with "etc.".

## [0.1.0] - 2026-03-31

### Added

- Initial release.
- HuggingFace dataset loader with field auto-detection.
- Four built-in scanners:
  - `answer_length` — flags answers longer than N words (default 4).
  - `duplicate_questions` — flags exact duplicate question text.
  - `inconsistent_format` — flags capitalisation, punctuation, and length outliers.
  - `answer_distribution` — flags class imbalance (≥85% single answer).
- Report generator: rich terminal output + REPORT.md.
- CLI: `inspect-dataset scan <dataset> [options]` with `--split`, `--revision`,
  `--question-field`, `--answer-field`, `--id-field`, `--scanners`,
  `--max-answer-words`, `--limit`, `-o/--output-dir`.
- JSON + Markdown output when `--output-dir` is given.
- Unit tests for all scanners.
