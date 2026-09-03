# Andes Context OS V0.4 — Asset Movement Dogfood Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, evidence-linked asset-movement layer that can represent three Argentine lithium dogfood cases while keeping observed movements, actor participation and opportunity hypotheses strictly separate.

**Architecture:** Keep the existing research/evidence contracts unchanged. Add focused stdlib-only modules for stable asset/actor identity, evidence-linked movements, explicit opportunity hypotheses, and a cross-object benchmark validator; checked-in public fixtures seed Río Grande, Hombre Muerto Oeste and Cauchari-Olaroz from exact Atlas Geotech baseline references and use explicitly identified public evidence IDs in integration tests.

**Tech Stack:** Python 3.11+, stdlib (`dataclasses`, `enum`, `json`, `pathlib`, `typing`), pytest 8.x. Runtime dependencies remain empty.

**Spec:** `docs/superpowers/specs/2026-09-02-andes-context-os-v0.4-asset-movement-dogfood-design.md`

## Global Constraints

- Repository feature milestone is `V0.4`; payload `contract_version` remains exactly `"0.1"` via the existing `CONTRACT_VERSION` constant.
- Python remains `>=3.11`; production `dependencies = []` remains unchanged.
- Reuse `ResearchIntent`, `TerritorialScope`, `SourceRegistry`, `SourceRuntimeObservation`, `EvidenceCandidate`, `EvidenceQualityVector`, `DiscoveryRun`, `InternalContextRecord` and `InternalContextSnapshot` unchanged.
- `baseline record != current state`; `signal != fact`; `evidence candidate != movement`; `movement != opportunity`; `actor proximity != relationship`; `opportunity hypothesis != demand`.
- Atlas Geotech is an exact baseline reference only. No runtime import, R/Shiny dependency, HTTP call or sibling-repository coupling is added.
- No HTTP client, GitHub client, web scraper, Reddit scraper, database, LLM SDK, embeddings, graph database, FastAPI, React, MCP, n8n, contact discovery, outreach, RFQ/RFI, ranking or commercial scoring.
- Actor identity is stable; actor role is movement-local.
- A `Movement` requires at least one existing `EvidenceCandidate` reference and never mutates evidence quality or review semantics.
- An `OpportunityHypothesis` is explicitly hypothetical. `supported` requires at least one evidence reference beyond all evidence used by its trigger movements.
- No generic `Relationship` object in V0.4.
- Unknown fields and unsupported enum values fail closed with `ValueError`.
- Timestamps use the existing `require_aware_iso8601()` helper.
- Public dogfood data must contain no private contacts, Gmail bodies, Apollo payloads, vault content, guessed emails, secrets, operational authorization claims or copied article bodies.

## File Structure

- Create `src/andes_context_os/assets.py` — `AssetType`, `Asset`, `ActorKind`, `Actor` contracts only.
- Create `src/andes_context_os/movements.py` — movement-local actor roles and `Movement` contract only.
- Create `src/andes_context_os/opportunities.py` — `OpportunityStatus` and `OpportunityHypothesis` only.
- Create `src/andes_context_os/asset_movement_benchmark.py` — JSON fixture loaders, deterministic canonical projection, and explicit cross-object validator.
- Create `tests/test_assets.py` — asset and actor contract tests.
- Create `tests/test_movements.py` — movement and opportunity local-contract tests.
- Create `tests/test_asset_movement_benchmark.py` — cross-object validation, public source-backed evidence fixtures, deterministic serialization and three-asset dogfood integration.
- Create `data/dogfood/argentina-lithium/assets.json` — three exact Atlas Geotech baseline anchors.
- Create `data/dogfood/argentina-lithium/actors.json` — only actors explicitly used by benchmark movements/hypotheses.
- Create `data/dogfood/argentina-lithium/movements.json` — evidence-ID-linked reviewed movement interpretations.
- Create `data/dogfood/argentina-lithium/opportunity_hypotheses.json` — conservative `proposed` hypotheses with assumptions and missing context explicit.
- Modify `README.md` — describe V0.4 as experimental dogfood, not a proven market-intelligence product.
- Do not modify `src/andes_context_os/evidence.py`, `src/andes_context_os/research.py`, `src/andes_context_os/runs.py`, `src/andes_context_os/sources.py`, or existing internal-context modules.

---

### Task 1: Asset and Actor Identity Contracts

**Files:**
- Create: `src/andes_context_os/assets.py`
- Create: `tests/test_assets.py`

**Interfaces:**
- Consumes: `CONTRACT_VERSION`, `require_fields()`, `require_string_list()`, `require_text()` from `andes_context_os.common`.
- Produces:
  - `AssetType(StrEnum)` with `MINING_PROJECT = "mining_project"`.
  - `Asset.from_dict(payload: dict[str, Any]) -> Asset` / `Asset.to_dict() -> dict[str, Any]`.
  - `ActorKind(StrEnum)` with `ORGANIZATION`, `GOVERNMENT_BODY`, `PERSON`, `COMMUNITY`, `OTHER`.
  - `Actor.from_dict(payload: dict[str, Any]) -> Actor` / `Actor.to_dict() -> dict[str, Any]`.

- [ ] **Step 1: Write RED asset/actor tests**

Create `tests/test_assets.py`:

```python
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
```

- [ ] **Step 2: Run RED**

```bash
pytest -q tests/test_assets.py
```

Expected: collection/import failure because `andes_context_os.assets` does not exist.

- [ ] **Step 3: Implement minimal strict contracts**

Create `src/andes_context_os/assets.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from andes_context_os.common import (
    CONTRACT_VERSION,
    require_fields,
    require_string_list,
    require_text,
)


class AssetType(StrEnum):
    MINING_PROJECT = "mining_project"


class ActorKind(StrEnum):
    ORGANIZATION = "organization"
    GOVERNMENT_BODY = "government_body"
    PERSON = "person"
    COMMUNITY = "community"
    OTHER = "other"


def _enum_value(enum_type: type[StrEnum], value: Any, field: str) -> StrEnum:
    text = require_text(value, field)
    try:
        return enum_type(text)
    except ValueError as exc:
        raise ValueError(f"{field} has unsupported value: {text}") from exc


def _optional_text(value: Any, field: str) -> str | None:
    return None if value is None else require_text(value, field)


@dataclass(frozen=True, slots=True)
class Asset:
    contract_version: str
    asset_id: str
    name: str
    asset_type: AssetType
    commodity: str
    territorial_scope_ref: str
    baseline_source_id: str
    baseline_record_ref: str
    notes: tuple[str, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Asset":
        fields = {
            "contract_version", "asset_id", "name", "asset_type", "commodity",
            "territorial_scope_ref", "baseline_source_id", "baseline_record_ref", "notes",
        }
        require_fields(payload, required=fields, allowed=fields)
        version = require_text(payload["contract_version"], "contract_version")
        if version != CONTRACT_VERSION:
            raise ValueError(f"contract_version must be {CONTRACT_VERSION}")
        return cls(
            version,
            require_text(payload["asset_id"], "asset_id"),
            require_text(payload["name"], "name"),
            _enum_value(AssetType, payload["asset_type"], "asset_type"),
            require_text(payload["commodity"], "commodity"),
            require_text(payload["territorial_scope_ref"], "territorial_scope_ref"),
            require_text(payload["baseline_source_id"], "baseline_source_id"),
            require_text(payload["baseline_record_ref"], "baseline_record_ref"),
            require_string_list(payload["notes"], "notes"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "asset_id": self.asset_id,
            "name": self.name,
            "asset_type": self.asset_type.value,
            "commodity": self.commodity,
            "territorial_scope_ref": self.territorial_scope_ref,
            "baseline_source_id": self.baseline_source_id,
            "baseline_record_ref": self.baseline_record_ref,
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class Actor:
    contract_version: str
    actor_id: str
    canonical_name: str
    actor_kind: ActorKind
    jurisdiction: str | None
    external_refs: tuple[str, ...]
    notes: tuple[str, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Actor":
        required = {"contract_version", "actor_id", "canonical_name", "actor_kind", "external_refs", "notes"}
        allowed = required | {"jurisdiction"}
        require_fields(payload, required=required, allowed=allowed)
        version = require_text(payload["contract_version"], "contract_version")
        if version != CONTRACT_VERSION:
            raise ValueError(f"contract_version must be {CONTRACT_VERSION}")
        return cls(
            version,
            require_text(payload["actor_id"], "actor_id"),
            require_text(payload["canonical_name"], "canonical_name"),
            _enum_value(ActorKind, payload["actor_kind"], "actor_kind"),
            _optional_text(payload.get("jurisdiction"), "jurisdiction"),
            require_string_list(payload["external_refs"], "external_refs"),
            require_string_list(payload["notes"], "notes"),
        )

    def to_dict(self) -> dict[str, Any]:
        result = {
            "contract_version": self.contract_version,
            "actor_id": self.actor_id,
            "canonical_name": self.canonical_name,
            "actor_kind": self.actor_kind.value,
            "external_refs": list(self.external_refs),
            "notes": list(self.notes),
        }
        if self.jurisdiction is not None:
            result["jurisdiction"] = self.jurisdiction
        return result
```

- [ ] **Step 4: Run GREEN**

```bash
pytest -q tests/test_assets.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/andes_context_os/assets.py tests/test_assets.py
git commit -m "feat: add asset and actor contracts"
```

---

### Task 2: Evidence-Linked Movement Contract

**Files:**
- Create: `src/andes_context_os/movements.py`
- Create: `tests/test_movements.py`

**Interfaces:**
- Consumes: `CONTRACT_VERSION`, `require_aware_iso8601()`, `require_fields()`, `require_string_list()`, `require_text()`.
- Produces:
  - `ActorRole` enum.
  - `MovementActorRef.from_dict()` / `.to_dict()`.
  - `MovementType` enum.
  - `MovementReviewState` enum.
  - `Movement.from_dict()` / `.to_dict()`.

- [ ] **Step 1: Write RED movement tests**

Create the movement half of `tests/test_movements.py`:

```python
import pytest

from andes_context_os.movements import (
    ActorRole,
    Movement,
    MovementReviewState,
    MovementType,
)


def movement_payload(**overrides):
    payload = {
        "contract_version": "0.1",
        "movement_id": "movement:rg:drilling:2026-05-21",
        "asset_id": "asset:ar:li:rio-grande-noa",
        "movement_type": "drilling",
        "observed_at": "2026-09-02T22:00:00-03:00",
        "actor_refs": [
            {"actor_id": "actor:noa-lithium", "role": "operator", "notes": []},
            {"actor_id": "actor:hidrotec", "role": "contractor", "notes": []},
        ],
        "evidence_candidate_refs": ["evidence:rg:noa:2026-05-21"],
        "factual_summary": "NOA reported completion of drilling-rig mobilization by Hidrotec for the 2026 Rio Grande campaign.",
        "previous_state": None,
        "new_state": None,
        "review_state": "reviewed",
        "reviewed_at": "2026-09-02T22:05:00-03:00",
        "derived_from_movement_ids": [],
        "limitations": ["Company disclosure; no inference about unannounced procurement."],
    }
    payload.update(overrides)
    return payload


def test_movement_round_trip_preserves_evidence_links_and_roles():
    movement = Movement.from_dict(movement_payload())
    assert movement.movement_type == MovementType.DRILLING
    assert movement.review_state == MovementReviewState.REVIEWED
    assert movement.actor_refs[1].role == ActorRole.CONTRACTOR
    assert movement.to_dict() == movement_payload()


def test_movement_requires_evidence_reference():
    with pytest.raises(ValueError, match="evidence_candidate_refs must not be empty"):
        Movement.from_dict(movement_payload(evidence_candidate_refs=[]))


def test_movement_rejects_duplicate_actor_role_pairs():
    actor = {"actor_id": "actor:noa-lithium", "role": "operator", "notes": []}
    with pytest.raises(ValueError, match="duplicate actor-role reference"):
        Movement.from_dict(movement_payload(actor_refs=[actor, actor]))


def test_stage_change_requires_distinct_previous_and_new_state():
    with pytest.raises(ValueError, match="stage_change requires distinct previous_state and new_state"):
        Movement.from_dict(movement_payload(
            movement_type="stage_change",
            previous_state="construction",
            new_state="construction",
        ))


def test_reviewed_movement_requires_reviewed_at():
    with pytest.raises(ValueError, match="reviewed_at is required"):
        Movement.from_dict(movement_payload(reviewed_at=None))


def test_unreviewed_movement_rejects_reviewed_at():
    with pytest.raises(ValueError, match="reviewed_at must be null"):
        Movement.from_dict(movement_payload(review_state="unreviewed"))


def test_movement_rejects_self_lineage():
    with pytest.raises(ValueError, match="cannot derive from itself"):
        Movement.from_dict(movement_payload(derived_from_movement_ids=["movement:rg:drilling:2026-05-21"]))
```

- [ ] **Step 2: Run RED**

```bash
pytest -q tests/test_movements.py
```

Expected: import/collection failure because `andes_context_os.movements` does not exist.

- [ ] **Step 3: Implement minimal movement contracts**

Create `src/andes_context_os/movements.py` with these public enums and classes:

```python
class ActorRole(StrEnum):
    OPERATOR = "operator"
    OWNER = "owner"
    PARTNER = "partner"
    CONTRACTOR = "contractor"
    CONSULTANT = "consultant"
    SUPPLIER = "supplier"
    FINANCIER = "financier"
    OFFTAKER = "offtaker"
    REGULATOR = "regulator"
    STATE_PARTNER = "state_partner"
    COMMUNITY_ACTOR = "community_actor"
    OTHER = "other"


class MovementType(StrEnum):
    STAGE_CHANGE = "stage_change"
    DRILLING = "drilling"
    PERMIT = "permit"
    CAPITAL = "capital"
    OWNERSHIP = "ownership"
    PARTNERSHIP = "partnership"
    CONTRACTOR = "contractor"
    CONSULTING = "consulting"
    OFFTAKE = "offtake"
    CONSTRUCTION = "construction"
    INFRASTRUCTURE = "infrastructure"
    PRODUCTION = "production"
    EXPANSION = "expansion"
    HIRING = "hiring"
    OTHER = "other"


class MovementReviewState(StrEnum):
    UNREVIEWED = "unreviewed"
    EVIDENCE_LINKED = "evidence_linked"
    REVIEWED = "reviewed"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
```

Implement `MovementActorRef` and `Movement` as frozen/slotted dataclasses using the existing strict helper style. Required parser rules:

```python
refs = require_string_list(payload["evidence_candidate_refs"], "evidence_candidate_refs", allow_empty=False)
if len(refs) != len(set(refs)):
    raise ValueError("evidence_candidate_refs contains duplicates")

pairs = [(item.actor_id, item.role.value) for item in actor_refs]
if len(pairs) != len(set(pairs)):
    raise ValueError("duplicate actor-role reference")

if movement_type == MovementType.STAGE_CHANGE:
    if previous_state is None or new_state is None or previous_state == new_state:
        raise ValueError("stage_change requires distinct previous_state and new_state")

reviewed_states = {
    MovementReviewState.REVIEWED,
    MovementReviewState.REJECTED,
    MovementReviewState.SUPERSEDED,
}
if review_state in reviewed_states and reviewed_at is None:
    raise ValueError("reviewed_at is required for reviewed, rejected and superseded movements")
if review_state not in reviewed_states and reviewed_at is not None:
    raise ValueError("reviewed_at must be null for unreviewed and evidence_linked movements")

if movement_id in derived_from_movement_ids:
    raise ValueError("movement cannot derive from itself")
if len(derived_from_movement_ids) != len(set(derived_from_movement_ids)):
    raise ValueError("derived_from_movement_ids contains duplicates")
```

`to_dict()` must emit every field in the spec, including explicit `None` for `previous_state`, `new_state`, and `reviewed_at`, so round-trip output is deterministic.

- [ ] **Step 4: Run GREEN**

```bash
pytest -q tests/test_movements.py
```

Expected: movement tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/andes_context_os/movements.py tests/test_movements.py
git commit -m "feat: add evidence-linked movement contract"
```

---

### Task 3: Explicit Opportunity Hypothesis Contract

**Files:**
- Create: `src/andes_context_os/opportunities.py`
- Modify: `tests/test_movements.py`

**Interfaces:**
- Consumes: `CONTRACT_VERSION`, `require_aware_iso8601()`, `require_fields()`, `require_string_list()`, `require_text()`.
- Produces:
  - `OpportunityStatus` enum.
  - `OpportunityHypothesis.from_dict()` / `.to_dict()`.
- Cross-object claims such as same-asset triggers and “additional evidence beyond trigger evidence” are intentionally deferred to Task 4 validator.

- [ ] **Step 1: Add RED opportunity tests**

Append to `tests/test_movements.py`:

```python
from andes_context_os.opportunities import OpportunityHypothesis, OpportunityStatus


def hypothesis_payload(**overrides):
    payload = {
        "contract_version": "0.1",
        "hypothesis_id": "opportunity:rg:external-field-services",
        "asset_id": "asset:ar:li:rio-grande-noa",
        "trigger_movement_refs": ["movement:rg:drilling:2026-05-21"],
        "actor_refs": ["actor:noa-lithium"],
        "need_category": "field_services",
        "statement": "Continued PFS work may create additional demand for externally procured field services.",
        "supporting_evidence_refs": [],
        "assumptions": ["At least part of future field work is procured externally."],
        "missing_context": ["Current supplier roster and procurement model."],
        "status": "proposed",
        "created_at": "2026-09-02T22:10:00-03:00",
        "reviewed_at": None,
    }
    payload.update(overrides)
    return payload


def test_proposed_hypothesis_round_trip_preserves_uncertainty():
    item = OpportunityHypothesis.from_dict(hypothesis_payload())
    assert item.status == OpportunityStatus.PROPOSED
    assert item.assumptions == ("At least part of future field work is procured externally.",)
    assert item.missing_context == ("Current supplier roster and procurement model.",)
    assert item.to_dict() == hypothesis_payload()


def test_hypothesis_requires_trigger_movement():
    with pytest.raises(ValueError, match="trigger_movement_refs must not be empty"):
        OpportunityHypothesis.from_dict(hypothesis_payload(trigger_movement_refs=[]))


def test_hypothesis_rejects_duplicate_actor_refs():
    with pytest.raises(ValueError, match="actor_refs contains duplicates"):
        OpportunityHypothesis.from_dict(hypothesis_payload(actor_refs=["actor:noa-lithium", "actor:noa-lithium"]))


def test_supported_hypothesis_requires_supporting_evidence_and_reviewed_at_locally():
    with pytest.raises(ValueError, match="supported requires supporting_evidence_refs"):
        OpportunityHypothesis.from_dict(hypothesis_payload(status="supported", reviewed_at="2026-09-02T22:15:00-03:00"))
    with pytest.raises(ValueError, match="reviewed_at is required"):
        OpportunityHypothesis.from_dict(hypothesis_payload(status="supported", supporting_evidence_refs=["evidence:extra"]))


def test_proposed_hypothesis_rejects_reviewed_at():
    with pytest.raises(ValueError, match="reviewed_at must be null"):
        OpportunityHypothesis.from_dict(hypothesis_payload(reviewed_at="2026-09-02T22:15:00-03:00"))
```

- [ ] **Step 2: Run RED**

```bash
pytest -q tests/test_movements.py
```

Expected: collection failure because `andes_context_os.opportunities` does not exist.

- [ ] **Step 3: Implement minimal opportunity contract**

Create `src/andes_context_os/opportunities.py` with:

```python
class OpportunityStatus(StrEnum):
    PROPOSED = "proposed"
    RESEARCHING = "researching"
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    DISCARDED = "discarded"
```

Implement `OpportunityHypothesis` as a frozen/slotted dataclass with the exact spec fields. Local parser rules:

```python
triggers = require_string_list(payload["trigger_movement_refs"], "trigger_movement_refs", allow_empty=False)
actors = require_string_list(payload["actor_refs"], "actor_refs")
support = require_string_list(payload["supporting_evidence_refs"], "supporting_evidence_refs")

for field, values in (
    ("trigger_movement_refs", triggers),
    ("actor_refs", actors),
    ("supporting_evidence_refs", support),
):
    if len(values) != len(set(values)):
        raise ValueError(f"{field} contains duplicates")

reviewed_states = {
    OpportunityStatus.SUPPORTED,
    OpportunityStatus.CONTRADICTED,
    OpportunityStatus.DISCARDED,
}
if status == OpportunityStatus.SUPPORTED and not support:
    raise ValueError("supported requires supporting_evidence_refs")
if status == OpportunityStatus.CONTRADICTED and not support:
    raise ValueError("contradicted requires supporting_evidence_refs")
if status in reviewed_states and reviewed_at is None:
    raise ValueError("reviewed_at is required for supported, contradicted and discarded hypotheses")
if status not in reviewed_states and reviewed_at is not None:
    raise ValueError("reviewed_at must be null for proposed and researching hypotheses")
```

Do not attempt semantic scoring, natural-language classification, same-asset validation or evidence-difference validation in this parser.

- [ ] **Step 4: Run GREEN**

```bash
pytest -q tests/test_movements.py
```

Expected: movement + opportunity tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/andes_context_os/opportunities.py tests/test_movements.py
git commit -m "feat: add opportunity hypothesis contract"
```

---

### Task 4: Deterministic Cross-Object Benchmark Validator

**Files:**
- Create: `src/andes_context_os/asset_movement_benchmark.py`
- Create: `tests/test_asset_movement_benchmark.py`

**Interfaces:**
- Consumes: `Asset`, `Actor`, `Movement`, `MovementReviewState`, `EvidenceCandidate`, `OpportunityHypothesis`, `OpportunityStatus`.
- Produces:
  - `validate_asset_movement_benchmark(*, assets, actors, movements, evidence_candidates, opportunity_hypotheses) -> None`.
  - `load_asset_movement_fixture(base_dir: str | Path) -> tuple[tuple[Asset, ...], tuple[Actor, ...], tuple[Movement, ...], tuple[OpportunityHypothesis, ...]]`.
  - `canonical_asset_movement_projection(*, assets, actors, movements, opportunity_hypotheses) -> dict[str, list[dict[str, Any]]]`.

- [ ] **Step 1: Write RED validator tests with real public-source evidence identities**

Create the top of `tests/test_asset_movement_benchmark.py`:

```python
import json
from pathlib import Path

import pytest

from andes_context_os.asset_movement_benchmark import (
    canonical_asset_movement_projection,
    load_asset_movement_fixture,
    validate_asset_movement_benchmark,
)
from andes_context_os.assets import Actor, Asset
from andes_context_os.evidence import EvidenceCandidate
from andes_context_os.movements import Movement
from andes_context_os.opportunities import OpportunityHypothesis

DOGFOOD = Path("data/dogfood/argentina-lithium")


def evidence(candidate_id: str, source_id: str, title: str, summary: str, source_reference: str, scope_id: str):
    return EvidenceCandidate.from_dict({
        "candidate_id": candidate_id,
        "source_id": source_id,
        "source_runtime_observation_id": None,
        "kind": "technical_reference",
        "title": title,
        "factual_summary": summary,
        "source_reference": source_reference,
        "temporal_context": {"observed_at": "2026-09-02T22:00:00-03:00"},
        "territorial_relation": {"scope_id": scope_id, "relation": "project-specific"},
        "quality": {
            "contract_version": "0.1",
            "authority": "first_party",
            "source_verification": "source_located",
            "freshness": "current",
            "spatial_precision": "project_area",
            "temporal_precision": "day",
            "coverage": "complete_for_claim",
            "completeness": "complete_for_contract",
            "corroboration": "single_source",
            "method_transparency": "documented",
            "rights_clarity": "reference_only",
            "review_state": "source_verified",
            "limitations": ["First-party public disclosure; interpretation remains bounded to the stated claim."],
            "missing_context": [],
        },
        "payload_ref": None,
        "corroboration_refs": [],
        "derived_from_ids": [],
        "candidate_state": "usable_for_research",
    })


PUBLIC_EVIDENCE = (
    evidence(
        "evidence:rg:noa:2026-05-21",
        "noa-lithium-news",
        "Rio Grande 2026 drilling mobilization",
        "NOA reported that Hidrotec completed mobilization of two drilling rigs for the 2026 Rio Grande campaign.",
        "https://www.noalithium.com/_resources/news/nr-20260521.pdf",
        "project:atlas-geotech:258",
    ),
    evidence(
        "evidence:hmw:galan:2026-07-30",
        "galan-quarterly-2026-q2",
        "HMW transition to producer and ramp-up",
        "Galan reported completion of wet commissioning, first processed lithium chloride and production ramp-up at HMW.",
        "https://www.ayondo.com/en/accw/AU0000021461/galan-lithium-limited/quarterly-activities-report-june-2026",
        "project:atlas-geotech:137",
    ),
    evidence(
        "evidence:co:lar:2026-08-11",
        "lithium-argentina-q2-2026",
        "Cauchari-Olaroz Stage 2 expansion activities",
        "Lithium Argentina reported RIGI approval and early development activities for Stage 2, including production wells, infrastructure and site preparation.",
        "https://investors.lithium-argentina.com/news-releases/news-release-details/lithium-argentina-reports-second-quarter-2026-results",
        "project:atlas-geotech:52",
    ),
)
```

Then add validator-focused tests:

```python
def load_valid_objects():
    assets, actors, movements, hypotheses = load_asset_movement_fixture(DOGFOOD)
    return assets, actors, movements, hypotheses


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
```

- [ ] **Step 2: Run RED**

```bash
pytest -q tests/test_asset_movement_benchmark.py
```

Expected: collection/import failure because the benchmark module does not exist and/or fixture files are absent.

- [ ] **Step 3: Implement loader, duplicate-ID guards, canonical projection and validator**

Create `src/andes_context_os/asset_movement_benchmark.py`. Use one generic JSON-array loader and explicit ID maps:

```python
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
    return tuple(parser(item) for item in raw)


def _unique_map(items: Iterable[T], id_attr: str, label: str) -> dict[str, T]:
    result: dict[str, T] = {}
    for item in items:
        item_id = getattr(item, id_attr)
        if item_id in result:
            raise ValueError(f"duplicate {label} id: {item_id}")
        result[item_id] = item
    return result


def load_asset_movement_fixture(base_dir: str | Path):
    base = Path(base_dir)
    return (
        _load_array(base / "assets.json", Asset.from_dict),
        _load_array(base / "actors.json", Actor.from_dict),
        _load_array(base / "movements.json", Movement.from_dict),
        _load_array(base / "opportunity_hypotheses.json", OpportunityHypothesis.from_dict),
    )


def canonical_asset_movement_projection(*, assets, actors, movements, opportunity_hypotheses):
    return {
        "assets": [item.to_dict() for item in sorted(assets, key=lambda item: item.asset_id)],
        "actors": [item.to_dict() for item in sorted(actors, key=lambda item: item.actor_id)],
        "movements": [item.to_dict() for item in sorted(movements, key=lambda item: item.movement_id)],
        "opportunity_hypotheses": [item.to_dict() for item in sorted(opportunity_hypotheses, key=lambda item: item.hypothesis_id)],
    }
```

Implement `validate_asset_movement_benchmark()` using explicit maps and these checks in this order:

1. reject duplicate asset, actor, movement, evidence and hypothesis IDs;
2. each movement asset exists;
3. each movement actor exists;
4. each movement evidence candidate exists;
5. each movement lineage reference exists and is not self-referential;
6. each hypothesis asset exists;
7. each hypothesis actor exists;
8. each trigger movement exists and belongs to the same asset;
9. each supporting evidence ref exists;
10. if status is `SUPPORTED`, the union of all trigger-movement evidence refs must not contain every supporting evidence ref;
11. if status is `SUPPORTED` and every trigger movement is `REJECTED`, reject it.

Use deterministic `ValueError` messages that include only IDs/field labels, never source bodies.

- [ ] **Step 4: Run validator tests; expect fixture absence only**

```bash
pytest -q tests/test_asset_movement_benchmark.py
```

Expected: failures should now be limited to absent dogfood fixture files. There must be no import errors.

- [ ] **Step 5: Commit validator before real fixtures**

```bash
git add src/andes_context_os/asset_movement_benchmark.py tests/test_asset_movement_benchmark.py
git commit -m "feat: add asset movement benchmark validator"
```

---

### Task 5: Three-Asset Argentina Lithium Dogfood Fixtures

**Files:**
- Create: `data/dogfood/argentina-lithium/assets.json`
- Create: `data/dogfood/argentina-lithium/actors.json`
- Create: `data/dogfood/argentina-lithium/movements.json`
- Create: `data/dogfood/argentina-lithium/opportunity_hypotheses.json`
- Modify: `tests/test_asset_movement_benchmark.py`

**Interfaces:**
- Consumes exact Atlas Geotech references from the approved spec and exact evidence IDs defined in `PUBLIC_EVIDENCE`.
- Produces one reviewed movement + one proposed opportunity hypothesis per asset, sufficient to dogfood stage differences without claiming commercial demand.

- [ ] **Step 1: Add exact three-asset fixtures**

Create `assets.json` with exactly:

```json
[
  {
    "contract_version": "0.1",
    "asset_id": "asset:ar:li:rio-grande-noa",
    "name": "Río Grande / NOA Lithium",
    "asset_type": "mining_project",
    "commodity": "lithium",
    "territorial_scope_ref": "project:atlas-geotech:258",
    "baseline_source_id": "atlas-geotech",
    "baseline_record_ref": "project_id:258",
    "notes": ["Atlas Geotech baseline identity only; mutable state is researched separately."]
  },
  {
    "contract_version": "0.1",
    "asset_id": "asset:ar:li:hombre-muerto-oeste",
    "name": "Hombre Muerto Oeste",
    "asset_type": "mining_project",
    "commodity": "lithium",
    "territorial_scope_ref": "project:atlas-geotech:137",
    "baseline_source_id": "atlas-geotech",
    "baseline_record_ref": "project_id:137",
    "notes": ["Atlas Geotech baseline identity only; mutable state is researched separately."]
  },
  {
    "contract_version": "0.1",
    "asset_id": "asset:ar:li:cauchari-olaroz",
    "name": "Cauchari-Olaroz",
    "asset_type": "mining_project",
    "commodity": "lithium",
    "territorial_scope_ref": "project:atlas-geotech:52",
    "baseline_source_id": "atlas-geotech",
    "baseline_record_ref": "project_id:52",
    "notes": ["Atlas Geotech baseline identity only; mutable state is researched separately."]
  }
]
```

Create `actors.json` with these actors only:

```json
[
  {
    "contract_version": "0.1",
    "actor_id": "actor:noa-lithium",
    "canonical_name": "NOA Lithium Brines Inc.",
    "actor_kind": "organization",
    "jurisdiction": "Canada / Argentina",
    "external_refs": ["https://www.noalithium.com/"],
    "notes": []
  },
  {
    "contract_version": "0.1",
    "actor_id": "actor:hidrotec",
    "canonical_name": "Hidrotec S.A.",
    "actor_kind": "organization",
    "jurisdiction": "Argentina",
    "external_refs": [],
    "notes": ["Named by NOA as drilling contractor in the 2026 Rio Grande campaign."]
  },
  {
    "contract_version": "0.1",
    "actor_id": "actor:galan-lithium",
    "canonical_name": "Galan Lithium Limited",
    "actor_kind": "organization",
    "jurisdiction": "Australia / Argentina",
    "external_refs": ["https://galanlithium.com.au/"],
    "notes": []
  },
  {
    "contract_version": "0.1",
    "actor_id": "actor:lithium-argentina",
    "canonical_name": "Lithium Argentina AG",
    "actor_kind": "organization",
    "jurisdiction": "Switzerland / Argentina",
    "external_refs": ["https://www.lithium-argentina.com/"],
    "notes": []
  },
  {
    "contract_version": "0.1",
    "actor_id": "actor:ganfeng-lithium",
    "canonical_name": "Ganfeng Lithium",
    "actor_kind": "organization",
    "jurisdiction": "China / Argentina",
    "external_refs": [],
    "notes": ["Named by Lithium Argentina as its partner in the Cauchari-Olaroz Stage 2 development work."]
  }
]
```

Create `movements.json` with one reviewed movement per asset:

```json
[
  {
    "contract_version": "0.1",
    "movement_id": "movement:rg:drilling:2026-05-21",
    "asset_id": "asset:ar:li:rio-grande-noa",
    "movement_type": "drilling",
    "observed_at": "2026-09-02T22:00:00-03:00",
    "actor_refs": [
      {"actor_id": "actor:noa-lithium", "role": "operator", "notes": []},
      {"actor_id": "actor:hidrotec", "role": "contractor", "notes": []}
    ],
    "evidence_candidate_refs": ["evidence:rg:noa:2026-05-21"],
    "factual_summary": "NOA reported completion of mobilization of two Hidrotec drilling rigs for the 2026 Rio Grande exploration campaign supporting work toward PFS.",
    "previous_state": null,
    "new_state": null,
    "review_state": "reviewed",
    "reviewed_at": "2026-09-02T22:05:00-03:00",
    "derived_from_movement_ids": [],
    "limitations": ["First-party company disclosure; does not establish future procurement beyond the named work."]
  },
  {
    "contract_version": "0.1",
    "movement_id": "movement:hmw:stage-change:2026-q2",
    "asset_id": "asset:ar:li:hombre-muerto-oeste",
    "movement_type": "stage_change",
    "observed_at": "2026-09-02T22:00:00-03:00",
    "actor_refs": [
      {"actor_id": "actor:galan-lithium", "role": "operator", "notes": []}
    ],
    "evidence_candidate_refs": ["evidence:hmw:galan:2026-07-30"],
    "factual_summary": "Galan reported completion of wet commissioning, first processed lithium chloride and production ramp-up at Hombre Muerto Oeste.",
    "previous_state": "construction / commissioning",
    "new_state": "production ramp-up",
    "review_state": "reviewed",
    "reviewed_at": "2026-09-02T22:05:00-03:00",
    "derived_from_movement_ids": [],
    "limitations": ["Stage wording is a bounded research interpretation of the cited quarterly disclosure, not a regulatory status classification."]
  },
  {
    "contract_version": "0.1",
    "movement_id": "movement:co:expansion:2026-08-11",
    "asset_id": "asset:ar:li:cauchari-olaroz",
    "movement_type": "expansion",
    "observed_at": "2026-09-02T22:00:00-03:00",
    "actor_refs": [
      {"actor_id": "actor:lithium-argentina", "role": "partner", "notes": []},
      {"actor_id": "actor:ganfeng-lithium", "role": "partner", "notes": []}
    ],
    "evidence_candidate_refs": ["evidence:co:lar:2026-08-11"],
    "factual_summary": "Lithium Argentina reported RIGI approval and early Stage 2 development activities at Cauchari-Olaroz, including additional production wells, infrastructure and site preparation, while advancing a modular DLE approach with Ganfeng.",
    "previous_state": null,
    "new_state": null,
    "review_state": "reviewed",
    "reviewed_at": "2026-09-02T22:05:00-03:00",
    "derived_from_movement_ids": [],
    "limitations": ["The disclosure identifies planned and early development activities; it does not identify which future scopes are externally procured."]
  }
]
```

Create `opportunity_hypotheses.json` with all three in `proposed` state:

```json
[
  {
    "contract_version": "0.1",
    "hypothesis_id": "opportunity:rg:external-field-services",
    "asset_id": "asset:ar:li:rio-grande-noa",
    "trigger_movement_refs": ["movement:rg:drilling:2026-05-21"],
    "actor_refs": ["actor:noa-lithium"],
    "need_category": "field_services",
    "statement": "Continued work toward PFS may create additional demand for externally procured drilling, hydrogeological or related field services.",
    "supporting_evidence_refs": [],
    "assumptions": ["At least part of future field work would be procured from external providers."],
    "missing_context": ["Current supplier roster.", "Procurement model and contract duration.", "Remaining 2026-2027 field-work scope."],
    "status": "proposed",
    "created_at": "2026-09-02T22:10:00-03:00",
    "reviewed_at": null
  },
  {
    "contract_version": "0.1",
    "hypothesis_id": "opportunity:hmw:ramp-up-support",
    "asset_id": "asset:ar:li:hombre-muerto-oeste",
    "trigger_movement_refs": ["movement:hmw:stage-change:2026-q2"],
    "actor_refs": ["actor:galan-lithium"],
    "need_category": "ramp_up_support",
    "statement": "Production ramp-up and planned capacity growth may create service needs around operating optimisation, laboratory QA/QC, pond works or plant support.",
    "supporting_evidence_refs": [],
    "assumptions": ["Some ramp-up or expansion scopes may be externally sourced rather than fully internal."],
    "missing_context": ["Current operating contractor model.", "Laboratory and QA/QC supplier arrangements.", "Scope owners for planned pond works."],
    "status": "proposed",
    "created_at": "2026-09-02T22:10:00-03:00",
    "reviewed_at": null
  },
  {
    "contract_version": "0.1",
    "hypothesis_id": "opportunity:co:stage2-supplier-scope",
    "asset_id": "asset:ar:li:cauchari-olaroz",
    "trigger_movement_refs": ["movement:co:expansion:2026-08-11"],
    "actor_refs": ["actor:lithium-argentina", "actor:ganfeng-lithium"],
    "need_category": "expansion_services",
    "statement": "Stage 2 early development may create externally addressable scopes around wells, infrastructure, site preparation, engineering or equipment integration.",
    "supporting_evidence_refs": [],
    "assumptions": ["At least one Stage 2 scope may be open to external suppliers or contractors."],
    "missing_context": ["Stage 2 procurement model.", "Existing framework agreements.", "Packages retained internally by Ganfeng or Minera Exar."],
    "status": "proposed",
    "created_at": "2026-09-02T22:10:00-03:00",
    "reviewed_at": null
  }
]
```

- [ ] **Step 2: Add benchmark assertions for exact baselines and canonical order**

Append to `tests/test_asset_movement_benchmark.py`:

```python
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


def test_canonical_projection_is_order_independent():
    assets, actors, movements, hypotheses = load_asset_movement_fixture(DOGFOOD)
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
```

- [ ] **Step 3: Run dogfood integration GREEN**

```bash
pytest -q tests/test_asset_movement_benchmark.py
```

Expected: PASS.

- [ ] **Step 4: Run focused V0.4 suite**

```bash
pytest -q tests/test_assets.py tests/test_movements.py tests/test_asset_movement_benchmark.py
```

Expected: PASS.

- [ ] **Step 5: Commit real dogfood fixtures**

```bash
git add data/dogfood/argentina-lithium tests/test_asset_movement_benchmark.py
git commit -m "test: add argentina lithium movement dogfood"
```

---

### Task 6: Release Gate, README Boundary and Full Regression

**Files:**
- Modify: `README.md`
- Modify: `tests/test_asset_movement_benchmark.py`
- Verify: `pyproject.toml`

**Interfaces:**
- Consumes all V0.4 contracts and fixtures.
- Produces a documented experimental V0.4 boundary and full regression evidence without changing runtime dependencies.

- [ ] **Step 1: Add RED release/dependency/privacy tests**

Append to `tests/test_asset_movement_benchmark.py`:

```python
def test_v04_dogfood_files_do_not_contain_private_or_action_fields():
    banned = {
        "email", "gmail", "apollo", "phone", "contact_name", "send_request",
        "approved_to_send", "route_authorized", "safe_to_travel", "community_approved",
    }
    for path in DOGFOOD.glob("*.json"):
        text = path.read_text(encoding="utf-8").lower()
        assert all(term not in text for term in banned)


def test_pyproject_keeps_runtime_dependencies_empty():
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "dependencies = []" in text
```

Run:

```bash
pytest -q tests/test_asset_movement_benchmark.py
```

Expected: PASS unless public fixture wording accidentally violates the privacy gate; fix fixture wording rather than weakening the gate.

- [ ] **Step 2: Add concise README V0.4 section**

Add after the current capability table or before “What it deliberately does not do”:

```markdown
## V0.4 experimental asset-movement dogfood

V0.4 adds a small interpretation layer above evidence for one controlled benchmark: three Argentine lithium assets seeded from exact Atlas Geotech baseline references.

```text
Asset baseline
  ↓
EvidenceCandidate
  ↓
Movement + actor roles
  ↓
OpportunityHypothesis
  ↓
explicit assumptions + missing context
```

The benchmark currently covers Río Grande / NOA Lithium, Hombre Muerto Oeste and Cauchari-Olaroz. It is designed to test whether meaningful project changes can be represented reproducibly without turning a public signal into verified demand.

The boundary remains strict:

```text
baseline record != current state
movement != opportunity
opportunity hypothesis != confirmed demand
actor participation != durable relationship
```

V0.4 does not add live scraping, a relationship graph, contact discovery, outreach, a database, a UI, scoring, agents or MCP.
```

Do not market the repository as a supplier marketplace, autonomous research agent or proven commercial intelligence engine.

- [ ] **Step 3: Run all tests**

```bash
pytest -q
```

Expected: all existing V0.1–V0.3 tests plus new V0.4 tests PASS.

- [ ] **Step 4: Verify no runtime dependency drift**

```bash
python - <<'PY'
from pathlib import Path
text = Path("pyproject.toml").read_text(encoding="utf-8")
assert "requires-python = \">=3.11\"" in text
assert "dependencies = []" in text
print("dependency gate: PASS")
PY
```

Expected: `dependency gate: PASS`.

- [ ] **Step 5: Inspect the public fixture diff for source/evidence boundary**

```bash
git diff --check
git diff -- data/dogfood/argentina-lithium README.md
```

Acceptance check: fixtures contain structured summaries and exact IDs only; no copied source-body paragraphs, private data, action authorization, guessed contacts or unsupported “confirmed demand” language.

- [ ] **Step 6: Commit release boundary**

```bash
git add README.md tests/test_asset_movement_benchmark.py
git commit -m "docs: describe v0.4 asset movement dogfood"
```

- [ ] **Step 7: Final verification before completion claim**

Run:

```bash
pytest -q
git status --short
git log -5 --oneline
```

Expected:
- all tests PASS;
- working tree contains no unintended files;
- recent commits show the V0.4 contract, movement, benchmark, fixtures and docs sequence.

## Implementation Completion Criteria

Before declaring V0.4 complete, verify all of the following from fresh command output:

- `Asset` contains identity/baseline fields only and rejects mutable `current_stage`-style additions.
- `Actor` contains no durable commercial role field.
- every benchmark `Movement` resolves an asset, all actor-role refs and at least one `EvidenceCandidate`.
- every benchmark hypothesis resolves its trigger movement(s) and actors.
- all three public dogfood hypotheses remain `proposed`; the repository makes no claim that service demand is confirmed.
- supported-state contract tests prove additional evidence beyond trigger evidence is required.
- exact Atlas baseline refs remain `project_id:258`, `project_id:137`, `project_id:52`.
- canonical projection is order independent.
- production runtime dependencies remain empty.
- the full legacy + V0.4 pytest suite passes.
- README calls V0.4 experimental dogfood, not a proven market-intelligence product.
