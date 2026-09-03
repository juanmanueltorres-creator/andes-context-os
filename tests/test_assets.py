import pytest

from andes_context_os.assets import Actor, ActorKind, Asset, AssetType


def asset_payload(**overrides):
    payload = {
        "contract_version": "0.1",
        "asset_id": "asset:ar:li:rio-grande-noa",
        "name": "Río Grande / NOA Lithium",
        "asset_type": "mining_project",
        "commodity": "lithium",
        "territorial_scope_ref": "project:atlas-geotech:258",
        "baseline_source_id": "atlas-geotech",
        "baseline_record_ref": "project_id:258",
        "notes": ["Baseline identity only; mutable project state belongs in evidence."],
    }
    payload.update(overrides)
    return payload


def actor_payload(**overrides):
    payload = {
        "contract_version": "0.1",
        "actor_id": "actor:noa-lithium",
        "canonical_name": "NOA Lithium Brines Inc.",
        "actor_kind": "organization",
        "jurisdiction": "Canada / Argentina",
        "external_refs": ["https://www.noalithium.com/"],
        "notes": [],
    }
    payload.update(overrides)
    return payload


def test_asset_round_trip_preserves_exact_baseline_reference():
    asset = Asset.from_dict(asset_payload())
    assert asset.asset_type == AssetType.MINING_PROJECT
    assert asset.baseline_record_ref == "project_id:258"
    assert asset.to_dict() == asset_payload()


def test_asset_rejects_mutable_current_stage_field():
    with pytest.raises(ValueError, match="unknown fields: current_stage"):
        Asset.from_dict(asset_payload(current_stage="PFS"))


def test_asset_rejects_unsupported_type():
    with pytest.raises(ValueError, match="asset_type has unsupported value"):
        Asset.from_dict(asset_payload(asset_type="company"))


def test_actor_round_trip_keeps_identity_separate_from_role():
    actor = Actor.from_dict(actor_payload())
    assert actor.actor_kind == ActorKind.ORGANIZATION
    assert "role" not in actor.to_dict()
    assert actor.to_dict() == actor_payload()


def test_actor_rejects_role_field():
    with pytest.raises(ValueError, match="unknown fields: role"):
        Actor.from_dict(actor_payload(role="contractor"))
