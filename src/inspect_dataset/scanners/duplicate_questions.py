from __future__ import annotations

import hashlib
from collections import defaultdict

from inspect_dataset._types import FieldMap, Finding, Record
from inspect_dataset.scanner import ScannerDef, get_sample_id


def _image_key(record: Record, image_field: str) -> str | None:
    """Return a stable key for the image in this record, or None if unavailable."""
    img = record.get(image_field)
    if img is None:
        return None
    if isinstance(img, dict):
        # HuggingFace Image(decode=False) → {"bytes": ..., "path": ...}
        raw = img.get("bytes")
        if raw:
            return hashlib.md5(raw).hexdigest()
        return img.get("path")
    if isinstance(img, (str, bytes)):
        return str(img)
    return None


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
        answers = [
            str(r.get(fields.answer, "") or "").strip().lower()
            for _, r in occurrences
        ]
        answers_agree = len(set(answers)) == 1

        # If an image field is provided, note whether images also match
        if fields.image is not None:
            image_keys = [_image_key(r, fields.image) for _, r in occurrences]
            images_agree = len(set(k for k in image_keys if k is not None)) == 1
        else:
            image_keys = []
            images_agree = None

        if answers_agree:
            # Same question, same answer — most likely a real duplicate
            severity: str = "high"
            explanation = (
                f"Question appears {len(occurrences)} times with the same answer "
                f"{answers[0]!r} (at indices {indices}). "
                "This is likely a duplicated sample."
            )
        else:
            # Same question, different answers — typical of multimodal datasets
            # where the same question is asked about different images
            severity = "low"
            explanation = (
                f"Question appears {len(occurrences)} times with different answers "
                f"(at indices {indices}). "
                "In multimodal datasets this is expected — verify images differ."
            )

        for idx, record in occurrences:
            metadata: dict[str, object] = {
                "duplicate_count": len(occurrences),
                "duplicate_indices": indices,
                "question": q_text,
                "answers_agree": answers_agree,
            }
            if fields.image is not None:
                metadata["images_agree"] = images_agree

            findings.append(
                Finding(
                    scanner="duplicate_questions",
                    severity=severity,  # type: ignore[arg-type]
                    category="question_quality",
                    explanation=explanation,
                    sample_index=idx,
                    sample_id=get_sample_id(record, fields, idx),
                    metadata=metadata,
                )
            )
    return findings


duplicate_questions = ScannerDef(
    name="duplicate_questions",
    fn=_scan,
    description=(
        "Flag questions that appear more than once. "
        "Same-answer duplicates are HIGH severity (likely copy errors); "
        "different-answer duplicates are LOW (expected in multimodal datasets)."
    ),
)
