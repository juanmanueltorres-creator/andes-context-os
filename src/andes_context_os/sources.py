from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from enum import StrEnum
import math
from types import MappingProxyType
from typing import Any

from andes_context_os.common import (
    CONTRACT_VERSION,
    require_aware_iso8601,
    require_fields,
    require_string_list,
    require_text,
)


class SourceKind(StrEnum):
    OFFICIAL = "official"
    INSTITUTIONAL = "institutional"
    TECHNICAL = "technical"
    PEER_REVIEWED = "peer_reviewed"
    PUBLIC_DATASET = "public_dataset"
    PUBLIC_HUMAN_PLATFORM = "public_human_platform"
    INTERNAL = "internal"
    SENSOR = "sensor"
    DERIVED = "derived"
    REFERENCE_ONLY = "reference_only"


class SourceAuthority(StrEnum):
    PRIMARY_AUTHORITY = "primary_authority"
    OFFICIAL_PUBLISHER = "official_publisher"
    INSTITUTIONAL_PUBLISHER = "institutional_publisher"
    PEER_REVIEWED_RESEARCH = "peer_reviewed_research"
    TECHNICAL_PROVIDER = "technical_provider"
    COMMUNITY_SOURCE = "community_source"
    INTERNAL_SOURCE = "internal_source"
    UNKNOWN = "unknown"


class AccessType(StrEnum):
    API = "api"
    WMS = "wms"
    WFS = "wfs"
    ARCGIS_FEATURE_SERVICE = "arcgis_feature_service"
    DOWNLOAD = "download"
    REPOSITORY = "repository"
    WEB_PAGE = "web_page"
    SEARCH_RESULT = "search_result"
    MANUAL = "manual"


class TemporalCharacter(StrEnum):
    HISTORICAL = "historical"
    PERIODIC = "periodic"
    NEAR_REALTIME = "near_realtime"
    REALTIME_CLAIMED = "realtime_claimed"
    STATIC = "static"
    UNKNOWN = "unknown"


class LicenseStatus(StrEnum):
    VERIFIED_OPEN = "verified_open"
    VERIFIED_RESTRICTED = "verified_restricted"
    REFERENCE_ONLY = "reference_only"
    UNKNOWN_REVIEW_REQUIRED = "unknown_review_required"


class RightsChoice(StrEnum):
    YES = "yes"
    NO = "no"
    CONDITIONAL = "conditional"
    UNKNOWN = "unknown"


class DeclaredStatus(StrEnum):
    REGISTERED = "registered"
    CANDIDATE = "candidate"
    RESTRICTED = "restricted"
    DEPRECATED = "deprecated"
    UNKNOWN = "unknown"


class RuntimeStatus(StrEnum):
    AVAILABLE = "available"
    EMPTY = "empty"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    OMITTED = "omitted"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


class RuntimeMethod(StrEnum):
    HTTP_PROBE = "http_probe"
    ADAPTER_QUERY = "adapter_query"
    MANUAL_VERIFICATION = "manual_verification"
    CACHED_OBSERVATION = "cached_observation"
    REPOSITORY_READ = "repository_read"
    SEARCH_DISCOVERY = "search_discovery"


def _enum(enum_type: type[StrEnum], value: Any, field: str) -> StrEnum:
    text = require_text(value, field)
    try:
        return enum_type(text)
    except ValueError as exc:
        raise ValueError(f"{field} has unsupported value: {text}") from exc


def _opt(value: Any, field: str) -> str | None:
    return None if value is None else require_text(value, field)


def _bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be a boolean")
    return value


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be a finite number")
    return number


def _freeze(value: Any, field: str) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{field} must contain finite JSON values")
        return value
    if isinstance(value, list):
        return tuple(_freeze(item, field) for item in value)
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise ValueError(f"{field} object keys must be strings")
        return MappingProxyType({key: _freeze(value[key], field) for key in sorted(value)})
    raise ValueError(f"{field} must contain JSON-compatible values")


def _plain(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _plain(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class CoverageBBox:
    west: float
    south: float
    east: float
    north: float

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CoverageBBox":
        names = {"west", "south", "east", "north"}
        require_fields(payload, required=names, allowed=names)
        west, south = _number(payload["west"], "west"), _number(payload["south"], "south")
        east, north = _number(payload["east"], "east"), _number(payload["north"], "north")
        if not -180 <= west <= 180 or not -180 <= east <= 180:
            raise ValueError("west/east must be between -180 and 180")
        if not -90 <= south <= 90 or not -90 <= north <= 90:
            raise ValueError("south/north must be between -90 and 90")
        if west >= east:
            raise ValueError("west must be < east")
        if south >= north:
            raise ValueError("south must be < north")
        return cls(west, south, east, north)

    def to_dict(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True, slots=True)
class SourceAccess:
    access_type: AccessType
    endpoint_or_reference: str | None
    requires_auth: bool
    expected_formats: tuple[str, ...]
    rate_limit_notes: tuple[str, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SourceAccess":
        names = {"access_type", "endpoint_or_reference", "requires_auth", "expected_formats", "rate_limit_notes"}
        require_fields(payload, required=names, allowed=names)
        access_type = _enum(AccessType, payload["access_type"], "access_type")
        endpoint = _opt(payload["endpoint_or_reference"], "endpoint_or_reference")
        if endpoint is None and access_type != AccessType.MANUAL:
            raise ValueError("endpoint_or_reference is required unless access_type is manual")
        return cls(
            access_type,
            endpoint,
            _bool(payload["requires_auth"], "requires_auth"),
            require_string_list(payload["expected_formats"], "expected_formats"),
            require_string_list(payload["rate_limit_notes"], "rate_limit_notes"),
        )

    def to_dict(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True, slots=True)
class SourceCoverage:
    countries: tuple[str, ...]
    admin_units: tuple[str, ...]
    bbox: CoverageBBox | None
    coverage_description: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SourceCoverage":
        required = {"countries", "bbox", "coverage_description"}
        require_fields(payload, required=required, allowed=required | {"admin_units"})
        bbox = payload["bbox"]
        if bbox is not None and not isinstance(bbox, dict):
            raise ValueError("bbox must be an object or null")
        return cls(
            require_string_list(payload["countries"], "countries"),
            require_string_list(payload.get("admin_units", []), "admin_units"),
            CoverageBBox.from_dict(bbox) if bbox is not None else None,
            require_text(payload["coverage_description"], "coverage_description"),
        )

    def to_dict(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True, slots=True)
class SourceRights:
    license_status: LicenseStatus
    license_name: str | None
    license_reference: str | None
    commercial_reuse: RightsChoice
    redistribution: RightsChoice
    attribution_required: bool
    legal_review_required: bool
    rights_notes: tuple[str, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SourceRights":
        required = {"license_status", "commercial_reuse", "redistribution", "attribution_required", "legal_review_required", "rights_notes"}
        require_fields(payload, required=required, allowed=required | {"license_name", "license_reference"})
        license_status = _enum(LicenseStatus, payload["license_status"], "license_status")
        commercial = _enum(RightsChoice, payload["commercial_reuse"], "commercial_reuse")
        if commercial == RightsChoice.YES and license_status == LicenseStatus.UNKNOWN_REVIEW_REQUIRED:
            raise ValueError("commercial_reuse=yes is invalid when license_status is unknown_review_required")
        return cls(
            license_status,
            _opt(payload.get("license_name"), "license_name"),
            _opt(payload.get("license_reference"), "license_reference"),
            commercial,
            _enum(RightsChoice, payload["redistribution"], "redistribution"),
            _bool(payload["attribution_required"], "attribution_required"),
            _bool(payload["legal_review_required"], "legal_review_required"),
            require_string_list(payload["rights_notes"], "rights_notes"),
        )

    def to_dict(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True, slots=True)
class AdapterBinding:
    adapter_key: str
    adapter_min_version: str | None
    capabilities: tuple[str, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AdapterBinding":
        required = {"adapter_key", "capabilities"}
        require_fields(payload, required=required, allowed=required | {"adapter_min_version"})
        return cls(
            require_text(payload["adapter_key"], "adapter_key"),
            _opt(payload.get("adapter_min_version"), "adapter_min_version"),
            require_string_list(payload["capabilities"], "capabilities"),
        )

    def to_dict(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True, slots=True)
class SourceRecord:
    contract_version: str
    source_id: str
    display_name: str
    provider: str
    jurisdiction: str
    domains: tuple[str, ...]
    source_kind: SourceKind
    authority: SourceAuthority
    access: SourceAccess
    coverage: SourceCoverage
    temporal_character: TemporalCharacter
    rights: SourceRights
    adapter_binding: AdapterBinding
    declared_status: DeclaredStatus
    limitations: tuple[str, ...]
    references: tuple[str, ...]
    reviewed_at: str | None
    registry_notes: tuple[str, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SourceRecord":
        required = {
            "contract_version", "source_id", "display_name", "provider", "jurisdiction", "domains",
            "source_kind", "authority", "access", "coverage", "temporal_character", "rights",
            "adapter_binding", "declared_status", "limitations", "references", "registry_notes",
        }
        require_fields(payload, required=required, allowed=required | {"reviewed_at"})
        version = require_text(payload["contract_version"], "contract_version")
        if version != CONTRACT_VERSION:
            raise ValueError(f"contract_version must be {CONTRACT_VERSION}")
        for name in ("access", "coverage", "rights", "adapter_binding"):
            if not isinstance(payload[name], dict):
                raise ValueError(f"{name} must be an object")
        reviewed_at = payload.get("reviewed_at")
        return cls(
            version,
            require_text(payload["source_id"], "source_id"),
            require_text(payload["display_name"], "display_name"),
            require_text(payload["provider"], "provider"),
            require_text(payload["jurisdiction"], "jurisdiction"),
            require_string_list(payload["domains"], "domains", allow_empty=False),
            _enum(SourceKind, payload["source_kind"], "source_kind"),
            _enum(SourceAuthority, payload["authority"], "authority"),
            SourceAccess.from_dict(payload["access"]),
            SourceCoverage.from_dict(payload["coverage"]),
            _enum(TemporalCharacter, payload["temporal_character"], "temporal_character"),
            SourceRights.from_dict(payload["rights"]),
            AdapterBinding.from_dict(payload["adapter_binding"]),
            _enum(DeclaredStatus, payload["declared_status"], "declared_status"),
            require_string_list(payload["limitations"], "limitations"),
            require_string_list(payload["references"], "references"),
            require_aware_iso8601(reviewed_at, "reviewed_at") if reviewed_at is not None else None,
            require_string_list(payload["registry_notes"], "registry_notes"),
        )

    def to_dict(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True, slots=True)
class ResponseMetadata:
    http_status: int | None
    content_type: str | None
    record_count: int | None
    elapsed_ms: int | float | None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ResponseMetadata":
        names = {"http_status", "content_type", "record_count", "elapsed_ms"}
        require_fields(payload, required=set(), allowed=names)
        status = payload.get("http_status")
        if status is not None and (isinstance(status, bool) or not isinstance(status, int) or not 100 <= status <= 599):
            raise ValueError("http_status must be an integer between 100 and 599")
        count = payload.get("record_count")
        if count is not None and (isinstance(count, bool) or not isinstance(count, int) or count < 0):
            raise ValueError("record_count must be a non-negative integer")
        elapsed = payload.get("elapsed_ms")
        if elapsed is not None:
            number = _number(elapsed, "elapsed_ms")
            if number < 0:
                raise ValueError("elapsed_ms must be non-negative")
        return cls(status, _opt(payload.get("content_type"), "content_type"), count, elapsed)

    def to_dict(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True, slots=True)
class SourceRuntimeObservation:
    contract_version: str
    observation_id: str
    source_id: str
    observed_at: str
    status: RuntimeStatus
    method: RuntimeMethod
    adapter_key: str | None
    adapter_version: str | None
    response_metadata: ResponseMetadata | None
    freshness_observation: Any
    errors: tuple[str, ...]
    notes: tuple[str, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SourceRuntimeObservation":
        required = {"contract_version", "observation_id", "source_id", "observed_at", "status", "method", "errors", "notes"}
        optional = {"adapter_key", "adapter_version", "response_metadata", "freshness_observation"}
        require_fields(payload, required=required, allowed=required | optional)
        version = require_text(payload["contract_version"], "contract_version")
        if version != CONTRACT_VERSION:
            raise ValueError(f"contract_version must be {CONTRACT_VERSION}")
        status = _enum(RuntimeStatus, payload["status"], "status")
        errors = require_string_list(payload["errors"], "errors")
        notes = require_string_list(payload["notes"], "notes")
        if status == RuntimeStatus.OMITTED and not (errors or notes):
            raise ValueError("omitted runtime observation requires an explicit reason")
        metadata = payload.get("response_metadata")
        if metadata is not None and not isinstance(metadata, dict):
            raise ValueError("response_metadata must be an object or null")
        response = ResponseMetadata.from_dict(metadata) if metadata is not None else None
        if status == RuntimeStatus.EMPTY and (response is None or response.record_count != 0):
            raise ValueError("empty runtime observation requires record_count=0")
        freshness = payload.get("freshness_observation")
        if freshness is not None and not isinstance(freshness, dict):
            raise ValueError("freshness_observation must be an object or null")
        return cls(
            version,
            require_text(payload["observation_id"], "observation_id"),
            require_text(payload["source_id"], "source_id"),
            require_aware_iso8601(payload["observed_at"], "observed_at"),
            status,
            _enum(RuntimeMethod, payload["method"], "method"),
            _opt(payload.get("adapter_key"), "adapter_key"),
            _opt(payload.get("adapter_version"), "adapter_version"),
            response,
            _freeze(freshness, "freshness_observation") if freshness is not None else None,
            errors,
            notes,
        )

    def to_dict(self) -> dict[str, Any]:
        return _plain(self)
