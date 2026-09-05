import json

from andes_context_os.opportunities import OpportunityHypothesis
from andes_context_os.opportunity_handoff import (
    ACTOR_NEED_KIND,
    RESEARCH_OPPORTUNITY_CONTRACT,
    ResearchOpportunityHandoff,
    build_actor_need_handoff,
    render_research_opportunity_handoff_json,
)


BASE_HYPOTHESIS = {
    "contract_version": "0.1",
    "hypothesis_id": "hypothesis:water-sj:001",
    "asset_id": "asset:san-juan-water-context",
    "trigger_movement_refs": ["movement:public-water-signal:001"],
    "actor_refs": ["actor:public-example:001"],
    "need_category": "water_decision_support",
    "statement": "A recurrent water-management workflow may benefit from consolidated territorial evidence.",
    "supporting_evidence_refs": ["evidence:001", "evidence:002"],
    "assumptions": [
        "The referenced actor owns or materially influences the decision.",
        "The current workflow requires evidence assembly from multiple sources.",
    ],
    "missing_context": [
        "Current workflow owner",
        "Current evidence assembly cost",
        "Procurement or collaboration path",
    ],
    "status": "researching",
    "created_at": "2026-09-05T01:00:00-03:00",
    "reviewed_at": None,
}


def build(payload: dict | None = None) -> ResearchOpportunityHandoff:
    hypothesis = OpportunityHypothesis.from_dict(payload or BASE_HYPOTHESIS)
    return build_actor_need_handoff(
        hypothesis,
        source_question_ref="question:fixture:water-san-juan:001",
        research_intent_ref="intent:water-san-juan:001",
        handoff_id="roh:fixture:water-san-juan:001",
        created_at="2026-09-05T01:10:00-03:00",
    )


def test_researching_remains_researching():
    handoff = build()
    assert handoff.contract == RESEARCH_OPPORTUNITY_CONTRACT
    assert handoff.candidate.kind == ACTOR_NEED_KIND
    assert handoff.candidate.research_status == "researching"


def test_supported_remains_supported():
    payload = {
        **BASE_HYPOTHESIS,
        "status": "supported",
        "reviewed_at": "2026-09-05T01:05:00-03:00",
    }
    assert build(payload).candidate.research_status == "supported"


def test_contradicted_remains_contradicted():
    payload = {
        **BASE_HYPOTHESIS,
        "status": "contradicted",
        "reviewed_at": "2026-09-05T01:05:00-03:00",
    }
    assert build(payload).candidate.research_status == "contradicted"


def test_empty_actor_refs_remain_valid_and_empty():
    payload = {**BASE_HYPOTHESIS, "actor_refs": []}
    handoff = build(payload)
    assert handoff.candidate.actor_refs == ()
    assert handoff.to_dict()["candidate"]["actor_refs"] == []


def test_assumptions_and_missing_context_preserve_order():
    handoff = build()
    assert handoff.candidate.assumptions == tuple(BASE_HYPOTHESIS["assumptions"])
    assert handoff.candidate.missing_context == tuple(BASE_HYPOTHESIS["missing_context"])


def test_supporting_evidence_refs_are_not_expanded_or_guessed():
    handoff = build()
    assert handoff.candidate.evidence_refs == ("evidence:001", "evidence:002")
    payload = handoff.to_dict()
    assert payload["candidate"]["evidence_refs"] == ["evidence:001", "evidence:002"]
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "movement:public-water-signal:001" not in serialized


def test_source_preserves_question_intent_and_hypothesis_refs():
    handoff = build()
    assert handoff.source.system == "andes-context-os"
    assert handoff.source.source_question_ref == "question:fixture:water-san-juan:001"
    assert handoff.source.research_intent_ref == "intent:water-san-juan:001"
    assert handoff.source.hypothesis_ref == "hypothesis:water-sj:001"


def test_candidate_has_no_action_authority_fields():
    candidate = build().to_dict()["candidate"]
    forbidden = {
        "buyer",
        "customer",
        "procurement_intent",
        "hiring_intent",
        "contact_permission",
        "willingness_to_pay",
        "outreach_permission",
    }
    assert forbidden.isdisjoint(candidate)


def test_contract_round_trips_through_strict_model():
    payload = build().to_dict()
    assert ResearchOpportunityHandoff.from_dict(payload).to_dict() == payload


def test_export_is_byte_deterministic_for_same_inputs():
    first = render_research_opportunity_handoff_json(build())
    second = render_research_opportunity_handoff_json(build())
    assert first == second
    assert first.endswith("\n")
    assert json.loads(first) == build().to_dict()
