from pathlib import Path

import pytest

from andes_context_os.asset_movement_benchmark import (
    canonical_asset_movement_projection,
    load_asset_movement_evidence_fixture,
    load_asset_movement_fixture,
    validate_asset_movement_benchmark,
)
from andes_context_os.movements import Movement
from andes_context_os.opportunities import OpportunityHypothesis

DOGFOOD = Path("data/dogfood/argentina-lithium")
PUBLIC_EVIDENCE = load_asset_movement_evidence_fixture(DOGFOOD)


def load_valid_objects():
    return load_asset_movement_fixture(DOGFOOD)


def test_research_loop_dogfood_persists_followup_state():
    assets, actors, movements, hypotheses = load_valid_objects()
    evidence_candidates = load_asset_movement_evidence_fixture(DOGFOOD)

    validate_asset_movement_benchmark(
        assets=assets,
        actors=actors,
        movements=movements,
        evidence_candidates=evidence_candidates,
        opportunity_hypotheses=hypotheses,
    )

    evidence_ids = {item.candidate_id for item in evidence_candidates}
    assert {
        "evidence:rg:noa:2026-05-12:hidrotec-framework",
        "evidence:rg:noa:2026-06-16:hatch-arrangement",
        "evidence:rg:noa:2026-07-16:drilling-progress",
        "evidence:co:lar:2026-08-11:ganfeng-equipment",
    } <= evidence_ids

    assert "actor:hatch" in {item.actor_id for item in actors}
    assert {
        "movement:rg:contractor:2026-05-12",
        "movement:rg:consulting:2026-06-16",
        "movement:rg:drilling:2026-07-16",
    } <= {item.movement_id for item in movements}

    hypothesis_map = {item.hypothesis_id: item for item in hypotheses}
    rio_grande = hypothesis_map["opportunity:rg:external-field-services"]
    assert rio_grande.status.value == "researching"
    assert {
        "evidence:rg:noa:2026-05-12:hidrotec-framework",
        "evidence:rg:noa:2026-06-16:hatch-arrangement",
        "evidence:rg:noa:2026-07-16:drilling-progress",
    } <= set(rio_grande.supporting_evidence_refs)
    assert "Current supplier roster." not in rio_grande.missing_context

    cauchari = hypothesis_map["opportunity:co:stage2-supplier-scope"]
    assert cauchari.status.value == "researching"
    assert "evidence:co:lar:2026-08-11:ganfeng-equipment" in cauchari.supporting_evidence_refs

    assert "opportunity:hmw:ramp-up-support" in hypothesis_map


def test_hmw_second_research_pass_narrows_without_auto_support():
    assets, actors, movements, hypotheses = load_valid_objects()
    evidence_candidates = load_asset_movement_evidence_fixture(DOGFOOD)

    validate_asset_movement_benchmark(
        assets=assets,
        actors=actors,
        movements=movements,
        evidence_candidates=evidence_candidates,
        opportunity_hypotheses=hypotheses,
    )

    assert "actor:authium" in {item.actor_id for item in actors}
    assert "evidence:hmw:authium:operating-offtake" in {
        item.candidate_id for item in evidence_candidates
    }
    assert "movement:hmw:partnership:authium" in {
        item.movement_id for item in movements
    }

    hmw = {
        item.hypothesis_id: item for item in hypotheses
    }["opportunity:hmw:ramp-up-support"]
    assert hmw.status.value == "researching"
    assert "evidence:hmw:authium:operating-offtake" in hmw.supporting_evidence_refs
    assert "Current operating contractor model." not in hmw.missing_context
    assert hmw.reviewed_at is None


def test_validator_accepts_resolved_three_asset_benchmark():
    assets, actors, movements, hypotheses = load_valid_objects()
    validate_asset_movement_benchmark(
        assets=assets,
        actors=actors,
        movements=movements,
        evidence_candidates=PUBLIC_EVIDENCE,
        opportunity_hypotheses=hypotheses,
    )


def test_validator_rejects_missing_actor_reference():
    assets, actors, movements, hypotheses = load_valid_objects()
    bad = Movement.from_dict({
        **movements[0].to_dict(),
        "actor_refs": [{"actor_id": "actor:missing", "role": "operator", "notes": []}],
    })
    with pytest.raises(ValueError, match="unknown actor_id: actor:missing"):
        validate_asset_movement_benchmark(
            assets=assets,
            actors=actors,
            movements=(bad, *movements[1:]),
            evidence_candidates=PUBLIC_EVIDENCE,
            opportunity_hypotheses=hypotheses,
        )


def test_validator_rejects_same_asset_violation():
    assets, actors, movements, hypotheses = load_valid_objects()
    bad = OpportunityHypothesis.from_dict({
        **hypotheses[0].to_dict(),
        "asset_id": "asset:ar:li:cauchari-olaroz",
    })
    with pytest.raises(ValueError, match="trigger movement belongs to different asset"):
        validate_asset_movement_benchmark(
            assets=assets,
            actors=actors,
            movements=movements,
            evidence_candidates=PUBLIC_EVIDENCE,
            opportunity_hypotheses=(bad, *hypotheses[1:]),
        )


def test_supported_hypothesis_requires_evidence_beyond_trigger_evidence():
    assets, actors, movements, hypotheses = load_valid_objects()
    first = hypotheses[0]
    trigger_evidence = movements[0].evidence_candidate_refs[0]
    supported = OpportunityHypothesis.from_dict({
        **first.to_dict(),
        "supporting_evidence_refs": [trigger_evidence],
        "status": "supported",
        "reviewed_at": "2026-09-02T22:20:00-03:00",
    })
    with pytest.raises(ValueError, match="supported hypothesis requires evidence beyond trigger movement evidence"):
        validate_asset_movement_benchmark(
            assets=assets,
            actors=actors,
            movements=movements,
            evidence_candidates=PUBLIC_EVIDENCE,
            opportunity_hypotheses=(supported, *hypotheses[1:]),
        )


def test_canonical_projection_is_deterministic_for_explicit_collections():
    assets, actors, movements, hypotheses = load_valid_objects()
    first = canonical_asset_movement_projection(
        assets=assets,
        actors=actors,
        movements=movements,
        opportunity_hypotheses=hypotheses,
    )
    second = canonical_asset_movement_projection(
        assets=tuple(reversed(assets)),
        actors=tuple(reversed(actors)),
        movements=tuple(reversed(movements)),
        opportunity_hypotheses=tuple(reversed(hypotheses)),
    )
    assert first == second


def test_dogfood_uses_exact_atlas_baseline_records():
    assets, _, _, _ = load_asset_movement_fixture(DOGFOOD)
    assert {item.asset_id: item.baseline_record_ref for item in assets} == {
        "asset:ar:li:rio-grande-noa": "project_id:258",
        "asset:ar:li:hombre-muerto-oeste": "project_id:137",
        "asset:ar:li:cauchari-olaroz": "project_id:52",
    }


def test_every_movement_has_evidence_and_every_hypothesis_has_trigger():
    _, _, movements, hypotheses = load_asset_movement_fixture(DOGFOOD)
    assert all(item.evidence_candidate_refs for item in movements)
    assert all(item.trigger_movement_refs for item in hypotheses)


def test_v04_dogfood_files_do_not_contain_private_or_action_fields():
    banned = {
        "email",
        "gmail",
        "apollo",
        "phone",
        "contact_name",
        "send_request",
        "approved_to_send",
        "route_authorized",
        "safe_to_travel",
        "community_approved",
    }
    for path in DOGFOOD.glob("*.json"):
        text = path.read_text(encoding="utf-8").lower()
        assert all(term not in text for term in banned)


def test_pyproject_keeps_runtime_dependencies_empty():
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "dependencies = []" in text


def test_readme_describes_v04_as_experimental_dogfood():
    text = Path("README.md").read_text(encoding="utf-8")
    assert "## V0.4 experimental asset-movement dogfood" in text
    assert "movement != opportunity" in text
    assert "opportunity hypothesis != confirmed demand" in text
    assert "does not add live scraping" in text
