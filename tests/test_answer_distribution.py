from inspect_dataset._types import FieldMap
from inspect_dataset.scanners.answer_distribution import answer_distribution

FIELDS = FieldMap(question="q", answer="a")


def records(*answers: str) -> list[dict]:
    return [{"q": f"question {i}", "a": a} for i, a in enumerate(answers)]


def test_balanced_dataset_no_finding():
    recs = records(*["yes"] * 5, *["no"] * 5)
    assert answer_distribution(recs, FIELDS) == []


def test_imbalanced_above_threshold_flagged():
    # 85% "yes" → exactly at threshold → flagged
    recs = records(*["yes"] * 85, *["no"] * 15)
    findings = answer_distribution(recs, FIELDS)
    assert len(findings) == 1
    f = findings[0]
    assert f.scanner == "answer_distribution"
    assert f.severity == "high"
    assert f.category == "distribution"
    assert f.sample_index == -1
    assert f.sample_id is None
    assert f.metadata["most_common_answer"] == "yes"
    assert f.metadata["most_common_count"] == 85
    assert f.metadata["total"] == 100


def test_imbalanced_just_below_threshold_no_finding():
    # 84% "yes" → below threshold
    recs = records(*["yes"] * 84, *["no"] * 16)
    assert answer_distribution(recs, FIELDS) == []


def test_all_same_answer_flagged():
    recs = records(*["yes"] * 10)
    findings = answer_distribution(recs, FIELDS)
    assert len(findings) == 1
    assert findings[0].metadata["fraction"] == 1.0


def test_case_insensitive_counting():
    # "Yes" and "yes" should be counted together
    recs = records(*["Yes"] * 45, *["yes"] * 45, *["no"] * 10)
    findings = answer_distribution(recs, FIELDS)
    assert len(findings) == 1
    assert findings[0].metadata["most_common_answer"] == "yes"
    assert findings[0].metadata["most_common_count"] == 90


def test_empty_answers_excluded():
    # 9 "yes" + 1 empty: fraction = 9/9 = 1.0 (empty excluded from total)
    recs = records(*["yes"] * 9, "")
    findings = answer_distribution(recs, FIELDS)
    assert len(findings) == 1
    assert findings[0].metadata["total"] == 9


def test_all_empty_no_finding():
    assert answer_distribution(records("", ""), FIELDS) == []


def test_single_finding_at_dataset_level():
    recs = records(*["yes"] * 9, "no")
    findings = answer_distribution(recs, FIELDS)
    assert len(findings) == 1
    assert findings[0].sample_index == -1
