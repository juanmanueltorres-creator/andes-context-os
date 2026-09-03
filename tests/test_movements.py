import pytest

from andes_context_os.movements import (
    ActorRole,
    Movement,
    MovementReviewState,
    MovementType,
)


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
