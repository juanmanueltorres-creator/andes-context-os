import json
from pathlib import Path

import pytest

from andes_context_os.handoffs import QuestionResearchHandoff
from andes_context_os.research import ResearchDomain


FIXTURES = Path(__file__).parent / "fixtures" / "handoffs"
QUESTION_FIXTURE = FIXTURES / "question_research_cartography_san_juan_v01.json"

EXPECTED_QUESTION = (
    "¿Qué errores de área, escala y percepción introduce el uso de Web Mercator en mapas "
    "territoriales de Argentina y San Juan, y qué CRS o proyección conviene utilizar según "
    "el objetivo: visualización web, análisis espacial, medición de superficie o comunicación "
    "pública?"
)


def load_question_handoff() -> QuestionResearchHandoff:
    payload = json.loads(QUESTION_FIXTURE.read_text(encoding="utf-8"))
    return QuestionResearchHandoff.from_dict(payload)


def test_cartography_question_handoff_is_valid_and_preserves_research_identity():
    handoff = load_question_handoff()

    assert handoff.question.raw == EXPECTED_QUESTION
    assert handoff.question.canonical == EXPECTED_QUESTION
    assert handoff.investigation.decision == "RESEARCH"
    assert handoff.routing.kind == "TERRITORIAL_RESEARCH"
    assert handoff.routing.destination == "andes-context-os"


def test_cartography_dogfood_stops_before_inventing_a_supported_domain():
    handoff = load_question_handoff()

    assert "No inferir un ResearchDomain soportado si la pregunta no encaja semánticamente." in handoff.constraints
    assert "territorial_cartography" not in {domain.value for domain in ResearchDomain}

    with pytest.raises(ValueError):
        ResearchDomain("territorial_cartography")
