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
from andes_context_os.sources import SourceAuthority


class SourceVerification(StrEnum):
    UNVERIFIED = "unverified"
    SOURCE_LOCATED = "source_located"
    SOURCE_IDENTITY_VERIFIED = "source_identity_verified"
    TECHNICALLY_REVIEWED = "technically_reviewed"
    INSTITUTIONALLY_REVIEWED = "institutionally_reviewed"


class Freshness(StrEnum):
    CURRENT = "current"
    DATED = "dated"
    STALE = "stale"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class SpatialPrecision(StrEnum):
    EXACT = "exact"
    SEGMENT = "segment"
    CORRIDOR = "corridor"
    PROJECT_AREA = "project_area"
    LOCALITY = "locality"
    ADMIN_UNIT = "admin_unit"
    REGIONAL = "regional"
    CONTEXTUAL = "contextual"
    UNKNOWN = "unknown"


class TemporalPrecision(StrEnum):
    EXACT_TIMESTAMP = "exact_timestamp"
    BOUNDED_INTERVAL = "bounded_interval"
    DAY = "day"
    PERIOD = "period"
    HISTORICAL = "historical"
    CONTEXTUAL = "contextual"
    UNKNOWN = "unknown"


class EvidenceCoverage(StrEnum):
    COMPLETE_FOR_CLAIM = "complete_for_claim"
    PARTIAL = "partial"
    CONTEXT_ONLY = "context_only"
    UNKNOWN = "unknown"


class Completeness(StrEnum):
    COMPLETE_FOR_CONTRACT = "complete_for_contract"
    PARTIAL = "partial"
    INDETERMINATE = "indeterminate"


class Corroboration(StrEnum):
    NONE = "none"
    SINGLE_SOURCE = "single_source"
    MULTIPLE_INDEPENDENT_SOURCES = "multiple_independent_sources"
    PARTIALLY_CORROBORATED = "partially_corroborated"
    CONTRADICTED = "contradicted"
    UNKNOWN = "unknown"


class MethodTransparency(StrEnum):
    DOCUMENTED = "documented"
    PARTIALLY_DOCUMENTED = "partially_documented"
    OPAQUE = "opaque"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class RightsClarity(StrEnum):
    CLEAR_OPEN = "clear_open"
    CLEAR_RESTRICTED = "clear_restricted"
    REFERENCE_ONLY = "reference_only"
    UNKNOWN = "unknown"


class ReviewState(StrEnum):
    UNREVIEWED = "unreviewed"
    SOURCE_VERIFIED = "source_verified"
    TECHNICALLY_REVIEWED = "technically_reviewed"
    INSTITUTIONALLY_REVIEWED = "institutionally_reviewed"
    DISCARDED = "discarded"
    SUPERSEDED = "superseded"


class CandidateKind(StrEnum):
    INTERNAL_CONTEXT = "internal_context"
    PUBLIC_HUMAN_SIGNAL = "public_human_signal"
    DATASET = "dataset"
    TECHNICAL_REFERENCE = "technical_reference"
    OFFICIAL_RECORD = "official_record"
    DERIVED_CANDIDATE = "derived_candidate"


class CandidateState(StrEnum):
    DISCOVERED = "discovered"
    NEEDS_REVIEW = "needs_review"
    USABLE_FOR_RESEARCH = "usable_for_research"
    RESTRICTED = "restricted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


def _enum(enum_type: type[StrEnum], value: Any, field: str) -> StrEnum:
    text = require_text(value, field)
    try:
        return enum_type(text)
    except ValueError as exc:
        raise ValueError(f"{field} has unsupported value: {text}") from exc


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return require_text(value, field)


@dataclass(frozen=True, slots=True)
class EvidenceQualityVector:
    contract_version: str
    authority: SourceAuthority
    source_verification: SourceVerification
    freshness: Freshness
    spatial_precision: SpatialPrecision
    temporal_precision: TemporalPrecision
    coverage: EvidenceCoverage
    completeness: Completeness
    corroboration: Corroboration
    method_transparency: MethodTransparency
    rights_clarity: RightsClarity
    review_state: ReviewState
    limitations: tuple[str, ...]
    missing_context: tuple[str, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EvidenceQualityVector":
        fields = {
            "contract_version", "authority", "source_verification", "freshness",
            "spatial_precision", "temporal_precision", "coverage", "completeness",
            "corroboration", "method_transparency", "rights_clarity", "review_state",
            "limitations", "missing_context",
        }
        require_fields(payload, required=fields, allowed=fields)
        version = require_text(payload["contract_version"], "contract_version")
        if version != CONTRACT_VERSION:
            raise ValueError(f"contract_version must be {CONTRACT_VERSION}")
        return cls(
            version,
            _enum(SourceAuthority, payload["authority"], "authority"),
            _enum(SourceVerification, payload["source_verification"], "source_verification"),
            _enum(Freshness, payload["freshness"], "freshness"),
            _enum(SpatialPrecision, payload["spatial_precision"], "spatial_precision"),
            _enum(TemporalPrecision, payload["temporal_precision"], "temporal_precision"),
            _enum(EvidenceCoverage, payload["coverage"], "coverage"),
            _enum(Completeness, payload["completeness"], "completeness"),
            _enum(Corroboration, payload["corroboration"], "corroboration"),
            _enum(MethodTransparency, payload["method_transparency"], "method_transparency"),
            _enum(RightsClarity, payload["rights_clarity"], "rights_clarity"),
            _enum(ReviewState, payload["review_state"], "review_state"),
            require_string_list(payload["limitations"], "limitations"),
            require_string_list(payload["missing_context"], "missing_context"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "authority": self.authority.value,
            "source_verification": self.source_verification.value,
            "freshness": self.freshness.value,
            "spatial_precision": self.spatial_precision.value,
            "temporal_precision": self.temporal_precision.value,
            "coverage": self.coverage.value,
            "completeness": self.completeness.value,
            "corroboration": self.corroboration.value,
            "method_transparency": self.method_transparency.value,
            "rights_clarity": self.rights_clarity.value,
            "review_state": self.review_state.value,
            "limitations": list(self.limitations),
            "missing_context": list(self.missing_context),
        }


@dataclass(frozen=True, slots=True)
class TemporalContext:
    published_at: str | None = None
    observed_at: str | None = None
    description: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TemporalContext":
        allowed = {"published_at", "observed_at", "description"}
        require_fields(payload, required=set(), allowed=allowed)
        published = payload.get("published_at")
        observed = payload.get("observed_at")
        description = payload.get("description")
        if published is None and observed is None and description is None:
            raise ValueError("temporal_context requires at least one field")
        return cls(
            require_aware_iso8601(published, "published_at") if published is not None else None,
            require_aware_iso8601(observed, "observed_at") if observed is not None else None,
            _optional_text(description, "description"),
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if self.published_at is not None:
            result["published_at"] = self.published_at
        if self.observed_at is not None:
            result["observed_at"] = self.observed_at
        if self.description is not None:
            result["description"] = self.description
        return result


@dataclass(frozen=True, slots=True)
class TerritorialRelation:
    scope_id: str
    relation: str
    notes: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TerritorialRelation":
        required = {"scope_id", "relation"}
        require_fields(payload, required=required, allowed=required | {"notes"})
        return cls(
            require_text(payload["scope_id"], "scope_id"),
            require_text(payload["relation"], "relation"),
            require_string_list(payload.get("notes", []), "notes"),
        )

    def to_dict(self) -> dict[str, Any]:
        result = {"scope_id": self.scope_id, "relation": self.relation}
        if self.notes:
            result["notes"] = list(self.notes)
        return result


@dataclass(frozen=True, slots=True)
class EvidenceCandidate:
    candidate_id: str
    source_id: str
    source_runtime_observation_id: str | None
    kind: CandidateKind
    title: str
    factual_summary: str
    source_reference: str
    temporal_context: TemporalContext
    territorial_relation: TerritorialRelation
    quality: EvidenceQualityVector
    payload_ref: str | None
    corroboration_refs: tuple[str, ...]
    derived_from_ids: tuple[str, ...]
    candidate_state: CandidateState

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EvidenceCandidate":
        fields = {
            "candidate_id", "source_id", "source_runtime_observation_id", "kind", "title",
            "factual_summary", "source_reference", "temporal_context", "territorial_relation",
            "quality", "payload_ref", "corroboration_refs", "derived_from_ids", "candidate_state",
        }
        require_fields(payload, required=fields, allowed=fields)
        for name in ("temporal_context", "territorial_relation", "quality"):
            if not isinstance(payload[name], dict):
                raise ValueError(f"{name} must be an object")
        quality = EvidenceQualityVector.from_dict(payload["quality"])
        refs = require_string_list(payload["corroboration_refs"], "corroboration_refs")
        if quality.corroboration == Corroboration.MULTIPLE_INDEPENDENT_SOURCES:
            if len(set(refs)) < 2:
                raise ValueError("multiple_independent_sources requires at least two distinct corroboration_refs")
        return cls(
            require_text(payload["candidate_id"], "candidate_id"),
            require_text(payload["source_id"], "source_id"),
            _optional_text(payload["source_runtime_observation_id"], "source_runtime_observation_id"),
            _enum(CandidateKind, payload["kind"], "kind"),
            require_text(payload["title"], "title"),
            require_text(payload["factual_summary"], "factual_summary"),
            require_text(payload["source_reference"], "source_reference"),
            TemporalContext.from_dict(payload["temporal_context"]),
            TerritorialRelation.from_dict(payload["territorial_relation"]),
            quality,
            _optional_text(payload["payload_ref"], "payload_ref"),
            refs,
            require_string_list(payload["derived_from_ids"], "derived_from_ids"),
            _enum(CandidateState, payload["candidate_state"], "candidate_state"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "source_id": self.source_id,
            "source_runtime_observation_id": self.source_runtime_observation_id,
            "kind": self.kind.value,
            "title": self.title,
            "factual_summary": self.factual_summary,
            "source_reference": self.source_reference,
            "temporal_context": self.temporal_context.to_dict(),
            "territorial_relation": self.territorial_relation.to_dict(),
            "quality": self.quality.to_dict(),
            "payload_ref": self.payload_ref,
            "corroboration_refs": list(self.corroboration_refs),
            "derived_from_ids": list(self.derived_from_ids),
            "candidate_state": self.candidate_state.value,
        }
