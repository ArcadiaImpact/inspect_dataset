from inspect_dataset._types import FieldMap
from inspect_dataset.scanners.duplicate_questions import duplicate_questions

FIELDS = FieldMap(question="q", answer="a")


def recs(*pairs: tuple[str, str]) -> list[dict]:
    """Build records from (question, answer) pairs."""
    return [{"q": q, "a": a} for q, a in pairs]


def test_no_duplicates_no_findings():
    data = recs(("what is A?", "yes"), ("what is B?", "no"), ("what is C?", "yes"))
    assert duplicate_questions(data, FIELDS) == []


# ---------------------------------------------------------------------------
# Same answer → HIGH (real duplicate)
# ---------------------------------------------------------------------------

def test_same_answer_duplicate_is_high():
    data = recs(("is it broken?", "no"), ("other q", "yes"), ("is it broken?", "no"))
    findings = duplicate_questions(data, FIELDS)
    assert len(findings) == 2
    for f in findings:
        assert f.severity == "high"
        assert f.metadata["answers_agree"] is True
        assert f.metadata["duplicate_indices"] == [0, 2]


def test_same_answer_triplicate_is_high():
    data = recs(("same?", "yes"), ("same?", "yes"), ("same?", "yes"))
    findings = duplicate_questions(data, FIELDS)
    assert len(findings) == 3
    assert all(f.severity == "high" for f in findings)
    assert all(f.metadata["duplicate_count"] == 3 for f in findings)


# ---------------------------------------------------------------------------
# Different answers → LOW (valid multimodal pattern)
# ---------------------------------------------------------------------------

def test_different_answer_duplicate_is_low():
    data = recs(("is the heart enlarged?", "yes"), ("other", "no"), ("is the heart enlarged?", "no"))
    findings = duplicate_questions(data, FIELDS)
    assert len(findings) == 2
    for f in findings:
        assert f.severity == "low"
        assert f.metadata["answers_agree"] is False


def test_mixed_groups_correct_severity():
    # "foo" appears twice with same answer → HIGH
    # "bar" appears twice with different answers → LOW
    data = recs(("foo", "yes"), ("bar", "a"), ("foo", "yes"), ("bar", "b"))
    findings = duplicate_questions(data, FIELDS)
    foo_findings = [f for f in findings if f.metadata["question"] == "foo"]
    bar_findings = [f for f in findings if f.metadata["question"] == "bar"]
    assert all(f.severity == "high" for f in foo_findings)
    assert all(f.severity == "low" for f in bar_findings)


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def test_case_insensitive_normalisation():
    data = recs(("What Is A?", "yes"), ("what is a?", "yes"))
    findings = duplicate_questions(data, FIELDS)
    assert len(findings) == 2


def test_whitespace_normalisation():
    data = recs(("  what is a?  ", "yes"), ("what is a?", "yes"))
    findings = duplicate_questions(data, FIELDS)
    assert len(findings) == 2


# ---------------------------------------------------------------------------
# Indices and IDs
# ---------------------------------------------------------------------------

def test_finding_indices_are_correct():
    data = recs(("unique", "x"), ("dup", "y"), ("other", "z"), ("dup", "y"))
    findings = duplicate_questions(data, FIELDS)
    assert len(findings) == 2
    assert all(f.metadata["duplicate_indices"] == [1, 3] for f in findings)
    assert {f.sample_index for f in findings} == {1, 3}


def test_sample_id_from_field():
    fields = FieldMap(question="q", answer="a", id="id")
    data = [
        {"q": "same", "a": "yes", "id": "id-0"},
        {"q": "same", "a": "yes", "id": "id-1"},
    ]
    findings = duplicate_questions(data, fields)
    assert {f.sample_id for f in findings} == {"id-0", "id-1"}


# ---------------------------------------------------------------------------
# Image field metadata
# ---------------------------------------------------------------------------

def test_image_field_agree_metadata():
    fields = FieldMap(question="q", answer="a", image="img")
    img_bytes = b"\x89PNG\r\n"
    data = [
        {"q": "what is shown?", "a": "yes", "img": {"bytes": img_bytes, "path": None}},
        {"q": "what is shown?", "a": "yes", "img": {"bytes": img_bytes, "path": None}},
    ]
    findings = duplicate_questions(data, fields)
    assert findings[0].metadata["images_agree"] is True


def test_image_field_disagree_metadata():
    fields = FieldMap(question="q", answer="a", image="img")
    data = [
        {"q": "what is shown?", "a": "yes", "img": {"bytes": b"img1", "path": None}},
        {"q": "what is shown?", "a": "no",  "img": {"bytes": b"img2", "path": None}},
    ]
    findings = duplicate_questions(data, fields)
    assert findings[0].metadata["images_agree"] is False


def test_no_image_field_no_images_agree_key():
    data = recs(("same?", "yes"), ("same?", "yes"))
    findings = duplicate_questions(data, FIELDS)
    assert "images_agree" not in findings[0].metadata
