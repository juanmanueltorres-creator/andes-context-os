from copy import deepcopy

import pytest

from andes_context_os.handoff_intake import (
    build_research_intent,
    preview_research_intent,
)
from andes_context_os.handoffs import QuestionResearchHandoff
from andes_context_os.research import ResearchActivity, ResearchDomain


VALID_HANDOFF = {
    "contract": "question-research-handoff/v0.1",
    "handoff_id": "qrh:fixture:water-san-juan:001",
    "created_at": "2026-09-04T21:00:00-03:00",
    "source": {
        "system": "question-radar",
        "question_id": "question:fixture:water-san-juan:001",
        "question_profile_ref": None,
        "decision_id": "decision:fixture:water-san-juan:001",
        "decision_fingerprint": "sha256:" + "1" * 64,
    },
    "question": {
        "raw": "¿Qué decisión recurrente relacionada con agua en San Juan podría mejorar utilizando evidencia territorial o satelital, quién toma hoy esa decisión y qué información le falta?",
        "canonical": "¿Qué decisión recurrente relacionada con agua en San Juan podría mejorar utilizando evidencia territorial o satelital, quién toma hoy esa decisión y qué información le falta?",
    },
    "investigation": {
        "decision": "RESEARCH",
        "rationale": "La pregunta justifica una investigación acotada; el handoff no confirma actor, demanda ni oportunidad.",
        "next_test": "Definir un territorio explícito de San Juan y localizar una fuente pública trazable.",
    },
    "routing": {
        "kind": "TERRITORIAL_RESEARCH",
        "destination": "andes-context-os",
    },
    "constraints": [
        "route != opportunity",
        "handoff != evidence",
        "current_at_export != current_now",
    ],
}


def handoff() -> QuestionResearchHandoff:
    return QuestionResearchHandoff.from_dict(deepcopy(VALID_HANDOFF))


def test_preview_preserves_upstream_context_and_explicit_semantics():
    preview = preview_research_intent(
        handoff(),
        domain=ResearchDomain.WATER,
        activity=ResearchActivity.DECISION_SUPPORT,
        goal="Identificar una decisión hídrica recurrente y la evidencia territorial que hoy le falta.",
        territory_hint="Provincia de San Juan, Argentina",
    )

    assert preview.source_question_ref == "question:fixture:water-san-juan:001"
    assert preview.source_decision_ref == "decision:fixture:water-san-juan:001"
    assert preview.source_decision_fingerprint == "sha256:" + "1" * 64
    assert preview.source_freshness == "AS_OF_EXPORT"
    assert preview.question_raw == VALID_HANDOFF["question"]["raw"]
    assert preview.question_canonical == VALID_HANDOFF["question"]["canonical"]
    assert preview.question_profile_ref is None
    assert preview.domain is ResearchDomain.WATER
    assert preview.activity is ResearchActivity.DECISION_SUPPORT
    assert preview.goal == "Identificar una decisión hídrica recurrente y la evidencia territorial que hoy le falta."
    assert preview.constraints == tuple(VALID_HANDOFF["constraints"])
    assert preview.territory_hint == "Provincia de San Juan, Argentina"
    assert preview.territorial_scope_required is True


def test_preview_requires_explicit_non_empty_goal():
    with pytest.raises(ValueError, match="goal"):
        preview_research_intent(
            handoff(),
            domain=ResearchDomain.WATER,
            activity=ResearchActivity.DECISION_SUPPORT,
            goal="   ",
        )


def test_preview_does_not_silently_substitute_upstream_next_test_as_goal():
    explicit_goal = "Entender la decisión antes de seleccionar fuentes."
    preview = preview_research_intent(
        handoff(),
        domain=ResearchDomain.WATER,
        activity=ResearchActivity.DECISION_SUPPORT,
        goal=explicit_goal,
    )
    assert preview.goal == explicit_goal
    assert preview.goal != VALID_HANDOFF["investigation"]["next_test"]


def test_preview_requires_domain_enum_instead_of_inferring_from_question_text():
    with pytest.raises(TypeError, match="domain"):
        preview_research_intent(
            handoff(),
            domain="water",  # type: ignore[arg-type]
            activity=ResearchActivity.DECISION_SUPPORT,
            goal="bounded research",
        )


def test_preview_requires_activity_enum_instead_of_inferring_from_question_text():
    with pytest.raises(TypeError, match="activity"):
        preview_research_intent(
            handoff(),
            domain=ResearchDomain.WATER,
            activity="decision_support",  # type: ignore[arg-type]
            goal="bounded research",
        )


def test_preview_does_not_create_scope_actor_evidence_or_opportunity_fields():
    preview = preview_research_intent(
        handoff(),
        domain=ResearchDomain.WATER,
        activity=ResearchActivity.DECISION_SUPPORT,
        goal="bounded research",
    )
    assert not hasattr(preview, "territorial_scope")
    assert not hasattr(preview, "actor_refs")
    assert not hasattr(preview, "evidence_refs")
    assert not hasattr(preview, "opportunity")
    assert preview.territorial_scope_required is True


def test_build_research_intent_maps_only_explicit_preview_values():
    preview = preview_research_intent(
        handoff(),
        domain=ResearchDomain.WATER,
        activity=ResearchActivity.DECISION_SUPPORT,
        goal="Identificar evidencia faltante para una decisión hídrica recurrente.",
        territory_hint="San Juan, Argentina",
    )
    intent = build_research_intent(
        preview,
        intent_id="intent:water-san-juan:001",
        created_at="2026-09-05T01:00:00-03:00",
    )

    assert intent.to_dict() == {
        "contract_version": "0.1",
        "intent_id": "intent:water-san-juan:001",
        "question_raw": VALID_HANDOFF["question"]["raw"],
        "question_canonical": VALID_HANDOFF["question"]["canonical"],
        "question_profile_ref": None,
        "domain": "water",
        "activity": "decision_support",
        "goal": "Identificar evidencia faltante para una decisión hídrica recurrente.",
        "constraints": VALID_HANDOFF["constraints"],
        "territory_hint": "San Juan, Argentina",
        "created_at": "2026-09-05T01:00:00-03:00",
    }


def test_build_research_intent_keeps_upstream_refs_out_of_research_intent_contract():
    preview = preview_research_intent(
        handoff(),
        domain=ResearchDomain.WATER,
        activity=ResearchActivity.DECISION_SUPPORT,
        goal="bounded research",
    )
    payload = build_research_intent(
        preview,
        intent_id="intent:water-san-juan:002",
        created_at="2026-09-05T01:05:00-03:00",
    ).to_dict()

    assert "source_question_ref" not in payload
    assert "source_decision_ref" not in payload
    assert "source_decision_fingerprint" not in payload
    assert "source_freshness" not in payload
