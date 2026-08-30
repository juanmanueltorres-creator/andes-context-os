from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re
from types import MappingProxyType
from typing import Any, Mapping

from andes_context_os.common import (
    CONTRACT_VERSION,
    require_aware_iso8601,
    require_fields,
    require_string_list,
    require_text,
)
from andes_context_os.hashing import sha256_json
from andes_context_os.registry import SourceRegistry
from andes_context_os.research import ResearchIntent, TerritorialScope
from andes_context_os.sources import SourceRuntimeObservation


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class RunStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


class RecommendedAction(StrEnum):
    WATCH = "watch"
    RESEARCH = "research"
    VALIDATE = "validate"
    BUILD_SPIKE = "build_spike"
    DISCARD = "discard"


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


def _sha256_text(value: Any, field: str) -> str:
    text = require_text(value, field)
    if _SHA256_RE.fullmatch(text) is None:
        raise ValueError(f"{field} must be 64 lowercase hex characters")
    return text


def _adapter_versions(value: Any) -> Mapping[str, str]:
    if not isinstance(value, dict):
        raise ValueError("adapter_versions must be an object")
    cleaned: dict[str, str] = {}
    for raw_key, raw_value in value.items():
        if not isinstance(raw_key, str) or not raw_key.strip():
            raise ValueError("adapter_versions keys must be non-empty strings")
        if not isinstance(raw_value, str) or not raw_value.strip():
            raise ValueError("adapter_versions values must be non-empty strings")
        cleaned[raw_key.strip()] = raw_value.strip()
    return MappingProxyType(dict(sorted(cleaned.items())))


@dataclass(frozen=True, slots=True)
class Lineage:
    question_profile_ref: str | None
    internal_snapshot_ref: str | None
    source_registry_hash: str
    input_refs: tuple[str, ...]
    run_hash: str | None
    supersedes_run_id: str | None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Lineage":
        required = {"source_registry_hash", "input_refs"}
        allowed = required | {
            "question_profile_ref",
            "internal_snapshot_ref",
            "run_hash",
            "supersedes_run_id",
        }
        require_fields(payload, required=required, allowed=allowed)
        supplied_run_hash = payload.get("run_hash")
        return cls(
            question_profile_ref=_optional_text(payload.get("question_profile_ref"), "question_profile_ref"),
            internal_snapshot_ref=_optional_text(payload.get("internal_snapshot_ref"), "internal_snapshot_ref"),
            source_registry_hash=_sha256_text(payload["source_registry_hash"], "lineage source_registry_hash"),
            input_refs=require_string_list(payload["input_refs"], "input_refs"),
            run_hash=(
                _sha256_text(supplied_run_hash, "run_hash")
                if supplied_run_hash is not None
                else None
            ),
            supersedes_run_id=_optional_text(payload.get("supersedes_run_id"), "supersedes_run_id"),
        )

    def to_dict(self, *, run_hash: str | None = None, include_run_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "question_profile_ref": self.question_profile_ref,
            "internal_snapshot_ref": self.internal_snapshot_ref,
            "source_registry_hash": self.source_registry_hash,
            "input_refs": list(self.input_refs),
            "supersedes_run_id": self.supersedes_run_id,
        }
        if include_run_hash:
            payload["run_hash"] = run_hash if run_hash is not None else self.run_hash
        return payload


@dataclass(frozen=True, slots=True)
class DiscoveryRun:
    contract_version: str
    run_id: str
    research_intent: ResearchIntent
    territorial_scope: TerritorialScope
    generated_at: str
    source_registry_version: str
    source_registry_hash: str
    adapter_versions: Mapping[str, str]
    source_observations: tuple[SourceRuntimeObservation, ...]
    candidate_refs: tuple[str, ...]
    contradictions: tuple[str, ...]
    missing_context: tuple[str, ...]
    warnings: tuple[str, ...]
    omitted_sources: tuple[str, ...]
    run_status: RunStatus
    recommended_action: RecommendedAction
    recommended_action_reason: str
    lineage: Lineage

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DiscoveryRun":
        fields = {
            "contract_version",
            "run_id",
            "research_intent",
            "territorial_scope",
            "generated_at",
            "source_registry_version",
            "source_registry_hash",
            "adapter_versions",
            "source_observations",
            "candidate_refs",
            "contradictions",
            "missing_context",
            "warnings",
            "omitted_sources",
            "run_status",
            "recommended_action",
            "recommended_action_reason",
            "lineage",
        }
        require_fields(payload, required=fields, allowed=fields)

        contract_version = require_text(payload["contract_version"], "contract_version")
        if contract_version != CONTRACT_VERSION:
            raise ValueError(f"contract_version must be {CONTRACT_VERSION}")

        for name in ("research_intent", "territorial_scope", "lineage"):
            if not isinstance(payload[name], dict):
                raise ValueError(f"{name} must be an object")

        raw_observations = payload["source_observations"]
        if not isinstance(raw_observations, list):
            raise ValueError("source_observations must be a list")
        observations: list[SourceRuntimeObservation] = []
        for raw_observation in raw_observations:
            if not isinstance(raw_observation, dict):
                raise ValueError("each source_observation must be an object")
            observations.append(SourceRuntimeObservation.from_dict(raw_observation))

        run = cls(
            contract_version=contract_version,
            run_id=require_text(payload["run_id"], "run_id"),
            research_intent=ResearchIntent.from_dict(payload["research_intent"]),
            territorial_scope=TerritorialScope.from_dict(payload["territorial_scope"]),
            generated_at=require_aware_iso8601(payload["generated_at"], "generated_at"),
            source_registry_version=require_text(payload["source_registry_version"], "source_registry_version"),
            source_registry_hash=_sha256_text(payload["source_registry_hash"], "source_registry_hash"),
            adapter_versions=_adapter_versions(payload["adapter_versions"]),
            source_observations=tuple(observations),
            candidate_refs=require_string_list(payload["candidate_refs"], "candidate_refs"),
            contradictions=require_string_list(payload["contradictions"], "contradictions"),
            missing_context=require_string_list(payload["missing_context"], "missing_context"),
            warnings=require_string_list(payload["warnings"], "warnings"),
            omitted_sources=require_string_list(payload["omitted_sources"], "omitted_sources"),
            run_status=_enum(RunStatus, payload["run_status"], "run_status"),
            recommended_action=_enum(RecommendedAction, payload["recommended_action"], "recommended_action"),
            recommended_action_reason=require_text(
                payload["recommended_action_reason"], "recommended_action_reason"
            ),
            lineage=Lineage.from_dict(payload["lineage"]),
        )

        if run.lineage.run_hash is not None and run.lineage.run_hash != run.run_hash:
            raise ValueError("run_hash mismatch")
        return run

    def _hash_payload(self) -> dict[str, Any]:
        payload = self._to_dict(include_run_hash=False)
        payload["adapter_versions"] = dict(sorted(payload["adapter_versions"].items()))
        payload["source_observations"] = sorted(
            payload["source_observations"], key=lambda item: item["observation_id"]
        )
        for field in (
            "candidate_refs",
            "contradictions",
            "missing_context",
            "warnings",
            "omitted_sources",
        ):
            payload[field] = sorted(payload[field])
        payload["lineage"]["input_refs"] = sorted(payload["lineage"]["input_refs"])
        return payload

    @property
    def run_hash(self) -> str:
        return sha256_json(self._hash_payload())

    def _to_dict(self, *, include_run_hash: bool) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "run_id": self.run_id,
            "research_intent": self.research_intent.to_dict(),
            "territorial_scope": self.territorial_scope.to_dict(),
            "generated_at": self.generated_at,
            "source_registry_version": self.source_registry_version,
            "source_registry_hash": self.source_registry_hash,
            "adapter_versions": dict(self.adapter_versions),
            "source_observations": [observation.to_dict() for observation in self.source_observations],
            "candidate_refs": list(self.candidate_refs),
            "contradictions": list(self.contradictions),
            "missing_context": list(self.missing_context),
            "warnings": list(self.warnings),
            "omitted_sources": list(self.omitted_sources),
            "run_status": self.run_status.value,
            "recommended_action": self.recommended_action.value,
            "recommended_action_reason": self.recommended_action_reason,
            "lineage": self.lineage.to_dict(
                run_hash=self.run_hash if include_run_hash else None,
                include_run_hash=include_run_hash,
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        return self._to_dict(include_run_hash=True)


def validate_run_against_registry(run: DiscoveryRun, registry: SourceRegistry) -> None:
    if run.source_registry_version != registry.registry_version:
        raise ValueError(
            f"registry version mismatch: run={run.source_registry_version} registry={registry.registry_version}"
        )
    if run.source_registry_hash != registry.registry_hash:
        raise ValueError("registry hash mismatch")
    if run.lineage.source_registry_hash != run.source_registry_hash:
        raise ValueError("lineage source_registry_hash mismatch")
