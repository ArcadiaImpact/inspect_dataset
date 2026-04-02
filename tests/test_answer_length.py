from inspect_dataset._types import FieldMap
from inspect_dataset.scanners.answer_length import _make_scanner, answer_length

FIELDS = FieldMap(question="q", answer="a")


def records(*answers: str) -> list[dict]:
    return [{"q": f"question {i}", "a": a} for i, a in enumerate(answers)]


def test_short_answer_no_finding():
    assert answer_length(records("yes", "no", "blue"), FIELDS) == []


def test_answer_at_threshold_no_finding():
    # Default threshold is 4; exactly 4 words should not be flagged
    assert answer_length(records("one two three four"), FIELDS) == []


def test_long_answer_flagged():
    findings = answer_length(records("one two three four five"), FIELDS)
    assert len(findings) == 1
    f = findings[0]
    assert f.scanner == "answer_length"
    assert f.severity == "medium"
    assert f.category == "label_quality"
    assert f.sample_index == 0
    assert f.metadata["word_count"] == 5


def test_only_long_answers_flagged():
    findings = answer_length(records("yes", "one two three four five", "no"), FIELDS)
    assert len(findings) == 1
    assert findings[0].sample_index == 1


def test_custom_threshold():
    scanner = _make_scanner(max_words=2)
    findings = scanner(records("one two three"), FIELDS)
    assert len(findings) == 1
    assert findings[0].metadata["word_count"] == 3


def test_custom_threshold_short_no_finding():
    scanner = _make_scanner(max_words=2)
    assert scanner(records("one two"), FIELDS) == []


def test_empty_answer_skipped():
    assert answer_length(records(""), FIELDS) == []


def test_sample_id_from_field():
    fields = FieldMap(question="q", answer="a", id="id")
    recs = [{"q": "question", "a": "one two three four five", "id": "sample-42"}]
    findings = answer_length(recs, fields)
    assert findings[0].sample_id == "sample-42"


def test_sample_id_defaults_to_index():
    findings = answer_length(records("one two three four five"), FIELDS)
    assert findings[0].sample_id == 0
