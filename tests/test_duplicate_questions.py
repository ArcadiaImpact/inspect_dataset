from inspect_dataset._types import FieldMap
from inspect_dataset.scanners.duplicate_questions import duplicate_questions

FIELDS = FieldMap(question="q", answer="a")


def records(*questions: str) -> list[dict]:
    return [{"q": q, "a": f"answer {i}"} for i, q in enumerate(questions)]


def test_no_duplicates_no_findings():
    assert duplicate_questions(records("what is A?", "what is B?", "what is C?"), FIELDS) == []


def test_exact_duplicate_produces_two_findings():
    recs = records("what is A?", "what is B?", "what is A?")
    findings = duplicate_questions(recs, FIELDS)
    assert len(findings) == 2
    for f in findings:
        assert f.scanner == "duplicate_questions"
        assert f.severity == "high"
        assert f.category == "question_quality"
        assert f.metadata["duplicate_count"] == 2
        assert f.metadata["duplicate_indices"] == [0, 2]


def test_triplicate_produces_three_findings():
    recs = records("same question", "same question", "same question")
    findings = duplicate_questions(recs, FIELDS)
    assert len(findings) == 3
    assert all(f.metadata["duplicate_count"] == 3 for f in findings)


def test_case_insensitive_normalisation():
    recs = records("What Is A?", "what is a?")
    findings = duplicate_questions(recs, FIELDS)
    assert len(findings) == 2


def test_whitespace_normalisation():
    recs = records("  what is a?  ", "what is a?")
    findings = duplicate_questions(recs, FIELDS)
    assert len(findings) == 2


def test_multiple_duplicate_groups():
    recs = records("foo", "bar", "foo", "bar")
    findings = duplicate_questions(recs, FIELDS)
    assert len(findings) == 4


def test_finding_indices_are_correct():
    recs = records("unique", "dup", "other", "dup")
    findings = duplicate_questions(recs, FIELDS)
    assert len(findings) == 2
    assert all(f.metadata["duplicate_indices"] == [1, 3] for f in findings)
    assert {f.sample_index for f in findings} == {1, 3}


def test_sample_id_from_field():
    fields = FieldMap(question="q", answer="a", id="id")
    recs = [
        {"q": "same", "a": "ans1", "id": "id-0"},
        {"q": "same", "a": "ans2", "id": "id-1"},
    ]
    findings = duplicate_questions(recs, fields)
    assert {f.sample_id for f in findings} == {"id-0", "id-1"}
