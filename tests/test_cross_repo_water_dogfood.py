import json
from pathlib import Path

from andes_context_os.handoff_intake import preview_research_intent
from andes_context_os.handoffs import QuestionResearchHandoff
from andes_context_os.opportunity_handoff import ResearchOpportunityHandoff
from andes_context_os.research import (
    ResearchActivity,
    ResearchDomain,
    TerritorialScope,
)


FIXTURES = Path(__file__).parent / "fixtures" / "handoffs"
QUESTION_FIXTURE = FIXTURES / "question_research_water_san_juan_v01.json"
OPPORTUNITY_FIXTURE = FIXTURES / "research_opportunity_water_san_juan_v01.json"

EXPECTED_QUESTION = (
    "¿Qué decisión recurrente relacionada con agua en San Juan podría mejorar utilizando "
    "evidencia territorial o satelital, quién toma hoy esa decisión y qué información le falta?"
)
EXPLICIT_GOAL = (
    "Identificar una decisión hídrica recurrente en San Juan y documentar qué evidencia "
    "territorial faltaría para evaluarla sin inferir demanda ni comprador."
)


def load_question_handoff() -> QuestionResearchHandoff:
    payload = json.loads(QUESTION_FIXTURE.read_text(encoding="utf-8"))
    return QuestionResearchHandoff.from_dict(payload)


def load_opportunity_handoff() -> ResearchOpportunityHandoff:
    payload = json.loads(OPPORTUNITY_FIXTURE.read_text(encoding="utf-8"))
    return ResearchOpportunityHandoff.from_dict(payload)


def test_upstream_question_is_preserved_verbatim():
    handoff = load_question_handoff()
    assert handoff.question.raw == EXPECTED_QUESTION
    assert handoff.question.canonical == EXPECTED_QUESTION


def test_water_and_decision_support_are_explicit_operator_inputs():
    preview = preview_research_intent(
        load_question_handoff(),
        domain=ResearchDomain.WATER,
        activity=ResearchActivity.DECISION_SUPPORT,
        goal=EXPLICIT_GOAL,
        territory_hint="San Juan, Argentina",
    )
    assert preview.domain is ResearchDomain.WATER
    assert preview.activity is ResearchActivity.DECISION_SUPPORT
    assert preview.goal == EXPLICIT_GOAL
    assert preview.territorial_scope_required is True


def test_territorial_scope_remains_a_separate_explicit_requirement():
    preview = preview_research_intent(
        load_question_handoff(),
        domain=ResearchDomain.WATER,
        activity=ResearchActivity.DECISION_SUPPORT,
        goal=EXPLICIT_GOAL,
        territory_hint="San Juan, Argentina",
    )
    assert preview.territorial_scope_required is True
    assert not hasattr(preview, "territorial_scope")

    scope = TerritorialScope.from_dict(
        {
            "contract_version": "0.1",
            "scope_id": "scope:water-san-juan:001",
            "countries": ["AR"],
            "admin_units": [
                {
                    "country_code": "AR",
                    "admin_level": "1",
                    "official_code": "J",
                    "name": "San Juan",
                    "source_id": "ar_ign_admin",
                }
            ],
            "project_refs": [],
            "corridor_refs": [],
            "segment_refs": [],
            "bbox": None,
            "geometry_ref": None,
            "crs": None,
            "precision": "admin_unit",
            "relation_basis": "official_geometry",
            "notes": ["Explicit dogfood scope; not inferred from question text."],
        }
    )
    assert scope.admin_units[0].name == "San Juan"


def test_research_output_can_remain_non_actionable_without_inventing_actor_or_evidence():
    handoff = load_opportunity_handoff()
    assert handoff.candidate.kind == "ACTOR_NEED_HYPOTHESIS"
    assert handoff.candidate.research_status == "researching"
    assert handoff.candidate.actor_refs == ()
    assert handoff.candidate.evidence_refs == ()
    assert handoff.candidate.assumptions == (
        "A recurring water-management decision exists within the selected territorial scope.",
        "Territorial or satellite evidence could materially change that decision.",
    )
    assert handoff.candidate.missing_context == (
        "Decision owner or materially involved actor",
        "Current decision cadence and workflow",
        "Evidence currently used",
        "Evidence assembly cost or delay",
        "Procurement or collaboration path",
    )


def test_research_output_keeps_cross_repo_lineage_without_promoting_authority():
    question = load_question_handoff()
    opportunity = load_opportunity_handoff()
    assert opportunity.source.source_question_ref == question.source.question_id
    assert opportunity.source.research_intent_ref == "intent:water-san-juan:001"
    assert opportunity.source.hypothesis_ref == "hypothesis:water-san-juan:001"

    candidate = opportunity.to_dict()["candidate"]
    forbidden = {
        "buyer",
        "customer",
        "problem_owner",
        "procurement_package",
        "procurement_intent",
        "contact_permission",
        "outreach_permission",
        "willingness_to_pay",
    }
    assert forbidden.isdisjoint(candidate)
