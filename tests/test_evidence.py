import pytest

from andes_context_os.evidence import EvidenceCandidate, EvidenceQualityVector

VALID_QUALITY = {
    "contract_version": "0.1",
    "authority": "community_source",
    "source_verification": "source_located",
    "freshness": "dated",
    "spatial_precision": "contextual",
    "temporal_precision": "day",
    "coverage": "context_only",
    "completeness": "partial",
    "corroboration": "none",
    "method_transparency": "not_applicable",
    "rights_clarity": "unknown",
    "review_state": "unreviewed",
    "limitations": ["Public human signal; not operational ground truth"],
    "missing_context": ["official road condition", "observed segment speed"],
}

VALID_CANDIDATE = {
    "candidate_id": "candidate-001",
    "source_id": "reddit_public",
    "source_runtime_observation_id": "obs-reddit-001",
    "kind": "public_human_signal",
    "title": "Long high-altitude access travel reported",
    "factual_summary": "A public post reports long travel time to a high-altitude mining project.",
    "source_reference": "https://www.reddit.com/example",
    "temporal_context": {"published_at": "2026-04-18T12:00:00-03:00"},
    "territorial_relation": {"scope_id": "scope-ar-j", "relation": "contextual"},
    "quality": VALID_QUALITY,
    "payload_ref": None,
    "corroboration_refs": [],
    "derived_from_ids": [],
    "candidate_state": "needs_review",
}


def test_quality_vector_round_trips():
    assert EvidenceQualityVector.from_dict(VALID_QUALITY).to_dict() == VALID_QUALITY


def test_quality_vector_rejects_confidence_score():
    with pytest.raises(ValueError, match="unknown fields: confidence_score"):
        EvidenceQualityVector.from_dict({**VALID_QUALITY, "confidence_score": 0.9})


def test_quality_vector_rejects_risk_score():
    with pytest.raises(ValueError, match="unknown fields: risk_score"):
        EvidenceQualityVector.from_dict({**VALID_QUALITY, "risk_score": 10})


def test_quality_vector_rejects_truth_score():
    with pytest.raises(ValueError, match="unknown fields: truth_score"):
        EvidenceQualityVector.from_dict({**VALID_QUALITY, "truth_score": 1})


def test_quality_vector_accepts_explicit_unknown_states():
    payload = {
        **VALID_QUALITY,
        "authority": "unknown",
        "freshness": "unknown",
        "spatial_precision": "unknown",
        "temporal_precision": "unknown",
        "coverage": "unknown",
        "corroboration": "unknown",
        "method_transparency": "unknown",
        "rights_clarity": "unknown",
    }
    quality = EvidenceQualityVector.from_dict(payload)
    assert quality.freshness.value == "unknown"
    assert quality.rights_clarity.value == "unknown"


def test_source_verified_is_distinct_from_technically_reviewed():
    source_verified = EvidenceQualityVector.from_dict({**VALID_QUALITY, "review_state": "source_verified"})
    technical = EvidenceQualityVector.from_dict({**VALID_QUALITY, "review_state": "technically_reviewed"})
    assert source_verified.review_state != technical.review_state


def test_quality_vector_rejects_unknown_enum_value():
    with pytest.raises(ValueError, match="freshness"):
        EvidenceQualityVector.from_dict({**VALID_QUALITY, "freshness": "probably_current"})


def test_candidate_round_trips():
    assert EvidenceCandidate.from_dict(VALID_CANDIDATE).to_dict() == VALID_CANDIDATE


def test_multiple_independent_sources_requires_two_refs():
    payload = {
        **VALID_CANDIDATE,
        "quality": {**VALID_QUALITY, "corroboration": "multiple_independent_sources"},
        "corroboration_refs": ["source-a"],
    }
    with pytest.raises(ValueError, match="at least two distinct corroboration_refs"):
        EvidenceCandidate.from_dict(payload)


def test_multiple_independent_sources_rejects_duplicate_refs():
    payload = {
        **VALID_CANDIDATE,
        "quality": {**VALID_QUALITY, "corroboration": "multiple_independent_sources"},
        "corroboration_refs": ["source-a", "source-a"],
    }
    with pytest.raises(ValueError, match="at least two distinct corroboration_refs"):
        EvidenceCandidate.from_dict(payload)


def test_multiple_independent_sources_accepts_two_distinct_refs():
    payload = {
        **VALID_CANDIDATE,
        "quality": {**VALID_QUALITY, "corroboration": "multiple_independent_sources"},
        "corroboration_refs": ["source-a", "source-b"],
    }
    candidate = EvidenceCandidate.from_dict(payload)
    assert candidate.corroboration_refs == ("source-a", "source-b")


@pytest.mark.parametrize("field", ["safe_to_travel", "road_open", "route_authorized", "community_approved"])
def test_candidate_rejects_operational_authorization_fields(field):
    with pytest.raises(ValueError, match=f"unknown fields: {field}"):
        EvidenceCandidate.from_dict({**VALID_CANDIDATE, field: True})


def test_candidate_rejects_unknown_kind():
    with pytest.raises(ValueError, match="kind"):
        EvidenceCandidate.from_dict({**VALID_CANDIDATE, "kind": "oracle"})


def test_candidate_rejects_unknown_state():
    with pytest.raises(ValueError, match="candidate_state"):
        EvidenceCandidate.from_dict({**VALID_CANDIDATE, "candidate_state": "proven"})


def test_temporal_context_rejects_naive_timestamp():
    payload = {**VALID_CANDIDATE, "temporal_context": {"published_at": "2026-04-18T12:00:00"}}
    with pytest.raises(ValueError, match="timezone-aware"):
        EvidenceCandidate.from_dict(payload)


def test_temporal_context_rejects_unknown_field():
    payload = {**VALID_CANDIDATE, "temporal_context": {"published_at": "2026-04-18T12:00:00-03:00", "fresh": True}}
    with pytest.raises(ValueError, match="unknown fields: fresh"):
        EvidenceCandidate.from_dict(payload)


def test_territorial_relation_requires_scope_id():
    payload = {**VALID_CANDIDATE, "territorial_relation": {"relation": "contextual"}}
    with pytest.raises(ValueError, match="missing required fields: scope_id"):
        EvidenceCandidate.from_dict(payload)


def test_candidate_is_immutable():
    candidate = EvidenceCandidate.from_dict(VALID_CANDIDATE)
    with pytest.raises(AttributeError):
        candidate.title = "changed"
