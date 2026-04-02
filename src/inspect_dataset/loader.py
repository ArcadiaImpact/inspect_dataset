from __future__ import annotations

from typing import Any

from inspect_dataset._types import FieldMap, Record

# Common field name candidates for auto-detection, in priority order
_QUESTION_CANDIDATES = ["question", "prompt", "input", "text", "query", "instruction"]
_ANSWER_CANDIDATES = ["answer", "label", "target", "output", "response", "gold"]
_ID_CANDIDATES = ["id", "sample_id", "idx", "index", "qid"]


def auto_detect_fields(columns: list[str]) -> FieldMap:
    """Infer question/answer/id field names from column names."""

    def pick(candidates: list[str]) -> str | None:
        for c in candidates:
            if c in columns:
                return c
        # Case-insensitive fallback
        lower = {col.lower(): col for col in columns}
        for c in candidates:
            if c in lower:
                return lower[c]
        return None

    question = pick(_QUESTION_CANDIDATES)
    answer = pick(_ANSWER_CANDIDATES)

    if question is None or answer is None:
        raise ValueError(
            f"Could not auto-detect question/answer fields from columns: {columns}. "
            "Use --question-field and --answer-field to specify them explicitly."
        )

    return FieldMap(
        question=question,
        answer=answer,
        id=pick(_ID_CANDIDATES),
    )


def load_hf_dataset(
    path: str,
    split: str = "train",
    revision: str | None = None,
    limit: int | None = None,
) -> list[Record]:
    """Load a HuggingFace dataset into a list of plain dicts.

    Image fields (bytes dicts) and other non-serialisable types are preserved
    as-is — scanners that don't need them will simply ignore them.
    """
    try:
        from datasets import load_dataset  # type: ignore[import-untyped]
    except ImportError:
        raise ImportError(
            "The 'datasets' package is required to load HuggingFace datasets. "
            "Install it with: pip install datasets"
        )

    from datasets import Image as HFImage

    kwargs: dict[str, Any] = {"split": split}
    if revision:
        kwargs["revision"] = revision

    dataset = load_dataset(path, **kwargs)

    # Disable PIL decoding for image columns so they arrive as raw bytes dicts.
    # This avoids a Pillow dependency and keeps records JSON-serialisable.
    for col_name, feature in dataset.features.items():
        if isinstance(feature, HFImage):
            dataset = dataset.cast_column(col_name, HFImage(decode=False))

    if limit is not None:
        dataset = dataset.select(range(min(limit, len(dataset))))

    return [dict(row) for row in dataset]


def resolve_fields(
    records: list[Record],
    question_field: str | None,
    answer_field: str | None,
    id_field: str | None,
    image_field: str | None = None,
) -> FieldMap:
    """Return a FieldMap from explicit overrides or auto-detection."""
    if not records:
        raise ValueError("Dataset is empty")

    columns = list(records[0].keys())

    if question_field is not None and answer_field is not None:
        return FieldMap(
            question=question_field,
            answer=answer_field,
            id=id_field,
            image=image_field,
        )

    detected = auto_detect_fields(columns)

    # Allow partial overrides
    return FieldMap(
        question=question_field or detected.question,
        answer=answer_field or detected.answer,
        id=id_field if id_field is not None else detected.id,
        image=image_field,
    )
