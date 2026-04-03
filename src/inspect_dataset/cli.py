from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from inspect_dataset.loader import load_hf_dataset, load_task_from_spec, resolve_fields
from inspect_dataset.report import print_report, save_findings
from inspect_dataset.scanner import run_scanners
from inspect_dataset.scanners import BUILTIN_SCANNER_NAMES, BUILTIN_SCANNERS


@click.group()
def cli() -> None:
    """inspect-dataset — dataset quality scanner for AI evaluation benchmarks."""


@cli.command()
@click.argument("dataset")
@click.option("--split", default="train", show_default=True, help="Dataset split to load.")
@click.option("--revision", default=None, help="Dataset revision / commit SHA to pin.")
@click.option("--question-field", default=None, help="Column name for questions (auto-detected if omitted).")
@click.option("--answer-field", default=None, help="Column name for answers (auto-detected if omitted).")
@click.option("--id-field", default=None, help="Column name for sample IDs (auto-detected if omitted).")
@click.option("--image-field", default=None, help="Column name for images. Used by duplicate_questions to distinguish same-question/different-image pairs from true duplicates.")
@click.option(
    "--scanners",
    default=None,
    help=(
        "Comma-separated list of scanners to run. "
        f"Available: {', '.join(BUILTIN_SCANNER_NAMES)}. "
        "Defaults to all scanners."
    ),
)
@click.option(
    "--max-answer-words",
    default=4,
    show_default=True,
    help="Threshold for the answer_length scanner.",
)
@click.option("--limit", default=None, type=int, help="Cap number of samples loaded.")
@click.option(
    "-o",
    "--output-dir",
    default=None,
    type=click.Path(),
    help="Save findings JSON + REPORT.md to this directory.",
)
def scan(
    dataset: str,
    split: str,
    revision: str | None,
    question_field: str | None,
    answer_field: str | None,
    id_field: str | None,
    image_field: str | None,
    scanners: str | None,
    max_answer_words: int,
    limit: int | None,
    output_dir: str | None,
) -> None:
    """Scan a dataset for quality issues.

    DATASET is one of:

    \b
      - A HuggingFace dataset path:    flaviagiammarino/vqa-rad
      - An inspect_ai registry name:   inspect_evals/medqa
      - A file + task name:            path/to/task.py@task_fn
      - A module + task name:          inspect_evals.medqa@medqa
    """
    console = Console()

    # Resolve scanners
    if scanners:
        names = [n.strip() for n in scanners.split(",")]
        unknown = [n for n in names if n not in BUILTIN_SCANNER_NAMES]
        if unknown:
            raise click.BadParameter(
                f"Unknown scanner(s): {', '.join(unknown)}. "
                f"Available: {', '.join(BUILTIN_SCANNER_NAMES)}",
                param_hint="--scanners",
            )
        scanner_list = [BUILTIN_SCANNER_NAMES[n] for n in names]
    else:
        scanner_list = list(BUILTIN_SCANNERS)

    # Apply per-scanner options
    if max_answer_words != 4:
        from inspect_dataset.scanners.answer_length import _make_scanner
        scanner_list = [
            _make_scanner(max_answer_words) if s.name == "answer_length" else s
            for s in scanner_list
        ]

    # Detect inspect_ai task spec.
    # - "@" present → always a task spec (module@fn or file@fn)
    # - "package/task" with no "@" → task if "package" is an installed Python
    #   package (importlib.util.find_spec returns non-None); HF slugs like
    #   "owner/dataset" have no corresponding Python package.
    import importlib.util as _ilu
    is_task = "@" in dataset or (
        "/" in dataset
        and _ilu.find_spec(dataset.split("/")[0]) is not None
    )

    if is_task:
        console.print(f"Loading inspect_ai task [bold]{dataset}[/bold]...")
        records, fields = load_task_from_spec(dataset, limit=limit)
        # Allow field overrides even on the task path
        if question_field or answer_field or id_field:
            fields = resolve_fields(records, question_field, answer_field, id_field, image_field)
    else:
        console.print(f"Loading [bold]{dataset}[/bold] split=[bold]{split}[/bold]...")
        records = load_hf_dataset(dataset, split=split, revision=revision, limit=limit)
        fields = resolve_fields(records, question_field, answer_field, id_field, image_field)

    console.print(f"  Loaded {len(records):,} samples.")
    console.print(
        f"  Fields: question=[bold]{fields.question}[/bold]  "
        f"answer=[bold]{fields.answer}[/bold]"
        + (f"  id=[bold]{fields.id}[/bold]" if fields.id else "")
    )

    console.print(f"\nRunning {len(scanner_list)} scanner(s)...")
    run = run_scanners(
        records,
        fields,
        scanner_list,
        dataset_name=dataset,
        split=split,
    )

    print_report(run, console=console)

    if output_dir:
        out = Path(output_dir)
        save_findings(run, out)
        console.print(f"Findings saved to [bold]{out}[/bold]")


@cli.command()
@click.argument("findings_dir", type=click.Path(exists=True))
def report(findings_dir: str) -> None:
    """Print a summary report from a saved findings directory."""
    import json

    console = Console()
    path = Path(findings_dir)
    summary_file = path / "scan_summary.json"

    if not summary_file.exists():
        raise click.ClickException(f"No scan_summary.json found in {findings_dir}")

    summary = json.loads(summary_file.read_text())
    console.print_json(json.dumps(summary, indent=2))

    report_file = path / "REPORT.md"
    if report_file.exists():
        console.print(f"\nFull report: [bold]{report_file}[/bold]")
