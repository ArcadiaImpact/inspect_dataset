from __future__ import annotations

from inspect_dataset._types import FieldMap, Finding, Record
from inspect_dataset.scanner import ScannerDef, get_sample_id

DEFAULT_MAX_WORDS = 4


def _make_scanner(max_words: int = DEFAULT_MAX_WORDS) -> ScannerDef:
    def _scan(records: list[Record], fields: FieldMap) -> list[Finding]:
        findings = []
        for i, record in enumerate(records):
            answer = str(record.get(fields.answer, "") or "").strip()
            word_count = len(answer.split())
            if word_count > max_words:
                findings.append(
                    Finding(
                        scanner="answer_length",
                        severity="medium",
                        category="label_quality",
                        explanation=(
                            f"Answer has {word_count} words (threshold: {max_words}). "
                            f"Long answers are unlikely to be reproduced verbatim by "
                            f"exact-match scorers. Answer: {answer!r}"
                        ),
                        sample_index=i,
                        sample_id=get_sample_id(record, fields, i),
                        metadata={"word_count": word_count, "answer": answer},
                    )
                )
        return findings

    return ScannerDef(
        name="answer_length",
        fn=_scan,
        description=(
            f"Flag answers longer than {max_words} words. "
            "Long answers are a weak proxy for exact-match scoring."
        ),
    )


answer_length = _make_scanner()
