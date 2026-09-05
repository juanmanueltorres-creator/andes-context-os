import math

import pytest

from andes_context_os.research import (
    BBox,
    ResearchActivity,
    ResearchIntent,
    TerritorialScope,
)

VALID_INTENT = {
    "contract_version": "0.1",
    "intent_id": "intent-filo-access-001",
    "question_raw": "¿Qué explica las demoras en un acceso minero de altura?",
    "question_canonical": "¿Qué evidencia pública puede ayudar a explicar demoras operacionales en un corredor minero de alta montaña?",
    "question_profile_ref": "question-radar:profile-001",
    "domain": "logistics",
    "activity": "access",
    "goal": "identify evidence candidates and missing context",
    "constraints": ["research only"],
    "territory_hint": "San Juan Andes",
    "created_at": "2026-08-30T09:00:00-03:00",
}

ADMIN_SCOPE = {
    "contract_version": "0.1",
    "scope_id": "scope-ar-j",
    "countries": ["AR"],
    "admin_units": [
        {
            "country_code": "AR",
            "admin_level": "1",
            "official_code": "J",
            "name": "San Juan",
            "source_id": "ar_ign_admin",
        }
    ],
    "project_refs": [],
    "corridor_refs": [],
    "segment_refs": [],
    "bbox": None,
    "geometry_ref": None,
    "crs": None,
    "precision": "admin_unit",
    "relation_basis": "official_geometry",
    "notes": [],
}


def bbox_scope(**bbox_overrides):
    bbox = {"west": -69.8, "south": -30.0, "east": -68.0, "north": -28.0}
    bbox.update(bbox_overrides)
    return {
        "contract_version": "0.1",
        "scope_id": "scope-bbox",
        "countries": ["AR"],
        "admin_units": [],
        "project_refs": [],
        "corridor_refs": [],
        "segment_refs": [],
        "bbox": bbox,
        "geometry_ref": None,
        "crs": "EPSG:4326",
        "precision": "regional",
        "relation_basis": "user_declared",
        "notes": [],
    }


def test_research_intent_preserves_raw_question():
    intent = ResearchIntent.from_dict(VALID_INTENT)
    assert intent.question_raw == VALID_INTENT["question_raw"]


def test_research_intent_round_trips():
    intent = ResearchIntent.from_dict(VALID_INTENT)
    assert intent.to_dict() == VALID_INTENT


def test_research_intent_accepts_decision_support_activity():
    payload = {**VALID_INTENT, "activity": "decision_support"}
    intent = ResearchIntent.from_dict(payload)
    assert intent.activity is ResearchActivity.DECISION_SUPPORT
    assert intent.to_dict()["activity"] == "decision_support"


def test_historical_research_activities_still_round_trip():
    historical = (
        "access",
        "haulage",
        "mobilization",
        "route_planning",
        "road_condition",
        "field_operations",
    )
    for activity in historical:
        payload = {**VALID_INTENT, "activity": activity}
        assert ResearchIntent.from_dict(payload).to_dict()["activity"] == activity


def test_research_intent_rejects_empty_question():
    with pytest.raises(ValueError, match="question_raw"):
        ResearchIntent.from_dict({**VALID_INTENT, "question_raw": "   "})


def test_research_intent_rejects_unknown_domain():
    with pytest.raises(ValueError, match="domain"):
        ResearchIntent.from_dict({**VALID_INTENT, "domain": "magic"})


def test_research_intent_rejects_unknown_activity():
    with pytest.raises(ValueError, match="activity"):
        ResearchIntent.from_dict({**VALID_INTENT, "activity": "teleportation"})


def test_research_intent_rejects_naive_created_at():
    with pytest.raises(ValueError, match="timezone-aware"):
        ResearchIntent.from_dict({**VALID_INTENT, "created_at": "2026-08-30T09:00:00"})


def test_research_intent_rejects_unknown_top_level_field():
    with pytest.raises(ValueError, match="unknown fields: conclusion"):
        ResearchIntent.from_dict({**VALID_INTENT, "conclusion": "route is safe"})


def test_scope_accepts_admin_only_scope():
    scope = TerritorialScope.from_dict(ADMIN_SCOPE)
    assert scope.scope_id == "scope-ar-j"
    assert scope.admin_units[0].official_code == "J"


def test_scope_accepts_corridor_scope():
    payload = {
        **ADMIN_SCOPE,
        "scope_id": "scope-corridor",
        "countries": [],
        "admin_units": [],
        "corridor_refs": ["agua-negra-v1"],
        "precision": "corridor",
        "relation_basis": "known_route",
    }
    scope = TerritorialScope.from_dict(payload)
    assert scope.corridor_refs == ("agua-negra-v1",)


def test_scope_accepts_bbox_scope_and_round_trips():
    payload = bbox_scope()
    scope = TerritorialScope.from_dict(payload)
    assert scope.bbox == BBox(west=-69.8, south=-30.0, east=-68.0, north=-28.0)
    assert scope.to_dict() == payload


def test_scope_rejects_west_greater_or_equal_east():
    with pytest.raises(ValueError, match="west must be < east"):
        TerritorialScope.from_dict(bbox_scope(west=-68.0, east=-69.0))


def test_scope_rejects_south_greater_or_equal_north():
    with pytest.raises(ValueError, match="south must be < north"):
        TerritorialScope.from_dict(bbox_scope(south=-27.0, north=-28.0))


def test_scope_rejects_invalid_latitude():
    with pytest.raises(ValueError, match="south must be between -90 and 90"):
        TerritorialScope.from_dict(bbox_scope(south=-91.0))


def test_scope_rejects_invalid_longitude():
    with pytest.raises(ValueError, match="west must be between -180 and 180"):
        TerritorialScope.from_dict(bbox_scope(west=-181.0))


def test_bbox_rejects_boolean_coordinate():
    with pytest.raises(ValueError, match="west must be a finite number"):
        BBox.from_dict({"west": True, "south": -30.0, "east": -68.0, "north": -28.0})


def test_bbox_rejects_non_finite_coordinate():
    with pytest.raises(ValueError, match="west must be a finite number"):
        BBox.from_dict({"west": math.nan, "south": -30.0, "east": -68.0, "north": -28.0})


def test_scope_rejects_empty_scope():
    payload = {
        "contract_version": "0.1",
        "scope_id": "scope-empty",
        "countries": [],
        "admin_units": [],
        "project_refs": [],
        "corridor_refs": [],
        "segment_refs": [],
        "bbox": None,
        "geometry_ref": None,
        "crs": None,
        "precision": "unknown",
        "relation_basis": "unknown",
        "notes": [],
    }
    with pytest.raises(ValueError, match="at least one territorial reference"):
        TerritorialScope.from_dict(payload)


def test_scope_rejects_antimeridian_crossing_semantics_in_v0():
    with pytest.raises(ValueError, match="antimeridian"):
        TerritorialScope.from_dict(bbox_scope(west=-170.0, east=170.0))


def test_scope_rejects_unknown_precision():
    with pytest.raises(ValueError, match="precision"):
        TerritorialScope.from_dict({**ADMIN_SCOPE, "precision": "pixel"})


def test_scope_rejects_unknown_relation_basis():
    with pytest.raises(ValueError, match="relation_basis"):
        TerritorialScope.from_dict({**ADMIN_SCOPE, "relation_basis": "guessed"})


def test_scope_rejects_unknown_top_level_field():
    with pytest.raises(ValueError, match="unknown fields: risk"):
        TerritorialScope.from_dict({**ADMIN_SCOPE, "risk": "low"})


def test_admin_unit_rejects_unknown_field():
    payload = {
        **ADMIN_SCOPE,
        "admin_units": [{**ADMIN_SCOPE["admin_units"][0], "population": 999}],
    }
    with pytest.raises(ValueError, match="unknown fields: population"):
        TerritorialScope.from_dict(payload)
