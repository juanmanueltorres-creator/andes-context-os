from copy import deepcopy

import pytest

from andes_context_os.registry import SourceRegistry
from andes_context_os.runs import DiscoveryRun, validate_run_against_registry


@pytest.fixture
def registry():
    return SourceRegistry.load("data/source_registry.v0.1.json")


@pytest.fixture
def valid_run_payload(registry):
    registry_hash = registry.registry_hash
    return {
        "contract_version": "0.1",
        "run_id": "run-agua-negra-001",
        "research_intent": {
            "contract_version": "0.1",
            "intent_id": "intent-agua-negra-001",
            "question_raw": "¿Qué datos públicos y señales humanas pueden ayudar a investigar degradación operacional en un corredor minero de altura?",
            "question_canonical": "¿Qué evidencia pública y señales humanas pueden ayudar a investigar degradación operacional en un corredor minero de alta montaña?",
            "question_profile_ref": "question-radar:profile-001",
            "domain": "logistics",
            "activity": "access",
            "goal": "identify evidence candidates and missing context",
            "constraints": ["research only", "no operational authorization"],
            "territory_hint": "San Juan Andes",
            "created_at": "2026-08-30T09:00:00-03:00",
        },
        "territorial_scope": {
            "contract_version": "0.1",
            "scope_id": "scope-agua-negra-001",
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
            "corridor_refs": ["agua-negra-v1"],
            "segment_refs": [],
            "bbox": None,
            "geometry_ref": None,
            "crs": None,
            "precision": "corridor",
            "relation_basis": "known_route",
            "notes": ["Benchmark research scope"],
        },
        "generated_at": "2026-08-30T09:20:00-03:00",
        "source_registry_version": registry.registry_version,
        "source_registry_hash": registry_hash,
        "adapter_versions": {
            "official_geo_service": "0.1",
            "public_human_signal": "0.1",
        },
        "source_observations": [
            {
                "contract_version": "0.1",
                "observation_id": "obs-cadastre-001",
                "source_id": "ar_sanjuan_mining_cadastre",
                "observed_at": "2026-08-30T09:10:00-03:00",
                "status": "available",
                "method": "adapter_query",
                "adapter_key": "official_geo_service",
                "adapter_version": "0.1",
                "response_metadata": {
                    "http_status": 200,
                    "content_type": "application/json",
                    "record_count": 3,
                    "elapsed_ms": 52,
                },
                "freshness_observation": None,
                "errors": [],
                "notes": [],
            },
            {
                "contract_version": "0.1",
                "observation_id": "obs-copernicus-001",
                "source_id": "eu_copernicus_dem",
                "observed_at": "2026-08-30T09:11:00-03:00",
                "status": "unavailable",
                "method": "adapter_query",
                "adapter_key": "copernicus_source",
                "adapter_version": "0.1",
                "response_metadata": None,
                "freshness_observation": None,
                "errors": ["source not queried in benchmark environment"],
                "notes": [],
            },
        ],
        "candidate_refs": ["candidate-public-road-context-001"],
        "contradictions": [],
        "missing_context": ["current field-observed road condition"],
        "warnings": ["Research run only; not an operational authorization"],
        "omitted_sources": ["reddit_public"],
        "run_status": "partial",
        "recommended_action": "research",
        "recommended_action_reason": "Corroborate route condition with current official and field evidence.",
        "lineage": {
            "question_profile_ref": "question-radar:profile-001",
            "internal_snapshot_ref": "geoplatform:agua-negra-v1",
            "source_registry_hash": registry_hash,
            "input_refs": ["corridor:agua-negra-v1"],
            "supersedes_run_id": None,
        },
    }


def test_partial_run_is_valid_when_optional_source_is_unavailable(valid_run_payload):
    run = DiscoveryRun.from_dict(valid_run_payload)
    assert run.run_status.value == "partial"
    assert run.source_observations[1].status.value == "unavailable"


def test_recommended_action_requires_reason(valid_run_payload):
    payload = {**valid_run_payload, "recommended_action_reason": ""}
    with pytest.raises(ValueError, match="recommended_action_reason"):
        DiscoveryRun.from_dict(payload)


@pytest.mark.parametrize(
    "field",
    ["safe_to_travel", "road_open", "route_authorized", "community_approved", "risk_low"],
)
def test_operational_authorization_fields_are_rejected(valid_run_payload, field):
    payload = {**valid_run_payload, field: True}
    with pytest.raises(ValueError, match=f"unknown fields: {field}"):
        DiscoveryRun.from_dict(payload)


def test_registry_hash_must_match(valid_run_payload, registry):
    run = DiscoveryRun.from_dict({**valid_run_payload, "source_registry_hash": "0" * 64})
    with pytest.raises(ValueError, match="registry hash mismatch"):
        validate_run_against_registry(run, registry)


def test_registry_version_must_match(valid_run_payload, registry):
    run = DiscoveryRun.from_dict({**valid_run_payload, "source_registry_version": "9.9"})
    with pytest.raises(ValueError, match="registry version mismatch"):
        validate_run_against_registry(run, registry)


def test_lineage_registry_hash_must_match_top_level(valid_run_payload, registry):
    payload = deepcopy(valid_run_payload)
    payload["lineage"]["source_registry_hash"] = "0" * 64
    run = DiscoveryRun.from_dict(payload)
    with pytest.raises(ValueError, match="lineage source_registry_hash"):
        validate_run_against_registry(run, registry)


def test_source_registry_hash_requires_lowercase_64_hex(valid_run_payload):
    with pytest.raises(ValueError, match="64 lowercase hex"):
        DiscoveryRun.from_dict({**valid_run_payload, "source_registry_hash": "A" * 64})


def test_generated_at_requires_timezone(valid_run_payload):
    with pytest.raises(ValueError, match="timezone-aware"):
        DiscoveryRun.from_dict({**valid_run_payload, "generated_at": "2026-08-30T09:20:00"})


def test_contract_version_is_strict(valid_run_payload):
    with pytest.raises(ValueError, match="contract_version must be 0.1"):
        DiscoveryRun.from_dict({**valid_run_payload, "contract_version": "0.2"})


def test_adapter_versions_require_non_empty_string_keys_and_values(valid_run_payload):
    with pytest.raises(ValueError, match="adapter_versions"):
        DiscoveryRun.from_dict({**valid_run_payload, "adapter_versions": {"": "0.1"}})
    with pytest.raises(ValueError, match="adapter_versions"):
        DiscoveryRun.from_dict({**valid_run_payload, "adapter_versions": {"official_geo_service": ""}})


def test_run_hash_is_lowercase_sha256(valid_run_payload):
    run = DiscoveryRun.from_dict(valid_run_payload)
    assert len(run.run_hash) == 64
    assert run.run_hash == run.run_hash.lower()
    int(run.run_hash, 16)


def test_run_hash_changes_for_meaningful_change(valid_run_payload):
    first = DiscoveryRun.from_dict(valid_run_payload)
    changed = deepcopy(valid_run_payload)
    changed["missing_context"].append("measured segment speed")
    second = DiscoveryRun.from_dict(changed)
    assert first.run_hash != second.run_hash


def test_run_hash_ignores_supplied_matching_run_hash_field(valid_run_payload):
    first = DiscoveryRun.from_dict(valid_run_payload)
    payload = deepcopy(valid_run_payload)
    payload["lineage"]["run_hash"] = first.run_hash
    second = DiscoveryRun.from_dict(payload)
    assert second.run_hash == first.run_hash


def test_supplied_wrong_run_hash_is_rejected(valid_run_payload):
    payload = deepcopy(valid_run_payload)
    payload["lineage"]["run_hash"] = "0" * 64
    with pytest.raises(ValueError, match="run_hash mismatch"):
        DiscoveryRun.from_dict(payload)


def test_to_dict_emits_computed_run_hash_in_lineage(valid_run_payload):
    run = DiscoveryRun.from_dict(valid_run_payload)
    payload = run.to_dict()
    assert payload["lineage"]["run_hash"] == run.run_hash


def test_run_collections_are_immutable_tuples(valid_run_payload):
    run = DiscoveryRun.from_dict(valid_run_payload)
    assert isinstance(run.candidate_refs, tuple)
    assert isinstance(run.source_observations, tuple)
    with pytest.raises(AttributeError):
        run.run_id = "changed"


def test_validate_run_against_registry_accepts_matching_registry(valid_run_payload, registry):
    run = DiscoveryRun.from_dict(valid_run_payload)
    validate_run_against_registry(run, registry)
