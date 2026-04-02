from inspect_dataset._types import FieldMap
from inspect_dataset.scanners.binary_question_ratio import binary_question_ratio

FIELDS = FieldMap(question="q", answer="a")


def records(*answers: str) -> list[dict]:
    return [{"q": f"question {i}", "a": a} for i, a in enumerate(answers)]


def test_all_open_answers_no_finding():
    recs = records("axial", "brain", "right upper lobe", "mri", "female")
    assert binary_question_ratio(recs, FIELDS) == []


def test_exactly_half_binary_no_finding():
    # 50% yes/no — at threshold, not above
    recs = records(*["yes"] * 5, *["axial"] * 5)
    assert binary_question_ratio(recs, FIELDS) == []


def test_above_threshold_flagged():
    # 60% yes/no
    recs = records(*["yes"] * 6, *["axial"] * 4)
    findings = binary_question_ratio(recs, FIELDS)
    assert len(findings) == 1
    f = findings[0]
    assert f.scanner == "binary_question_ratio"
    assert f.severity == "low"
    assert f.category == "distribution"
    assert f.sample_index == -1
    assert f.sample_id is None


def test_all_yes_no_flagged():
    recs = records(*["yes"] * 5, *["no"] * 5)
    findings = binary_question_ratio(recs, FIELDS)
    assert len(findings) == 1
    assert findings[0].metadata["binary_count"] == 10
    assert findings[0].metadata["fraction"] == 1.0


def test_metadata_counts():
    recs = records(*["yes"] * 7, *["no"] * 3)
    findings = binary_question_ratio(recs, FIELDS)
    m = findings[0].metadata
    assert m["yes_count"] == 7
    assert m["no_count"] == 3
    assert m["binary_count"] == 10


def test_naive_majority_score_correct():
    # 7 yes, 3 no → majority is yes → naive score = 7/10
    recs = records(*["yes"] * 7, *["no"] * 3)
    findings = binary_question_ratio(recs, FIELDS)
    assert findings[0].metadata["naive_majority_score"] == 0.7


def test_empty_answers_excluded():
    # 6 yes/no + 4 empty → 6/6 = 100% binary (empty excluded)
    recs = records(*["yes"] * 6, *[""] * 4)
    findings = binary_question_ratio(recs, FIELDS)
    assert len(findings) == 1
    assert findings[0].metadata["total"] == 6


def test_all_empty_no_finding():
    assert binary_question_ratio(records("", ""), FIELDS) == []
