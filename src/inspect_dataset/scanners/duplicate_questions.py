from __future__ import annotations

from collections import defaultdict

from inspect_dataset._types import FieldMap, Finding, Record
from inspect_dataset.scanner import ScannerDef, get_sample_id


def _scan(records: list[Record], fields: FieldMap) -> list[Finding]:
    # Map normalised question text → list of (index, record)
    seen: dict[str, list[tuple[int, Record]]] = defaultdict(list)
    for i, record in enumerate(records):
        q = str(record.get(fields.question, "") or "").strip().lower()
        seen[q].append((i, record))

    findings = []
    for q_text, occurrences in seen.items():
        if len(occurrences) <= 1:
            continue
        indices = [idx for idx, _ in occurrences]
        for idx, record in occurrences:
            findings.append(
                Finding(
                    scanner="duplicate_questions",
                    severity="high",
                    category="question_quality",
                    explanation=(
                        f"Question appears {len(occurrences)} times in the dataset "
                        f"(at indices {indices}). "
                        f"Duplicates inflate sample counts and bias metrics. "
                        f"Question: {q_text!r}"
                    ),
                    sample_index=idx,
                    sample_id=get_sample_id(record, fields, idx),
                    metadata={
                        "duplicate_count": len(occurrences),
                        "duplicate_indices": indices,
                        "question": q_text,
                    },
                )
            )
    return findings


duplicate_questions = ScannerDef(
    name="duplicate_questions",
    fn=_scan,
    description="Flag questions that appear more than once in the dataset.",
)
