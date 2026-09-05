from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from andes_context_os.common import (
    require_aware_iso8601,
    require_fields,
    require_string_list,
    require_text,
)
from andes_context_os.opportunities import OpportunityHypothesis, OpportunityStatus


ACTOR_NEED_KIND = "ACTOR_NEED_HYPOTHESIS"
RESEARCH_OPPORTUNITY_CONTRACT = "research-opportunity-handoff/v0.1"

_TOP_LEVEL_FIELDS = {"contract", "handoff_id", "created_at", "source", "candidate"}
_SOURCE_FIELDS = {
    "system",
    "source_question_ref",
    "research_intent_ref",
    "hypothesis_ref",
}
_CANDIDATE_FIELDS = {
    "kind",
    "need_category",
    "statement",
    "actor_refs",
    "evidence_refs",
    "assumptions",
    "missing_context",
    "research_status",
}


def _require_object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return value


@dataclass(frozen=True, slots=True)
class ResearchOpportunitySource:
    system: str
    source_question_ref: str
    research_intent_ref: str
    hypothesis_ref: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ResearchOpportunitySource":
        require_fields(payload, required=_SOURCE_FIELDS, allowed=_SOURCE_FIELDS)
        system = require_text(payload["system"], "source.system")
        if system != "andes-context-os":
            raise ValueError("source.system must be andes-context-os")
        return cls(
            system=system,
            source_question_ref=require_text(
                payload["source_question_ref"], "source.source_question_ref"
            ),
            research_intent_ref=require_text(
                payload["research_intent_ref"], "source.research_intent_ref"
            ),
            hypothesis_ref=require_text(
                payload["hypothesis_ref"], "source.hypothesis_ref"
            ),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "system": self.system,
            "source_question_ref": self.source_question_ref,
            "research_intent_ref": self.research_intent_ref,
            "hypothesis_ref": self.hypothesis_ref,
        }


@dataclass(frozen=True, slots=True)
class ActorNeedCandidate:
    kind: str
    need_category: str
    statement: str
    actor_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    assumptions: tuple[str, ...]
    missing_context: tuple[str, ...]
    research_status: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ActorNeedCandidate":
        require_fields(
            payload,
            required=_CANDIDATE_FIELDS,
            allowed=_CANDIDATE_FIELDS,
        )
        kind = require_text(payload["kind"], "candidate.kind")
        if kind != ACTOR_NEED_KIND:
            raise ValueError(f"candidate.kind must be {ACTOR_NEED_KIND}")
        research_status = require_text(
            payload["research_status"], "candidate.research_status"
        )
        try:
            OpportunityStatus(research_status)
        except ValueError as exc:
            raise ValueError("candidate.research_status is unsupported") from exc
        return cls(
            kind=kind,
            need_category=require_text(
                payload["need_category"], "candidate.need_category"
            ),
            statement=require_text(payload["statement"], "candidate.statement"),
            actor_refs=require_string_list(
                payload["actor_refs"], "candidate.actor_refs"
            ),
            evidence_refs=require_string_list(
                payload["evidence_refs"], "candidate.evidence_refs"
            ),
            assumptions=require_string_list(
                payload["assumptions"], "candidate.assumptions"
            ),
            missing_context=require_string_list(
                payload["missing_context"], "candidate.missing_context"
            ),
            research_status=research_status,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "need_category": self.need_category,
            "statement": self.statement,
            "actor_refs": list(self.actor_refs),
            "evidence_refs": list(self.evidence_refs),
            "assumptions": list(self.assumptions),
            "missing_context": list(self.missing_context),
            "research_status": self.research_status,
        }


@dataclass(frozen=True, slots=True)
class ResearchOpportunityHandoff:
    contract: str
    handoff_id: str
    created_at: str
    source: ResearchOpportunitySource
    candidate: ActorNeedCandidate

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ResearchOpportunityHandoff":
        payload = _require_object(payload, "handoff")
        require_fields(
            payload,
            required=_TOP_LEVEL_FIELDS,
            allowed=_TOP_LEVEL_FIELDS,
        )
        contract = require_text(payload["contract"], "contract")
        if contract != RESEARCH_OPPORTUNITY_CONTRACT:
            raise ValueError(f"contract must be {RESEARCH_OPPORTUNITY_CONTRACT}")
        return cls(
            contract=contract,
            handoff_id=require_text(payload["handoff_id"], "handoff_id"),
            created_at=require_aware_iso8601(payload["created_at"], "created_at"),
            source=ResearchOpportunitySource.from_dict(
                _require_object(payload["source"], "source")
            ),
            candidate=ActorNeedCandidate.from_dict(
                _require_object(payload["candidate"], "candidate")
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract": self.contract,
            "handoff_id": self.handoff_id,
            "created_at": self.created_at,
            "source": self.source.to_dict(),
            "candidate": self.candidate.to_dict(),
        }


def build_actor_need_handoff(
    hypothesis: OpportunityHypothesis,
    *,
    source_question_ref: str,
    research_intent_ref: str,
    handoff_id: str,
    created_at: str,
) -> ResearchOpportunityHandoff:
    if not isinstance(hypothesis, OpportunityHypothesis):
        raise TypeError("hypothesis must be an OpportunityHypothesis")

    payload = {
        "contract": RESEARCH_OPPORTUNITY_CONTRACT,
        "handoff_id": handoff_id,
        "created_at": created_at,
        "source": {
            "system": "andes-context-os",
            "source_question_ref": source_question_ref,
            "research_intent_ref": research_intent_ref,
            "hypothesis_ref": hypothesis.hypothesis_id,
        },
        "candidate": {
            "kind": ACTOR_NEED_KIND,
            "need_category": hypothesis.need_category,
            "statement": hypothesis.statement,
            "actor_refs": list(hypothesis.actor_refs),
            "evidence_refs": list(hypothesis.supporting_evidence_refs),
            "assumptions": list(hypothesis.assumptions),
            "missing_context": list(hypothesis.missing_context),
            "research_status": hypothesis.status.value,
        },
    }
    return ResearchOpportunityHandoff.from_dict(payload)


def render_research_opportunity_handoff_json(
    handoff: ResearchOpportunityHandoff,
) -> str:
    if not isinstance(handoff, ResearchOpportunityHandoff):
        raise TypeError("handoff must be a ResearchOpportunityHandoff")
    return (
        json.dumps(
            handoff.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )
