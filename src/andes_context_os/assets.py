from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from andes_context_os.common import (
    CONTRACT_VERSION,
    require_fields,
    require_string_list,
    require_text,
)


class AssetType(StrEnum):
    MINING_PROJECT = "mining_project"


class ActorKind(StrEnum):
    ORGANIZATION = "organization"
    GOVERNMENT_BODY = "government_body"
    PERSON = "person"
    COMMUNITY = "community"
    OTHER = "other"


def _enum_value(enum_type: type[StrEnum], value: Any, field: str) -> StrEnum:
    text = require_text(value, field)
    try:
        return enum_type(text)
    except ValueError as exc:
        raise ValueError(f"{field} has unsupported value: {text}") from exc


def _optional_text(value: Any, field: str) -> str | None:
    return None if value is None else require_text(value, field)


@dataclass(frozen=True, slots=True)
class Asset:
    contract_version: str
    asset_id: str
    name: str
    asset_type: AssetType
    commodity: str
    territorial_scope_ref: str
    baseline_source_id: str
    baseline_record_ref: str
    notes: tuple[str, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Asset":
        fields = {
            "contract_version",
            "asset_id",
            "name",
            "asset_type",
            "commodity",
            "territorial_scope_ref",
            "baseline_source_id",
            "baseline_record_ref",
            "notes",
        }
        require_fields(payload, required=fields, allowed=fields)
        version = require_text(payload["contract_version"], "contract_version")
        if version != CONTRACT_VERSION:
            raise ValueError(f"contract_version must be {CONTRACT_VERSION}")
        return cls(
            version,
            require_text(payload["asset_id"], "asset_id"),
            require_text(payload["name"], "name"),
            _enum_value(AssetType, payload["asset_type"], "asset_type"),
            require_text(payload["commodity"], "commodity"),
            require_text(payload["territorial_scope_ref"], "territorial_scope_ref"),
            require_text(payload["baseline_source_id"], "baseline_source_id"),
            require_text(payload["baseline_record_ref"], "baseline_record_ref"),
            require_string_list(payload["notes"], "notes"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "asset_id": self.asset_id,
            "name": self.name,
            "asset_type": self.asset_type.value,
            "commodity": self.commodity,
            "territorial_scope_ref": self.territorial_scope_ref,
            "baseline_source_id": self.baseline_source_id,
            "baseline_record_ref": self.baseline_record_ref,
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class Actor:
    contract_version: str
    actor_id: str
    canonical_name: str
    actor_kind: ActorKind
    jurisdiction: str | None
    external_refs: tuple[str, ...]
    notes: tuple[str, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Actor":
        required = {
            "contract_version",
            "actor_id",
            "canonical_name",
            "actor_kind",
            "external_refs",
            "notes",
        }
        allowed = required | {"jurisdiction"}
        require_fields(payload, required=required, allowed=allowed)
        version = require_text(payload["contract_version"], "contract_version")
        if version != CONTRACT_VERSION:
            raise ValueError(f"contract_version must be {CONTRACT_VERSION}")
        return cls(
            version,
            require_text(payload["actor_id"], "actor_id"),
            require_text(payload["canonical_name"], "canonical_name"),
            _enum_value(ActorKind, payload["actor_kind"], "actor_kind"),
            _optional_text(payload.get("jurisdiction"), "jurisdiction"),
            require_string_list(payload["external_refs"], "external_refs"),
            require_string_list(payload["notes"], "notes"),
        )

    def to_dict(self) -> dict[str, Any]:
        result = {
            "contract_version": self.contract_version,
            "actor_id": self.actor_id,
            "canonical_name": self.canonical_name,
            "actor_kind": self.actor_kind.value,
            "external_refs": list(self.external_refs),
            "notes": list(self.notes),
        }
        if self.jurisdiction is not None:
            result["jurisdiction"] = self.jurisdiction
        return result
