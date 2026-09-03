from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Iterable, TypeVar

from andes_context_os.assets import Actor, Asset
from andes_context_os.evidence import EvidenceCandidate
from andes_context_os.movements import Movement, MovementReviewState
from andes_context_os.opportunities import OpportunityHypothesis, OpportunityStatus

T = TypeVar("T")


def _load_array(path: Path, parser: Callable[[dict[str, Any]], T]) -> tuple[T, ...]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"{path.name} must contain a JSON array")
    result: list[T] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"{path.name}[{index}] must be an object")
        result.append(parser(item))
    return tuple(result)


def _unique_map(items: Iterable[T], id_attr: str, label: str) -> dict[str, T]:
    result: dict[str, T] = {}
    for item in items:
        item_id = getattr(item, id_attr)
        if item_id in result:
            raise ValueError(f"duplicate {label} id: {item_id}")
        result[item_id] = item
    return result


def load_asset_movement_fixture(
    base_dir: str | Path,
) -> tuple[
    tuple[Asset, ...],
    tuple[Actor, ...],
    tuple[Movement, ...],
    tuple[OpportunityHypothesis, ...],
]:
    base = Path(base_dir)
    return (
        _load_array(base / "assets.json", Asset.from_dict),
        _load_array(base / "actors.json", Actor.from_dict),
        _load_array(base / "movements.json", Movement.from_dict),
        _load_array(base / "opportunity_hypotheses.json", OpportunityHypothesis.from_dict),
    )


def canonical_asset_movement_projection(
    *,
    assets: Iterable[Asset],
    actors: Iterable[Actor],
    movements: Iterable[Movement],
    opportunity_hypotheses: Iterable[OpportunityHypothesis],
) -> dict[str, list[dict[str, Any]]]:
    return {
        "assets": [item.to_dict() for item in sorted(assets, key=lambda item: item.asset_id)],
        "actors": [item.to_dict() for item in sorted(actors, key=lambda item: item.actor_id)],
        "movements": [item.to_dict() for item in sorted(movements, key=lambda item: item.movement_id)],
        "opportunity_hypotheses": [
            item.to_dict()
            for item in sorted(opportunity_hypotheses, key=lambda item: item.hypothesis_id)
        ],
    }


def validate_asset_movement_benchmark(
    *,
    assets: Iterable[Asset],
    actors: Iterable[Actor],
    movements: Iterable[Movement],
    evidence_candidates: Iterable[EvidenceCandidate],
    opportunity_hypotheses: Iterable[OpportunityHypothesis],
) -> None:
    asset_map = _unique_map(assets, "asset_id", "asset")
    actor_map = _unique_map(actors, "actor_id", "actor")
    movement_map = _unique_map(movements, "movement_id", "movement")
    evidence_map = _unique_map(evidence_candidates, "candidate_id", "evidence")
    hypothesis_map = _unique_map(opportunity_hypotheses, "hypothesis_id", "hypothesis")

    for movement in movement_map.values():
        if movement.asset_id not in asset_map:
            raise ValueError(f"unknown asset_id: {movement.asset_id}")
        for actor_ref in movement.actor_refs:
            if actor_ref.actor_id not in actor_map:
                raise ValueError(f"unknown actor_id: {actor_ref.actor_id}")
        for evidence_id in movement.evidence_candidate_refs:
            if evidence_id not in evidence_map:
                raise ValueError(f"unknown evidence_candidate_id: {evidence_id}")
        for parent_id in movement.derived_from_movement_ids:
            if parent_id == movement.movement_id:
                raise ValueError(f"movement cannot derive from itself: {movement.movement_id}")
            if parent_id not in movement_map:
                raise ValueError(f"unknown derived movement_id: {parent_id}")

    for hypothesis in hypothesis_map.values():
        if hypothesis.asset_id not in asset_map:
            raise ValueError(f"unknown asset_id: {hypothesis.asset_id}")
        for actor_id in hypothesis.actor_refs:
            if actor_id not in actor_map:
                raise ValueError(f"unknown actor_id: {actor_id}")

        trigger_movements: list[Movement] = []
        trigger_evidence: set[str] = set()
        for movement_id in hypothesis.trigger_movement_refs:
            movement = movement_map.get(movement_id)
            if movement is None:
                raise ValueError(f"unknown trigger movement_id: {movement_id}")
            if movement.asset_id != hypothesis.asset_id:
                raise ValueError(
                    f"trigger movement belongs to different asset: {movement_id}"
                )
            trigger_movements.append(movement)
            trigger_evidence.update(movement.evidence_candidate_refs)

        for evidence_id in hypothesis.supporting_evidence_refs:
            if evidence_id not in evidence_map:
                raise ValueError(f"unknown supporting evidence_id: {evidence_id}")

        if hypothesis.status == OpportunityStatus.SUPPORTED:
            additional_evidence = set(hypothesis.supporting_evidence_refs) - trigger_evidence
            if not additional_evidence:
                raise ValueError(
                    "supported hypothesis requires evidence beyond trigger movement evidence"
                )
            if trigger_movements and all(
                movement.review_state == MovementReviewState.REJECTED
                for movement in trigger_movements
            ):
                raise ValueError(
                    "supported hypothesis cannot rely only on rejected trigger movements"
                )
