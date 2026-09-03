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


class ActorRole(StrEnum):
    OPERATOR = "operator"
    OWNER = "owner"
    PARTNER = "partner"
    CONTRACTOR = "contractor"
    CONSULTANT = "consultant"
    SUPPLIER = "supplier"
    FINANCIER = "financier"
    OFFTAKER = "offtaker"
    REGULATOR = "regulator"
    STATE_PARTNER = "state_partner"
    COMMUNITY_ACTOR = "community_actor"
    OTHER = "other"


class MovementType(StrEnum):
    STAGE_CHANGE = "stage_change"
    DRILLING = "drilling"
    PERMIT = "permit"
    CAPITAL = "capital"
    OWNERSHIP = "ownership"
    PARTNERSHIP = "partnership"
    CONTRACTOR = "contractor"
    CONSULTING = "consulting"
    OFFTAKE = "offtake"
    CONSTRUCTION = "construction"
    INFRASTRUCTURE = "infrastructure"
    PRODUCTION = "production"
    EXPANSION = "expansion"
    HIRING = "hiring"
    OTHER = "other"


class MovementReviewState(StrEnum):
    UNREVIEWED = "unreviewed"
    EVIDENCE_LINKED = "evidence_linked"
    REVIEWED = "reviewed"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


def _enum_value(enum_type: type[StrEnum], value: Any, field: str) -> StrEnum:
    text = require_text(value, field)
    try:
        return enum_type(text)
    except ValueError as exc:
        raise ValueError(f"{field} has unsupported value: {text}") from exc


def _optional_text(value: Any, field: str) -> str | None:
    return None if value is None else require_text(value, field)


@dataclass(frozen=True, slots=True)
class MovementActorRef:
    actor_id: str
    role: ActorRole
    notes: tuple[str, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MovementActorRef":
        fields = {"actor_id", "role", "notes"}
        require_fields(payload, required=fields, allowed=fields)
        return cls(
            actor_id=require_text(payload["actor_id"], "actor_id"),
            role=_enum_value(ActorRole, payload["role"], "role"),
            notes=require_string_list(payload["notes"], "notes"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "role": self.role.value,
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class Movement:
    contract_version: str
    movement_id: str
    asset_id: str
    movement_type: MovementType
    observed_at: str
    actor_refs: tuple[MovementActorRef, ...]
    evidence_candidate_refs: tuple[str, ...]
    factual_summary: str
    previous_state: str | None
    new_state: str | None
    review_state: MovementReviewState
    reviewed_at: str | None
    derived_from_movement_ids: tuple[str, ...]
    limitations: tuple[str, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Movement":
        required = {
            "contract_version",
            "movement_id",
            "asset_id",
            "movement_type",
            "observed_at",
            "actor_refs",
            "evidence_candidate_refs",
            "factual_summary",
            "review_state",
            "derived_from_movement_ids",
            "limitations",
        }
        allowed = required | {"previous_state", "new_state", "reviewed_at"}
        require_fields(payload, required=required, allowed=allowed)

        version = require_text(payload["contract_version"], "contract_version")
        if version != CONTRACT_VERSION:
            raise ValueError(f"contract_version must be {CONTRACT_VERSION}")

        if not isinstance(payload["actor_refs"], list):
            raise ValueError("actor_refs must be a list")
        actor_refs = tuple(MovementActorRef.from_dict(item) for item in payload["actor_refs"])
        pairs = [(item.actor_id, item.role.value) for item in actor_refs]
        if len(pairs) != len(set(pairs)):
            raise ValueError("duplicate actor-role reference")

        evidence_refs = require_string_list(
            payload["evidence_candidate_refs"],
            "evidence_candidate_refs",
            allow_empty=False,
        )
        if len(evidence_refs) != len(set(evidence_refs)):
            raise ValueError("evidence_candidate_refs contains duplicates")

        movement_id = require_text(payload["movement_id"], "movement_id")
        movement_type = _enum_value(MovementType, payload["movement_type"], "movement_type")
        previous_state = _optional_text(payload.get("previous_state"), "previous_state")
        new_state = _optional_text(payload.get("new_state"), "new_state")
        if movement_type == MovementType.STAGE_CHANGE:
            if previous_state is None or new_state is None or previous_state == new_state:
                raise ValueError("stage_change requires distinct previous_state and new_state")

        review_state = _enum_value(MovementReviewState, payload["review_state"], "review_state")
        raw_reviewed_at = payload.get("reviewed_at")
        reviewed_at = (
            require_aware_iso8601(raw_reviewed_at, "reviewed_at")
            if raw_reviewed_at is not None
            else None
        )
        reviewed_states = {
            MovementReviewState.REVIEWED,
            MovementReviewState.REJECTED,
            MovementReviewState.SUPERSEDED,
        }
        if review_state in reviewed_states and reviewed_at is None:
            raise ValueError("reviewed_at is required for reviewed, rejected and superseded movements")
        if review_state not in reviewed_states and reviewed_at is not None:
            raise ValueError("reviewed_at must be null for unreviewed and evidence_linked movements")

        derived_ids = require_string_list(payload["derived_from_movement_ids"], "derived_from_movement_ids")
        if movement_id in derived_ids:
            raise ValueError("movement cannot derive from itself")
        if len(derived_ids) != len(set(derived_ids)):
            raise ValueError("derived_from_movement_ids contains duplicates")

        return cls(
            contract_version=version,
            movement_id=movement_id,
            asset_id=require_text(payload["asset_id"], "asset_id"),
            movement_type=movement_type,
            observed_at=require_aware_iso8601(payload["observed_at"], "observed_at"),
            actor_refs=actor_refs,
            evidence_candidate_refs=evidence_refs,
            factual_summary=require_text(payload["factual_summary"], "factual_summary"),
            previous_state=previous_state,
            new_state=new_state,
            review_state=review_state,
            reviewed_at=reviewed_at,
            derived_from_movement_ids=derived_ids,
            limitations=require_string_list(payload["limitations"], "limitations"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "movement_id": self.movement_id,
            "asset_id": self.asset_id,
            "movement_type": self.movement_type.value,
            "observed_at": self.observed_at,
            "actor_refs": [item.to_dict() for item in self.actor_refs],
            "evidence_candidate_refs": list(self.evidence_candidate_refs),
            "factual_summary": self.factual_summary,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
            "review_state": self.review_state.value,
            "reviewed_at": self.reviewed_at,
            "derived_from_movement_ids": list(self.derived_from_movement_ids),
            "limitations": list(self.limitations),
        }
