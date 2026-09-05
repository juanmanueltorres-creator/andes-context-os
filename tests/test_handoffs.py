from copy import deepcopy

import pytest

from andes_context_os.handoffs import (
    QUESTION_RESEARCH_CONTRACT,
    SOURCE_FRESHNESS,
    TERRITORIAL_ROUTE,
    QuestionResearchHandoff,
)


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


def test_accepts_valid_territorial_question_handoff():
    handoff = QuestionResearchHandoff.from_dict(deepcopy(VALID_HANDOFF))
    assert handoff.contract == QUESTION_RESEARCH_CONTRACT
    assert handoff.routing.kind == TERRITORIAL_ROUTE
    assert handoff.source_freshness == SOURCE_FRESHNESS
    assert handoff.to_dict() == VALID_HANDOFF


def test_accepts_do_now_as_actionable_decision():
    payload = deepcopy(VALID_HANDOFF)
    payload["investigation"]["decision"] = "DO_NOW"
    assert QuestionResearchHandoff.from_dict(payload).investigation.decision == "DO_NOW"


def test_rejects_public_contribution_route():
    payload = deepcopy(VALID_HANDOFF)
    payload["routing"] = {
        "kind": "PUBLIC_CONTRIBUTION_RESEARCH",
        "destination": "opportunity-os",
    }
    with pytest.raises(ValueError, match="TERRITORIAL_RESEARCH"):
        QuestionResearchHandoff.from_dict(payload)


def test_rejects_wrong_destination_for_territorial_route():
    payload = deepcopy(VALID_HANDOFF)
    payload["routing"]["destination"] = "opportunity-os"
    with pytest.raises(ValueError, match="andes-context-os"):
        QuestionResearchHandoff.from_dict(payload)


def test_rejects_unsupported_contract_version():
    payload = {**VALID_HANDOFF, "contract": "question-research-handoff/v0.2"}
    with pytest.raises(ValueError, match="question-research-handoff/v0.1"):
        QuestionResearchHandoff.from_dict(payload)


def test_rejects_unknown_fields():
    payload = {**VALID_HANDOFF, "buyer": "someone"}
    with pytest.raises(ValueError, match="unknown fields: buyer"):
        QuestionResearchHandoff.from_dict(payload)


def test_rejects_unknown_nested_fields():
    payload = deepcopy(VALID_HANDOFF)
    payload["routing"]["confidence"] = 0.9
    with pytest.raises(ValueError, match="unknown fields: confidence"):
        QuestionResearchHandoff.from_dict(payload)


def test_rejects_non_actionable_decision():
    payload = deepcopy(VALID_HANDOFF)
    payload["investigation"]["decision"] = "PARKED"
    with pytest.raises(ValueError, match="DO_NOW.*RESEARCH|RESEARCH.*DO_NOW"):
        QuestionResearchHandoff.from_dict(payload)


def test_requires_decision_fingerprint():
    payload = deepcopy(VALID_HANDOFF)
    del payload["source"]["decision_fingerprint"]
    with pytest.raises(ValueError, match="decision_fingerprint"):
        QuestionResearchHandoff.from_dict(payload)


def test_rejects_malformed_decision_fingerprint():
    payload = deepcopy(VALID_HANDOFF)
    payload["source"]["decision_fingerprint"] = "sha256:not-a-digest"
    with pytest.raises(ValueError, match="decision_fingerprint"):
        QuestionResearchHandoff.from_dict(payload)


def test_requires_timezone_aware_created_at():
    payload = {**VALID_HANDOFF, "created_at": "2026-09-04T21:00:00"}
    with pytest.raises(ValueError, match="timezone-aware"):
        QuestionResearchHandoff.from_dict(payload)


def test_rejects_wrong_source_system():
    payload = deepcopy(VALID_HANDOFF)
    payload["source"]["system"] = "other-system"
    with pytest.raises(ValueError, match="question-radar"):
        QuestionResearchHandoff.from_dict(payload)
