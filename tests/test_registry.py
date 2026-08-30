from pathlib import Path
import json

import pytest

from andes_context_os.registry import SourceRegistry

SEED = Path("data/source_registry.v0.1.json")
EXPECTED_IDS = {
    "ar_segemar_sigam",
    "ar_siacam",
    "ar_sanjuan_mining_cadastre",
    "ar_dnv_routes",
    "ar_ign_admin",
    "osm_global",
    "cl_sernageomin",
    "pe_ingemmet_geocatmin",
    "eu_copernicus_dem",
    "research_automine",
    "research_ampilot",
    "reddit_public",
}


def test_seed_registry_loads():
    registry = SourceRegistry.load(SEED)
    assert registry.registry_version == "0.1"
    assert {source.source_id for source in registry.sources} == EXPECTED_IDS
    assert registry.get("ar_sanjuan_mining_cadastre").source_id == "ar_sanjuan_mining_cadastre"


def test_registry_hash_is_deterministic():
    first = SourceRegistry.load(SEED)
    second = SourceRegistry.load(SEED)
    assert first.registry_hash == second.registry_hash


def test_registry_hash_ignores_source_array_order():
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    reordered = {**seed, "sources": list(reversed(seed["sources"]))}
    assert SourceRegistry.from_dict(seed).registry_hash == SourceRegistry.from_dict(reordered).registry_hash


def test_registry_hash_changes_for_meaningful_metadata_change():
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    changed = json.loads(json.dumps(seed))
    changed["sources"][0]["display_name"] += " updated"
    assert SourceRegistry.from_dict(seed).registry_hash != SourceRegistry.from_dict(changed).registry_hash


def test_registry_hash_excludes_generated_at():
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    later = {**seed, "generated_at": "2026-08-31T03:50:00-03:00"}
    assert SourceRegistry.from_dict(seed).registry_hash == SourceRegistry.from_dict(later).registry_hash


def test_registry_rejects_duplicate_source_ids(tmp_path):
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    seed["sources"].append(seed["sources"][0])
    path = tmp_path / "duplicate.json"
    path.write_text(json.dumps(seed), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate source_id"):
        SourceRegistry.load(path)


def test_registry_rejects_unknown_registry_version():
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="registry_version must be 0.1"):
        SourceRegistry.from_dict({**seed, "registry_version": "9.9"})


def test_registry_rejects_naive_generated_at():
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="timezone-aware"):
        SourceRegistry.from_dict({**seed, "generated_at": "2026-08-30T03:50:00"})


def test_registry_rejects_malformed_source():
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    malformed = json.loads(json.dumps(seed))
    malformed["sources"][0]["declared_status"] = "available"
    with pytest.raises(ValueError, match="declared_status"):
        SourceRegistry.from_dict(malformed)


def test_registry_get_missing_source_raises_key_error():
    registry = SourceRegistry.load(SEED)
    with pytest.raises(KeyError, match="missing"):
        registry.get("missing")


def test_seed_rights_are_conservative():
    registry = SourceRegistry.load(SEED)

    san_juan = registry.get("ar_sanjuan_mining_cadastre")
    assert san_juan.access.access_type.value == "wfs"
    assert san_juan.rights.license_status.value == "unknown_review_required"
    assert san_juan.rights.commercial_reuse.value == "unknown"
    assert san_juan.rights.redistribution.value == "unknown"

    osm = registry.get("osm_global")
    assert osm.rights.license_name == "ODbL"
    assert osm.rights.license_status.value == "verified_open"
    assert osm.rights.commercial_reuse.value == "yes"
    assert osm.rights.redistribution.value == "conditional"
    assert osm.rights.attribution_required is True

    for source_id in ("research_automine", "research_ampilot"):
        source = registry.get(source_id)
        assert source.source_kind.value == "reference_only"
        assert source.rights.license_status.value == "reference_only"
        assert source.rights.commercial_reuse.value == "no"
        assert source.rights.redistribution.value == "no"

    reddit = registry.get("reddit_public")
    assert reddit.source_kind.value == "public_human_platform"
    assert reddit.authority.value == "community_source"
    assert reddit.rights.license_status.value == "unknown_review_required"
    assert "public visibility does not imply bulk reuse permission" in reddit.limitations


def test_seed_declared_status_never_claims_runtime_availability():
    registry = SourceRegistry.load(SEED)
    assert all(source.declared_status.value == "candidate" for source in registry.sources)
    assert all(source.declared_status.value != "available" for source in registry.sources)


def test_registry_round_trip_preserves_hash():
    registry = SourceRegistry.load(SEED)
    round_tripped = SourceRegistry.from_dict(registry.to_dict())
    assert round_tripped.registry_hash == registry.registry_hash
