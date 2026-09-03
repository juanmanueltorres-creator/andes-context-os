from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from andes_context_os.common import (
    CONTRACT_VERSION,
    require_aware_iso8601,
    require_fields,
    require_string_list,
    require_text,
)


class OpportunityStatus(StrEnum):
    PROPOSED = "proposed"
    RESEARCHING = "researching"
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    DISCARDED = "discarded"


def _enum_value(enum_type: type[StrEnum], value: Any, field: str) -> StrEnum:
    text = require_text(value, field)
    try:
        return enum_type(text)
    except ValueError as exc:
        raise ValueError(f"{field} has unsupported value: {text}") from exc


@dataclass(frozen=True, slots=True)
class OpportunityHypothesis:
    contract_version: str
    hypothesis_id: str
    asset_id: str
    trigger_movement_refs: tuple[str, ...]
    actor_refs: tuple[str, ...]
    need_category: str
    statement: str
    supporting_evidence_refs: tuple[str, ...]
    assumptions: tuple[str, ...]
    missing_context: tuple[str, ...]
    status: OpportunityStatus
    created_at: str
    reviewed_at: str | None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "OpportunityHypothesis":
        required = {
            "contract_version",
            "hypothesis_id",
            "asset_id",
            "trigger_movement_refs",
            "actor_refs",
            "need_category",
            "statement",
            "supporting_evidence_refs",
            "assumptions",
            "missing_context",
            "status",
            "created_at",
        }
        allowed = required | {"reviewed_at"}
        require_fields(payload, required=required, allowed=allowed)

        version = require_text(payload["contract_version"], "contract_version")
        if version != CONTRACT_VERSION:
            raise ValueError(f"contract_version must be {CONTRACT_VERSION}")

        triggers = require_string_list(
            payload["trigger_movement_refs"],
            "trigger_movement_refs",
            allow_empty=False,
        )
        actors = require_string_list(payload["actor_refs"], "actor_refs")
        support = require_string_list(payload["supporting_evidence_refs"], "supporting_evidence_refs")
        for field, values in (
            ("trigger_movement_refs", triggers),
            ("actor_refs", actors),
            ("supporting_evidence_refs", support),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"{field} contains duplicates")

        status = _enum_value(OpportunityStatus, payload["status"], "status")
        raw_reviewed_at = payload.get("reviewed_at")
        reviewed_at = (
            require_aware_iso8601(raw_reviewed_at, "reviewed_at")
            if raw_reviewed_at is not None
            else None
        )

        if status == OpportunityStatus.SUPPORTED and not support:
            raise ValueError("supported requires supporting_evidence_refs")
        if status == OpportunityStatus.CONTRADICTED and not support:
            raise ValueError("contradicted requires supporting_evidence_refs")

        reviewed_states = {
            OpportunityStatus.SUPPORTED,
            OpportunityStatus.CONTRADICTED,
            OpportunityStatus.DISCARDED,
        }
        if status in reviewed_states and reviewed_at is None:
            raise ValueError("reviewed_at is required for supported, contradicted and discarded hypotheses")
        if status not in reviewed_states and reviewed_at is not None:
            raise ValueError("reviewed_at must be null for proposed and researching hypotheses")

        return cls(
            contract_version=version,
            hypothesis_id=require_text(payload["hypothesis_id"], "hypothesis_id"),
            asset_id=require_text(payload["asset_id"], "asset_id"),
            trigger_movement_refs=triggers,
            actor_refs=actors,
            need_category=require_text(payload["need_category"], "need_category"),
            statement=require_text(payload["statement"], "statement"),
            supporting_evidence_refs=support,
            assumptions=require_string_list(payload["assumptions"], "assumptions"),
            missing_context=require_string_list(payload["missing_context"], "missing_context"),
            status=status,
            created_at=require_aware_iso8601(payload["created_at"], "created_at"),
            reviewed_at=reviewed_at,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "hypothesis_id": self.hypothesis_id,
            "asset_id": self.asset_id,
            "trigger_movement_refs": list(self.trigger_movement_refs),
            "actor_refs": list(self.actor_refs),
            "need_category": self.need_category,
            "statement": self.statement,
            "supporting_evidence_refs": list(self.supporting_evidence_refs),
            "assumptions": list(self.assumptions),
            "missing_context": list(self.missing_context),
            "status": self.status.value,
            "created_at": self.created_at,
            "reviewed_at": self.reviewed_at,
        }
