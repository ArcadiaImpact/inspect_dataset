from __future__ import annotations

from typing import Any, Callable

from inspect_dataset._types import FieldMap, Finding, Record, ScanRun

DatasetScanner = Callable[[list[Record], FieldMap], list[Finding]]


class ScannerDef:
    """A named scanner with metadata."""

    def __init__(
        self,
        name: str,
        fn: DatasetScanner,
        description: str = "",
    ) -> None:
        self.name = name
        self.fn = fn
        self.description = description

    def __call__(self, records: list[Record], fields: FieldMap) -> list[Finding]:
        return self.fn(records, fields)


def dataset_scanner(
    description: str = "",
) -> Callable[[DatasetScanner], ScannerDef]:
    """Decorator that wraps a scanner function into a ScannerDef.

    Usage::

        @dataset_scanner(description="Flag long answers")
        def answer_length(records, fields):
            ...
    """

    def decorator(fn: DatasetScanner) -> ScannerDef:
        return ScannerDef(name=fn.__name__, fn=fn, description=description)

    return decorator


def run_scanners(
    records: list[Record],
    fields: FieldMap,
    scanners: list[ScannerDef],
    dataset_name: str = "",
    split: str | None = None,
) -> ScanRun:
    all_findings: list[Finding] = []
    for scanner in scanners:
        findings = scanner(records, fields)
        # Ensure scanner name is stamped on every finding
        for f in findings:
            f.scanner = scanner.name
        all_findings.extend(findings)
    return ScanRun(
        dataset_name=dataset_name,
        split=split,
        total_samples=len(records),
        findings=all_findings,
    )


def get_field_value(record: Record, field_name: str) -> Any:
    return record.get(field_name)


def get_sample_id(record: Record, fields: FieldMap, index: int) -> str | int | None:
    if fields.id is not None:
        return record.get(fields.id)
    return index
