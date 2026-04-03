from __future__ import annotations

import importlib
from pathlib import Path
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


def _input_to_str(input: Any) -> str:
    """Extract question text from an inspect_ai Sample.input value.

    Handles both plain strings and list[ChatMessage] (Pydantic objects or dicts).
    For message lists, uses the content of the last user message.
    """
    if isinstance(input, str):
        return input
    if isinstance(input, list) and input:
        for msg in reversed(input):
            role = getattr(msg, "role", None) or (msg.get("role") if isinstance(msg, dict) else None)
            if role == "user":
                content = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else None)
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    # ContentBlock list — join text parts
                    return " ".join(
                        str(getattr(part, "text", "") or (part.get("text", "") if isinstance(part, dict) else ""))
                        for part in content
                        if (getattr(part, "type", None) or (part.get("type") if isinstance(part, dict) else None)) == "text"
                    )
        # Fallback: stringify first message content
        msg = input[0]
        content = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else None)
        return str(content) if content is not None else ""
    return str(input)


def _target_to_str(target: Any) -> str:
    """Extract answer text from an inspect_ai Sample.target value."""
    if isinstance(target, list):
        return target[0] if target else ""
    return str(target) if target is not None else ""


def load_inspect_task(task_or_fn: Any, limit: int | None = None) -> tuple[list[Record], FieldMap]:
    """Load records from an inspect_ai Task object or task function.

    Converts each ``inspect_ai.Sample`` to a plain ``Record`` dict using the
    fixed field mapping: ``input`` → question, ``target`` → answer, ``id`` → id.
    ``choices`` and ``metadata`` are preserved in the record for scanners that
    can use them. ``files`` is stored under ``__files__`` for future use by the
    view server.

    Returns a ``(records, fields)`` tuple — the ``FieldMap`` is pre-set so no
    auto-detection is needed.
    """
    task = task_or_fn() if callable(task_or_fn) else task_or_fn
    dataset = getattr(task, "dataset", None)
    if dataset is None:
        raise ValueError("Task has no dataset")

    records: list[Record] = []
    for sample in dataset:
        record: Record = {
            "input": _input_to_str(sample.input),
            "target": _target_to_str(sample.target),
            "id": sample.id,
        }
        if sample.choices:
            record["choices"] = sample.choices
        if sample.metadata:
            # Merge metadata into record so scanners can access it directly
            for k, v in sample.metadata.items():
                record.setdefault(k, v)
        if sample.files:
            record["__files__"] = sample.files
        records.append(record)
        if limit is not None and len(records) >= limit:
            break

    fields = FieldMap(question="input", answer="target", id="id")
    return records, fields


def load_task_from_spec(spec: str, limit: int | None = None) -> tuple[list[Record], FieldMap]:
    """Load records from a task spec string, using the inspect_ai registry.

    Accepts the same spec formats as ``inspect eval``:

    - Registry name (bare):        ``inspect_evals/medqa``
    - File + task name:            ``path/to/task.py@task_fn``
    - Module + task name:          ``inspect_evals.medqa@medqa``

    For registry names and ``file@task`` specs, this delegates to
    ``inspect_ai.load_task_spec`` so the full entry-points and registry
    machinery is used identically to the ``inspect`` CLI.

    For ``module@attr`` specs where the left side looks like a Python module
    path (contains ``.`` but is not a file path), the attribute is imported
    directly without going through the registry.

    Raises ``ImportError`` if ``inspect_ai`` is not installed.
    """
    try:
        from inspect_ai._eval.loader import load_task_spec as _inspect_load_task_spec
    except ImportError:
        raise ImportError(
            "inspect_ai is required to load tasks by spec. "
            "Install it with: pip install inspect-ai"
        )

    has_at = "@" in spec

    if has_at:
        left, right = spec.rsplit("@", 1)
        left_path = Path(left)
        # If the left side is a dotted module path (not a file), import directly
        # so callers don't need the task to be @task-decorated / registered.
        if "." in left and not left_path.exists():
            try:
                module = importlib.import_module(left)
            except ImportError as e:
                raise ImportError(f"Could not import module {left!r}: {e}") from e
            if not hasattr(module, right):
                raise AttributeError(f"Module {left!r} has no attribute {right!r}")
            task_obj = getattr(module, right)
            return load_inspect_task(task_obj, limit=limit)

    # Fall through: let inspect_ai's loader handle it (registry name, file@task, etc.)
    tasks = _inspect_load_task_spec(spec)
    if not tasks:
        raise ValueError(f"No tasks found for spec {spec!r}")
    if len(tasks) > 1:
        raise ValueError(
            f"Spec {spec!r} matched {len(tasks)} tasks; use a more specific spec "
            f"(e.g. include the task name after @)."
        )
    return load_inspect_task(tasks[0], limit=limit)


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
