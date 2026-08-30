from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
from typing import Any

from andes_context_os.common import (
    CONTRACT_VERSION,
    require_aware_iso8601,
    require_fields,
    require_string_list,
    require_text,
)


class ResearchDomain(StrEnum):
    MINING = "mining"
    GEOLOGY = "geology"
    LOGISTICS = "logistics"
    ACCESS = "access"
    WATER = "water"
    ENVIRONMENT = "environment"
    COMMUNITY = "community"
    WORKFORCE = "workforce"


class ResearchActivity(StrEnum):
    ACCESS = "access"
    HAULAGE = "haulage"
    MOBILIZATION = "mobilization"
    ROUTE_PLANNING = "route_planning"
    ROAD_CONDITION = "road_condition"
    FIELD_OPERATIONS = "field_operations"


class ScopePrecision(StrEnum):
    EXACT_GEOMETRY = "exact_geometry"
    SEGMENT = "segment"
    CORRIDOR = "corridor"
    PROJECT_AREA = "project_area"
    LOCALITY = "locality"
    ADMIN_UNIT = "admin_unit"
    REGIONAL = "regional"
    CONTEXTUAL = "contextual"
    UNKNOWN = "unknown"


class RelationBasis(StrEnum):
    OFFICIAL_GEOMETRY = "official_geometry"
    PROJECT_GEOMETRY = "project_geometry"
    KNOWN_ROUTE = "known_route"
    USER_DECLARED = "user_declared"
    GEOCODED = "geocoded"
    INFERRED_CONTEXT = "inferred_context"
    UNKNOWN = "unknown"


def _enum_value(enum_type: type[StrEnum], value: Any, field: str) -> StrEnum:
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
class ResearchIntent:
    contract_version: str
    intent_id: str
    question_raw: str
    question_canonical: str
    question_profile_ref: str | None
    domain: ResearchDomain
    activity: ResearchActivity
    goal: str
    constraints: tuple[str, ...]
    territory_hint: str | None
    created_at: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ResearchIntent":
        required = {
            "contract_version",
            "intent_id",
            "question_raw",
            "question_canonical",
            "domain",
            "activity",
            "goal",
            "constraints",
            "created_at",
        }
        allowed = required | {"question_profile_ref", "territory_hint"}
        require_fields(payload, required=required, allowed=allowed)

        contract_version = require_text(payload["contract_version"], "contract_version")
        if contract_version != CONTRACT_VERSION:
            raise ValueError(f"contract_version must be {CONTRACT_VERSION}")

        question_raw = payload["question_raw"]
        require_text(question_raw, "question_raw")

        return cls(
            contract_version=contract_version,
            intent_id=require_text(payload["intent_id"], "intent_id"),
            question_raw=question_raw,
            question_canonical=require_text(payload["question_canonical"], "question_canonical"),
            question_profile_ref=_optional_text(payload.get("question_profile_ref"), "question_profile_ref"),
            domain=_enum_value(ResearchDomain, payload["domain"], "domain"),
            activity=_enum_value(ResearchActivity, payload["activity"], "activity"),
            goal=require_text(payload["goal"], "goal"),
            constraints=require_string_list(payload["constraints"], "constraints"),
            territory_hint=_optional_text(payload.get("territory_hint"), "territory_hint"),
            created_at=require_aware_iso8601(payload["created_at"], "created_at"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "intent_id": self.intent_id,
            "question_raw": self.question_raw,
            "question_canonical": self.question_canonical,
            "question_profile_ref": self.question_profile_ref,
            "domain": self.domain.value,
            "activity": self.activity.value,
            "goal": self.goal,
            "constraints": list(self.constraints),
            "territory_hint": self.territory_hint,
            "created_at": self.created_at,
        }


@dataclass(frozen=True, slots=True)
class AdminUnit:
    country_code: str
    admin_level: str
    official_code: str | None
    name: str
    source_id: str | None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AdminUnit":
        required = {"country_code", "admin_level", "name"}
        allowed = required | {"official_code", "source_id"}
        require_fields(payload, required=required, allowed=allowed)
        return cls(
            country_code=require_text(payload["country_code"], "country_code"),
            admin_level=require_text(payload["admin_level"], "admin_level"),
            official_code=_optional_text(payload.get("official_code"), "official_code"),
            name=require_text(payload["name"], "name"),
            source_id=_optional_text(payload.get("source_id"), "source_id"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "country_code": self.country_code,
            "admin_level": self.admin_level,
            "official_code": self.official_code,
            "name": self.name,
            "source_id": self.source_id,
        }


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be a finite number")
    return number


@dataclass(frozen=True, slots=True)
class BBox:
    west: float
    south: float
    east: float
    north: float

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "BBox":
        fields = {"west", "south", "east", "north"}
        require_fields(payload, required=fields, allowed=fields)

        west = _finite_number(payload["west"], "west")
        south = _finite_number(payload["south"], "south")
        east = _finite_number(payload["east"], "east")
        north = _finite_number(payload["north"], "north")

        for field, value in (("west", west), ("east", east)):
            if value < -180 or value > 180:
                raise ValueError(f"{field} must be between -180 and 180")
        for field, value in (("south", south), ("north", north)):
            if value < -90 or value > 90:
                raise ValueError(f"{field} must be between -90 and 90")

        if west >= east:
            raise ValueError("west must be < east")
        if south >= north:
            raise ValueError("south must be < north")
        if east - west > 180:
            raise ValueError("antimeridian-crossing bbox is unsupported in V0")

        return cls(west=west, south=south, east=east, north=north)

    def to_dict(self) -> dict[str, float]:
        return {
            "west": self.west,
            "south": self.south,
            "east": self.east,
            "north": self.north,
        }


@dataclass(frozen=True, slots=True)
class TerritorialScope:
    contract_version: str
    scope_id: str
    countries: tuple[str, ...]
    admin_units: tuple[AdminUnit, ...]
    project_refs: tuple[str, ...]
    corridor_refs: tuple[str, ...]
    segment_refs: tuple[str, ...]
    bbox: BBox | None
    geometry_ref: str | None
    crs: str | None
    precision: ScopePrecision
    relation_basis: RelationBasis
    notes: tuple[str, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TerritorialScope":
        fields = {
            "contract_version",
            "scope_id",
            "countries",
            "admin_units",
            "project_refs",
            "corridor_refs",
            "segment_refs",
            "bbox",
            "geometry_ref",
            "crs",
            "precision",
            "relation_basis",
            "notes",
        }
        require_fields(payload, required=fields, allowed=fields)

        contract_version = require_text(payload["contract_version"], "contract_version")
        if contract_version != CONTRACT_VERSION:
            raise ValueError(f"contract_version must be {CONTRACT_VERSION}")

        if not isinstance(payload["admin_units"], list):
            raise ValueError("admin_units must be a list")
        admin_units = tuple(AdminUnit.from_dict(item) for item in payload["admin_units"])

        bbox_value = payload["bbox"]
        if bbox_value is not None and not isinstance(bbox_value, dict):
            raise ValueError("bbox must be an object or null")
        bbox = BBox.from_dict(bbox_value) if bbox_value is not None else None

        countries = require_string_list(payload["countries"], "countries")
        project_refs = require_string_list(payload["project_refs"], "project_refs")
        corridor_refs = require_string_list(payload["corridor_refs"], "corridor_refs")
        segment_refs = require_string_list(payload["segment_refs"], "segment_refs")
        geometry_ref = _optional_text(payload["geometry_ref"], "geometry_ref")

        if not (
            countries
            or admin_units
            or project_refs
            or corridor_refs
            or segment_refs
            or bbox is not None
            or geometry_ref is not None
        ):
            raise ValueError("territorial scope requires at least one territorial reference")

        return cls(
            contract_version=contract_version,
            scope_id=require_text(payload["scope_id"], "scope_id"),
            countries=countries,
            admin_units=admin_units,
            project_refs=project_refs,
            corridor_refs=corridor_refs,
            segment_refs=segment_refs,
            bbox=bbox,
            geometry_ref=geometry_ref,
            crs=_optional_text(payload["crs"], "crs"),
            precision=_enum_value(ScopePrecision, payload["precision"], "precision"),
            relation_basis=_enum_value(RelationBasis, payload["relation_basis"], "relation_basis"),
            notes=require_string_list(payload["notes"], "notes"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "scope_id": self.scope_id,
            "countries": list(self.countries),
            "admin_units": [unit.to_dict() for unit in self.admin_units],
            "project_refs": list(self.project_refs),
            "corridor_refs": list(self.corridor_refs),
            "segment_refs": list(self.segment_refs),
            "bbox": self.bbox.to_dict() if self.bbox is not None else None,
            "geometry_ref": self.geometry_ref,
            "crs": self.crs,
            "precision": self.precision.value,
            "relation_basis": self.relation_basis.value,
            "notes": list(self.notes),
        }
