from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import Path
import re
from typing import Any

from andes_context_os.common import (
    CONTRACT_VERSION,
    require_aware_iso8601,
    require_fields,
    require_string_list,
    require_text,
)
from andes_context_os.research import ResearchActivity, ResearchDomain

CATALOG_VERSION = "0.1"
SNAPSHOT_VERSION = "0.1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class InternalContextKind(StrEnum):
    VAULT_NOTE = "vault_note"
    REPOSITORY = "repository"
    FEATURE = "feature"
    KNOWN_SOURCE = "known_source"
    KNOWN_EVIDENCE = "known_evidence"
    KNOWN_GAP = "known_gap"
    KNOWN_DECISION = "known_decision"


class ContextSensitivity(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"


def _enum_value(enum_type: type[StrEnum], value: Any, field: str) -> StrEnum:
    text = require_text(value, field)
    try:
        return enum_type(text)
    except ValueError as exc:
        raise ValueError(f"{field} has unsupported value: {text}") from exc


def _enum_list(enum_type: type[StrEnum], value: Any, field: str) -> tuple[StrEnum, ...]:
    return tuple(_enum_value(enum_type, item, field) for item in require_string_list(value, field))


def _optional_text(value: Any, field: str) -> str | None:
    return None if value is None else require_text(value, field)


@dataclass(frozen=True, slots=True)
class InternalContextRecord:
    contract_version: str
    context_id: str
    kind: InternalContextKind
    title: str
    reference: str
    summary: str
    domains: tuple[ResearchDomain, ...]
    activities: tuple[ResearchActivity, ...]
    territory_refs: tuple[str, ...]
    tags: tuple[str, ...]
    sensitivity: ContextSensitivity
    reviewed_at: str | None
    limitations: tuple[str, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "InternalContextRecord":
        required = {
            "contract_version", "context_id", "kind", "title", "reference", "summary",
            "domains", "activities", "territory_refs", "tags", "sensitivity", "limitations",
        }
        allowed = required | {"reviewed_at"}
        require_fields(payload, required=required, allowed=allowed)
        version = require_text(payload["contract_version"], "contract_version")
        if version != CONTRACT_VERSION:
            raise ValueError(f"contract_version must be {CONTRACT_VERSION}")
        reviewed_at = payload.get("reviewed_at")
        return cls(
            contract_version=version,
            context_id=require_text(payload["context_id"], "context_id"),
            kind=_enum_value(InternalContextKind, payload["kind"], "kind"),
            title=require_text(payload["title"], "title"),
            reference=require_text(payload["reference"], "reference"),
            summary=require_text(payload["summary"], "summary"),
            domains=_enum_list(ResearchDomain, payload["domains"], "domains"),
            activities=_enum_list(ResearchActivity, payload["activities"], "activities"),
            territory_refs=require_string_list(payload["territory_refs"], "territory_refs"),
            tags=require_string_list(payload["tags"], "tags"),
            sensitivity=_enum_value(ContextSensitivity, payload["sensitivity"], "sensitivity"),
            reviewed_at=(require_aware_iso8601(reviewed_at, "reviewed_at") if reviewed_at is not None else None),
            limitations=require_string_list(payload["limitations"], "limitations"),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "contract_version": self.contract_version,
            "context_id": self.context_id,
            "kind": self.kind.value,
            "title": self.title,
            "reference": self.reference,
            "summary": self.summary,
            "domains": [item.value for item in self.domains],
            "activities": [item.value for item in self.activities],
            "territory_refs": list(self.territory_refs),
            "tags": list(self.tags),
            "sensitivity": self.sensitivity.value,
            "limitations": list(self.limitations),
        }
        if self.reviewed_at is not None:
            payload["reviewed_at"] = self.reviewed_at
        return payload


@dataclass(frozen=True, slots=True)
class InternalContextCatalog:
    catalog_version: str
    records: tuple[InternalContextRecord, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "InternalContextCatalog":
        fields = {"catalog_version", "records"}
        require_fields(payload, required=fields, allowed=fields)
        version = require_text(payload["catalog_version"], "catalog_version")
        if version != CATALOG_VERSION:
            raise ValueError(f"catalog_version must be {CATALOG_VERSION}")
        raw_records = payload["records"]
        if not isinstance(raw_records, list):
            raise ValueError("records must be a list")
        parsed: list[InternalContextRecord] = []
        for item in raw_records:
            if not isinstance(item, dict):
                raise ValueError("each record must be an object")
            parsed.append(InternalContextRecord.from_dict(item))
        ids = [record.context_id for record in parsed]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate context_id in internal context catalog")
        return cls(catalog_version=version, records=tuple(parsed))

    @classmethod
    def load(cls, path: str | Path) -> "InternalContextCatalog":
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("invalid internal context catalog JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("internal context catalog root must be an object")
        return cls.from_dict(payload)

    def to_dict(self) -> dict[str, Any]:
        return {"catalog_version": self.catalog_version, "records": [record.to_dict() for record in self.records]}
