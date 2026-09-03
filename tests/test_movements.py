import pytest

from andes_context_os.movements import (
    ActorRole,
    Movement,
    MovementReviewState,
    MovementType,
)
from andes_context_os.opportunities import OpportunityHypothesis, OpportunityStatus


def movement_payload(**overrides):
    payload = {
        "contract_version": "0.1",
        "movement_id": "movement:rg:drilling:2026-05-21",
        "asset_id": "asset:ar:li:rio-grande-noa",
        "movement_type": "drilling",
        "observed_at": "2026-09-02T22:00:00-03:00",
        "actor_refs": [
            {"actor_id": "actor:noa-lithium", "role": "operator", "notes": []},
            {"actor_id": "actor:hidrotec", "role": "contractor", "notes": []},
        ],
        "evidence_candidate_refs": ["evidence:rg:noa:2026-05-21"],
        "factual_summary": "NOA reported completion of drilling-rig mobilization by Hidrotec for the 2026 Rio Grande campaign.",
        "previous_state": None,
        "new_state": None,
        "review_state": "reviewed",
        "reviewed_at": "2026-09-02T22:05:00-03:00",
        "derived_from_movement_ids": [],
        "limitations": ["Company disclosure; no inference about unannounced procurement."],
    }
    payload.update(overrides)
    return payload


def hypothesis_payload(**overrides):
    payload = {
        "contract_version": "0.1",
        "hypothesis_id": "opportunity:rg:external-field-services",
        "asset_id": "asset:ar:li:rio-grande-noa",
        "trigger_movement_refs": ["movement:rg:drilling:2026-05-21"],
        "actor_refs": ["actor:noa-lithium"],
        "need_category": "field_services",
        "statement": "Continued PFS work may create additional demand for externally procured field services.",
        "supporting_evidence_refs": [],
        "assumptions": ["At least part of future field work is procured externally."],
        "missing_context": ["Current supplier roster and procurement model."],
        "status": "proposed",
        "created_at": "2026-09-02T22:10:00-03:00",
        "reviewed_at": None,
    }
    payload.update(overrides)
    return payload


def test_movement_round_trip_preserves_evidence_links_and_roles():
    movement = Movement.from_dict(movement_payload())
    assert movement.movement_type == MovementType.DRILLING
    assert movement.review_state == MovementReviewState.REVIEWED
    assert movement.actor_refs[1].role == ActorRole.CONTRACTOR
    assert movement.to_dict() == movement_payload()


def test_movement_requires_evidence_reference():
    with pytest.raises(ValueError, match="evidence_candidate_refs must not be empty"):
        Movement.from_dict(movement_payload(evidence_candidate_refs=[]))


def test_movement_rejects_duplicate_actor_role_pairs():
    actor = {"actor_id": "actor:noa-lithium", "role": "operator", "notes": []}
    with pytest.raises(ValueError, match="duplicate actor-role reference"):
        Movement.from_dict(movement_payload(actor_refs=[actor, actor]))


def test_stage_change_requires_distinct_previous_and_new_state():
    with pytest.raises(ValueError, match="stage_change requires distinct previous_state and new_state"):
        Movement.from_dict(movement_payload(
            movement_type="stage_change",
            previous_state="construction",
            new_state="construction",
        ))


def test_reviewed_movement_requires_reviewed_at():
    with pytest.raises(ValueError, match="reviewed_at is required"):
        Movement.from_dict(movement_payload(reviewed_at=None))


def test_unreviewed_movement_rejects_reviewed_at():
    with pytest.raises(ValueError, match="reviewed_at must be null"):
        Movement.from_dict(movement_payload(review_state="unreviewed"))


def test_movement_rejects_self_lineage():
    with pytest.raises(ValueError, match="cannot derive from itself"):
        Movement.from_dict(movement_payload(derived_from_movement_ids=["movement:rg:drilling:2026-05-21"]))


def test_proposed_hypothesis_round_trip_preserves_uncertainty():
    item = OpportunityHypothesis.from_dict(hypothesis_payload())
    assert item.status == OpportunityStatus.PROPOSED
    assert item.assumptions == ("At least part of future field work is procured externally.",)
    assert item.missing_context == ("Current supplier roster and procurement model.",)
    assert item.to_dict() == hypothesis_payload()


def test_hypothesis_requires_trigger_movement():
    with pytest.raises(ValueError, match="trigger_movement_refs must not be empty"):
        OpportunityHypothesis.from_dict(hypothesis_payload(trigger_movement_refs=[]))


def test_hypothesis_rejects_duplicate_actor_refs():
    with pytest.raises(ValueError, match="actor_refs contains duplicates"):
        OpportunityHypothesis.from_dict(hypothesis_payload(actor_refs=["actor:noa-lithium", "actor:noa-lithium"]))


def test_supported_hypothesis_requires_supporting_evidence_and_reviewed_at_locally():
    with pytest.raises(ValueError, match="supported requires supporting_evidence_refs"):
        OpportunityHypothesis.from_dict(hypothesis_payload(status="supported", reviewed_at="2026-09-02T22:15:00-03:00"))
    with pytest.raises(ValueError, match="reviewed_at is required"):
        OpportunityHypothesis.from_dict(hypothesis_payload(status="supported", supporting_evidence_refs=["evidence:extra"]))


def test_proposed_hypothesis_rejects_reviewed_at():
    with pytest.raises(ValueError, match="reviewed_at must be null"):
        OpportunityHypothesis.from_dict(hypothesis_payload(reviewed_at="2026-09-02T22:15:00-03:00"))


def test_proposed_hypothesis_allows_reviewed_at_field_to_be_omitted():
    payload = hypothesis_payload()
    payload.pop("reviewed_at")
    item = OpportunityHypothesis.from_dict(payload)
    assert item.reviewed_at is None
    assert item.to_dict()["reviewed_at"] is None
