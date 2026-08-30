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
from andes_context_os.hashing import sha256_json
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


class MatchReason(StrEnum):
    DOMAIN_MATCH = "domain_match"
    ACTIVITY_MATCH = "activity_match"
    TERRITORY_MATCH = "territory_match"


@dataclass(frozen=True, slots=True)
class ContextSelection:
    context_id: str
    kind: InternalContextKind
    title: str
    reference: str
    summary: str
    match_reasons: tuple[MatchReason, ...]
    limitations: tuple[str, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ContextSelection":
        fields = {"context_id", "kind", "title", "reference", "summary", "match_reasons", "limitations"}
        require_fields(payload, required=fields, allowed=fields)
        raw = require_string_list(payload["match_reasons"], "match_reasons", allow_empty=False)
        reasons = tuple(
            sorted(
                (_enum_value(MatchReason, item, "match_reasons") for item in raw),
                key=lambda item: item.value,
            )
        )
        return cls(
            context_id=require_text(payload["context_id"], "context_id"),
            kind=_enum_value(InternalContextKind, payload["kind"], "kind"),
            title=require_text(payload["title"], "title"),
            reference=require_text(payload["reference"], "reference"),
            summary=require_text(payload["summary"], "summary"),
            match_reasons=reasons,
            limitations=require_string_list(payload["limitations"], "limitations"),
        )

    @classmethod
    def from_record(
        cls,
        record: InternalContextRecord,
        reasons: tuple[MatchReason, ...],
    ) -> "ContextSelection":
        return cls.from_dict(
            {
                "context_id": record.context_id,
                "kind": record.kind.value,
                "title": record.title,
                "reference": record.reference,
                "summary": record.summary,
                "match_reasons": [reason.value for reason in reasons],
                "limitations": list(record.limitations),
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "kind": self.kind.value,
            "title": self.title,
            "reference": self.reference,
            "summary": self.summary,
            "match_reasons": [reason.value for reason in self.match_reasons],
            "limitations": list(self.limitations),
        }


_CATEGORY_BY_KIND = {
    InternalContextKind.VAULT_NOTE: "related_vault_notes",
    InternalContextKind.REPOSITORY: "related_repositories",
    InternalContextKind.FEATURE: "related_features",
    InternalContextKind.KNOWN_SOURCE: "known_sources",
    InternalContextKind.KNOWN_EVIDENCE: "known_evidence",
    InternalContextKind.KNOWN_GAP: "known_gaps",
    InternalContextKind.KNOWN_DECISION: "known_decisions",
}
_KIND_BY_CATEGORY = {field: kind for kind, field in _CATEGORY_BY_KIND.items()}
_CATEGORY_FIELDS = tuple(_KIND_BY_CATEGORY)


def _sha256_text(value: Any, field: str) -> str:
    text = require_text(value, field)
    if _SHA256_RE.fullmatch(text) is None:
        raise ValueError(f"{field} must be 64 lowercase hex characters")
    return text


@dataclass(frozen=True, slots=True)
class InternalContextSnapshot:
    contract_version: str
    snapshot_version: str
    snapshot_id: str
    generated_at: str
    research_intent_id: str
    question_profile_ref: str | None
    territorial_scope_id: str
    related_vault_notes: tuple[ContextSelection, ...]
    related_repositories: tuple[ContextSelection, ...]
    related_features: tuple[ContextSelection, ...]
    known_sources: tuple[ContextSelection, ...]
    known_evidence: tuple[ContextSelection, ...]
    known_gaps: tuple[ContextSelection, ...]
    known_decisions: tuple[ContextSelection, ...]
    missing_context: tuple[str, ...]

    @classmethod
    def build(
        cls,
        *,
        generated_at: str,
        research_intent_id: str,
        question_profile_ref: str | None,
        territorial_scope_id: str,
        selections: tuple[ContextSelection, ...],
        missing_context: tuple[str, ...],
    ) -> "InternalContextSnapshot":
        generated = require_aware_iso8601(generated_at, "generated_at")
        intent_id = require_text(research_intent_id, "research_intent_id")
        scope_id = require_text(territorial_scope_id, "territorial_scope_id")
        question_ref = _optional_text(question_profile_ref, "question_profile_ref")
        missing = require_string_list(list(missing_context), "missing_context")
        ordered = tuple(sorted(selections, key=lambda item: (item.kind.value, item.context_id)))
        buckets: dict[str, list[ContextSelection]] = {field: [] for field in _CATEGORY_FIELDS}
        for selection in ordered:
            buckets[_CATEGORY_BY_KIND[selection.kind]].append(selection)
        provisional = cls(
            contract_version=CONTRACT_VERSION,
            snapshot_version=SNAPSHOT_VERSION,
            snapshot_id="0" * 64,
            generated_at=generated,
            research_intent_id=intent_id,
            question_profile_ref=question_ref,
            territorial_scope_id=scope_id,
            related_vault_notes=tuple(buckets["related_vault_notes"]),
            related_repositories=tuple(buckets["related_repositories"]),
            related_features=tuple(buckets["related_features"]),
            known_sources=tuple(buckets["known_sources"]),
            known_evidence=tuple(buckets["known_evidence"]),
            known_gaps=tuple(buckets["known_gaps"]),
            known_decisions=tuple(buckets["known_decisions"]),
            missing_context=missing,
        )
        snapshot_id = sha256_json(provisional._payload_without_id())
        return cls(
            contract_version=provisional.contract_version,
            snapshot_version=provisional.snapshot_version,
            snapshot_id=snapshot_id,
            generated_at=provisional.generated_at,
            research_intent_id=provisional.research_intent_id,
            question_profile_ref=provisional.question_profile_ref,
            territorial_scope_id=provisional.territorial_scope_id,
            related_vault_notes=provisional.related_vault_notes,
            related_repositories=provisional.related_repositories,
            related_features=provisional.related_features,
            known_sources=provisional.known_sources,
            known_evidence=provisional.known_evidence,
            known_gaps=provisional.known_gaps,
            known_decisions=provisional.known_decisions,
            missing_context=provisional.missing_context,
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "InternalContextSnapshot":
        fields = {
            "contract_version",
            "snapshot_version",
            "snapshot_id",
            "generated_at",
            "research_intent_id",
            "question_profile_ref",
            "territorial_scope_id",
            "related_vault_notes",
            "related_repositories",
            "related_features",
            "known_sources",
            "known_evidence",
            "known_gaps",
            "known_decisions",
            "missing_context",
        }
        require_fields(payload, required=fields, allowed=fields)
        contract_version = require_text(payload["contract_version"], "contract_version")
        if contract_version != CONTRACT_VERSION:
            raise ValueError(f"contract_version must be {CONTRACT_VERSION}")
        snapshot_version = require_text(payload["snapshot_version"], "snapshot_version")
        if snapshot_version != SNAPSHOT_VERSION:
            raise ValueError(f"snapshot_version must be {SNAPSHOT_VERSION}")

        parsed_categories: dict[str, tuple[ContextSelection, ...]] = {}
        for category in _CATEGORY_FIELDS:
            raw_items = payload[category]
            if not isinstance(raw_items, list):
                raise ValueError(f"{category} must be a list")
            parsed: list[ContextSelection] = []
            expected_kind = _KIND_BY_CATEGORY[category]
            for raw in raw_items:
                if not isinstance(raw, dict):
                    raise ValueError(f"each {category} item must be an object")
                selection = ContextSelection.from_dict(raw)
                if selection.kind is not expected_kind:
                    raise ValueError(f"{category} contains selection with incompatible kind")
                parsed.append(selection)
            parsed_categories[category] = tuple(sorted(parsed, key=lambda item: item.context_id))

        snapshot = cls(
            contract_version=contract_version,
            snapshot_version=snapshot_version,
            snapshot_id=_sha256_text(payload["snapshot_id"], "snapshot_id"),
            generated_at=require_aware_iso8601(payload["generated_at"], "generated_at"),
            research_intent_id=require_text(payload["research_intent_id"], "research_intent_id"),
            question_profile_ref=_optional_text(payload["question_profile_ref"], "question_profile_ref"),
            territorial_scope_id=require_text(payload["territorial_scope_id"], "territorial_scope_id"),
            related_vault_notes=parsed_categories["related_vault_notes"],
            related_repositories=parsed_categories["related_repositories"],
            related_features=parsed_categories["related_features"],
            known_sources=parsed_categories["known_sources"],
            known_evidence=parsed_categories["known_evidence"],
            known_gaps=parsed_categories["known_gaps"],
            known_decisions=parsed_categories["known_decisions"],
            missing_context=require_string_list(payload["missing_context"], "missing_context"),
        )
        if sha256_json(snapshot._payload_without_id()) != snapshot.snapshot_id:
            raise ValueError("snapshot_id mismatch")
        return snapshot

    def _payload_without_id(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "snapshot_version": self.snapshot_version,
            "generated_at": self.generated_at,
            "research_intent_id": self.research_intent_id,
            "question_profile_ref": self.question_profile_ref,
            "territorial_scope_id": self.territorial_scope_id,
            "related_vault_notes": [item.to_dict() for item in self.related_vault_notes],
            "related_repositories": [item.to_dict() for item in self.related_repositories],
            "related_features": [item.to_dict() for item in self.related_features],
            "known_sources": [item.to_dict() for item in self.known_sources],
            "known_evidence": [item.to_dict() for item in self.known_evidence],
            "known_gaps": [item.to_dict() for item in self.known_gaps],
            "known_decisions": [item.to_dict() for item in self.known_decisions],
            "missing_context": list(self.missing_context),
        }

    def to_dict(self) -> dict[str, Any]:
        return {"snapshot_id": self.snapshot_id, **self._payload_without_id()}
