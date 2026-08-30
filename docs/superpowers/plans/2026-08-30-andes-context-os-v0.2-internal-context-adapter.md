# Andes Context OS V0.2 — Internal Context Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, dependency-free internal-context adapter that turns a strict local reference catalog into an immutable, content-addressed `InternalContextSnapshot` for a `ResearchIntent` + `TerritorialScope` pair without reading GitHub, the private vault, a database, an LLM, embeddings, or any external service.

**Architecture:** Keep contracts and serialization in `src/andes_context_os/internal_context.py`; keep selection/orchestration in `src/andes_context_os/adapters/internal_context.py`. The catalog contains high-density references only. Matching is exact and categorical (`domain_match`, `activity_match`, `territory_match`), territorial-specific records require an exact territorial match, restricted records never leave the adapter, and the snapshot ID is SHA-256 over canonical serialized snapshot content excluding `snapshot_id` itself.

**Tech Stack:** Python 3.11+, stdlib only (`dataclasses`, `enum.StrEnum`, `json`, `pathlib`), existing `andes_context_os.common` validation helpers, existing `andes_context_os.hashing.sha256_json`, pytest >=8,<9, GitHub Actions Python 3.11.

**Spec:** `docs/superpowers/specs/2026-08-30-andes-context-os-v0.2-internal-context-adapter-design.md`

## Global Constraints

- Work only on branch `feat/internal-context-adapter`; do not write implementation commits directly to `main`.
- Preserve `contract_version = "0.1"` and use `snapshot_version = "0.1"`, `catalog_version = "0.1"`.
- No new runtime dependency.
- No network access, GitHub client, vault client, Google Drive client, DB, API, CLI, LLM, embeddings, fuzzy matching, bbox intersection, or GeoPlatform runtime import.
- `internal context match != evidence validation`.
- `known evidence reference != current operational evidence`.
- `known decision != current authorization`.
- No `relevance_score`, `confidence_score`, weighted rank, aggregate score, `risk_score`, or `truth_score`.
- Unknown contract fields fail closed with `ValueError` via the existing `require_fields()` pattern.
- Persisted timestamps must be timezone-aware ISO-8601 via `require_aware_iso8601()`.
- All list inputs must be validated as JSON lists and copied to immutable tuples.
- Restricted records must never be serialized into `InternalContextSnapshot`; omission reporting must not reveal ID, title, reference, summary, count, tags, or territorial metadata.
- Snapshot output ordering must be deterministic and independent of input catalog order.
- `snapshot_id` must be the lowercase SHA-256 from `sha256_json()` over the complete serialized snapshot payload excluding `snapshot_id` itself.
- `DiscoveryRun` stays unchanged; V0.2 only provides a snapshot suitable for `lineage.internal_snapshot_ref` and `lineage.input_refs[]`.
- Baseline before implementation: 117 tests green on V0.1. Every task must preserve existing tests.

## File Structure

```text
src/andes_context_os/
├── internal_context.py                 # enums, record/catalog contracts, selection projection, snapshot serialization/hash
└── adapters/
    ├── __init__.py                     # adapter package marker/public import boundary
    └── internal_context.py             # exact matching, eligibility gates, restricted omission behavior

data/
└── internal_context.example.v0.1.json  # fictitious/public-safe example catalog only

tests/
├── test_internal_context.py            # contract/catalog/snapshot tests
├── test_internal_context_adapter.py    # selection semantics and privacy tests
└── test_internal_context_release.py    # public example + README/release assertions

README.md                               # document V0.2 without claiming live vault/GitHub integration
```

`internal_context.py` owns data semantics and canonical serialization. `adapters/internal_context.py` owns only selection decisions. This prevents provider I/O from leaking into the contract core when real Vault/GitHub producers are added later.

---

### Task 1: InternalContextRecord + InternalContextCatalog

**Files:**
- Create: `src/andes_context_os/internal_context.py`
- Create: `tests/test_internal_context.py`

**Interfaces:**
- Consumes: `CONTRACT_VERSION`, `require_aware_iso8601()`, `require_fields()`, `require_string_list()`, `require_text()` from `andes_context_os.common`; `ResearchDomain`, `ResearchActivity` from `andes_context_os.research`.
- Produces: `InternalContextKind`, `ContextSensitivity`, `InternalContextRecord.from_dict()`, `InternalContextRecord.to_dict()`, `InternalContextCatalog.from_dict()`, `InternalContextCatalog.load()`, `InternalContextCatalog.to_dict()`.

- [ ] **Step 1: Add RED fixtures and record parsing tests**

Create `tests/test_internal_context.py` with the exact base fixture and first contract tests:

```python
from copy import deepcopy
import json

import pytest

from andes_context_os.internal_context import (
    ContextSensitivity,
    InternalContextCatalog,
    InternalContextKind,
    InternalContextRecord,
)


VALID_RECORD = {
    "contract_version": "0.1",
    "context_id": "repo-geoplatform-access",
    "kind": "repository",
    "title": "GeoPlatform access capability",
    "reference": "repo:GeoPlatform#access",
    "summary": "Existing territorial access-analysis capability worth inspecting before a new spike.",
    "domains": ["logistics"],
    "activities": ["access", "route_planning"],
    "territory_refs": [],
    "tags": ["geospatial", "access"],
    "sensitivity": "public",
    "reviewed_at": "2026-08-30T09:00:00-03:00",
    "limitations": ["Reference does not establish current road condition"],
}


def test_internal_context_record_round_trips():
    record = InternalContextRecord.from_dict(VALID_RECORD)
    assert record.to_dict() == VALID_RECORD
    assert record.kind is InternalContextKind.REPOSITORY
    assert record.sensitivity is ContextSensitivity.PUBLIC


def test_record_rejects_unknown_field():
    with pytest.raises(ValueError, match="unknown fields: api_key"):
        InternalContextRecord.from_dict({**VALID_RECORD, "api_key": "secret"})


def test_record_rejects_unknown_kind():
    with pytest.raises(ValueError, match="kind"):
        InternalContextRecord.from_dict({**VALID_RECORD, "kind": "memory_blob"})


def test_record_rejects_unknown_sensitivity():
    with pytest.raises(ValueError, match="sensitivity"):
        InternalContextRecord.from_dict({**VALID_RECORD, "sensitivity": "classified"})


def test_record_rejects_unknown_domain():
    with pytest.raises(ValueError, match="domains"):
        InternalContextRecord.from_dict({**VALID_RECORD, "domains": ["magic"]})


def test_record_rejects_unknown_activity():
    with pytest.raises(ValueError, match="activities"):
        InternalContextRecord.from_dict({**VALID_RECORD, "activities": ["teleportation"]})


def test_record_rejects_naive_reviewed_at():
    with pytest.raises(ValueError, match="timezone-aware"):
        InternalContextRecord.from_dict({**VALID_RECORD, "reviewed_at": "2026-08-30T09:00:00"})


def test_record_accepts_reviewed_at_omitted():
    payload = {key: value for key, value in VALID_RECORD.items() if key != "reviewed_at"}
    assert InternalContextRecord.from_dict(payload).reviewed_at is None
```

- [ ] **Step 2: Run the record tests to verify RED**

Run:

```bash
pytest tests/test_internal_context.py -q
```

Expected: collection fails with `ModuleNotFoundError: No module named 'andes_context_os.internal_context'`.

- [ ] **Step 3: Implement the minimal record contract**

Create `src/andes_context_os/internal_context.py` with closed enums and strict parsing following existing V0.1 patterns:

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import Path
from typing import Any

from andes_context_os.common import (
    CONTRACT_VERSION,
    require_aware_iso8601,
    require_fields,
    require_string_list,
    require_text,
)
from andes_context_os.research import ResearchActivity, ResearchDomain

CATALOG_VERSION = "0.1"
SNAPSHOT_VERSION = "0.1"


class InternalContextKind(StrEnum):
    VAULT_NOTE = "vault_note"
    REPOSITORY = "repository"
    FEATURE = "feature"
    KNOWN_SOURCE = "known_source"
    KNOWN_EVIDENCE = "known_evidence"
    KNOWN_GAP = "known_gap"
    KNOWN_DECISION = "known_decision"


class ContextSensitivity(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"


def _enum_value(enum_type: type[StrEnum], value: Any, field: str) -> StrEnum:
    text = require_text(value, field)
    try:
        return enum_type(text)
    except ValueError as exc:
        raise ValueError(f"{field} has unsupported value: {text}") from exc


def _enum_list(enum_type: type[StrEnum], value: Any, field: str) -> tuple[StrEnum, ...]:
    raw = require_string_list(value, field)
    return tuple(_enum_value(enum_type, item, field) for item in raw)


@dataclass(frozen=True, slots=True)
class InternalContextRecord:
    contract_version: str
    context_id: str
    kind: InternalContextKind
    title: str
    reference: str
    summary: str
    domains: tuple[ResearchDomain, ...]
    activities: tuple[ResearchActivity, ...]
    territory_refs: tuple[str, ...]
    tags: tuple[str, ...]
    sensitivity: ContextSensitivity
    reviewed_at: str | None
    limitations: tuple[str, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "InternalContextRecord":
        required = {
            "contract_version", "context_id", "kind", "title", "reference", "summary",
            "domains", "activities", "territory_refs", "tags", "sensitivity", "limitations",
        }
        allowed = required | {"reviewed_at"}
        require_fields(payload, required=required, allowed=allowed)
        contract_version = require_text(payload["contract_version"], "contract_version")
        if contract_version != CONTRACT_VERSION:
            raise ValueError(f"contract_version must be {CONTRACT_VERSION}")
        reviewed_at = payload.get("reviewed_at")
        return cls(
            contract_version=contract_version,
            context_id=require_text(payload["context_id"], "context_id"),
            kind=_enum_value(InternalContextKind, payload["kind"], "kind"),
            title=require_text(payload["title"], "title"),
            reference=require_text(payload["reference"], "reference"),
            summary=require_text(payload["summary"], "summary"),
            domains=_enum_list(ResearchDomain, payload["domains"], "domains"),
            activities=_enum_list(ResearchActivity, payload["activities"], "activities"),
            territory_refs=require_string_list(payload["territory_refs"], "territory_refs"),
            tags=require_string_list(payload["tags"], "tags"),
            sensitivity=_enum_value(ContextSensitivity, payload["sensitivity"], "sensitivity"),
            reviewed_at=(
                require_aware_iso8601(reviewed_at, "reviewed_at")
                if reviewed_at is not None else None
            ),
            limitations=require_string_list(payload["limitations"], "limitations"),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "contract_version": self.contract_version,
            "context_id": self.context_id,
            "kind": self.kind.value,
            "title": self.title,
            "reference": self.reference,
            "summary": self.summary,
            "domains": [item.value for item in self.domains],
            "activities": [item.value for item in self.activities],
            "territory_refs": list(self.territory_refs),
            "tags": list(self.tags),
            "sensitivity": self.sensitivity.value,
            "limitations": list(self.limitations),
        }
        if self.reviewed_at is not None:
            payload["reviewed_at"] = self.reviewed_at
        return payload
```

Do not add matching, snapshot logic, file provider abstractions, or hashes in this step.

- [ ] **Step 4: Run record tests to verify GREEN**

Run:

```bash
pytest tests/test_internal_context.py -q
```

Expected: all record tests pass.

- [ ] **Step 5: Add RED catalog tests**

Append:

```python
VALID_CATALOG = {
    "catalog_version": "0.1",
    "records": [VALID_RECORD],
}


def test_catalog_round_trips():
    catalog = InternalContextCatalog.from_dict(VALID_CATALOG)
    assert catalog.to_dict() == VALID_CATALOG


def test_catalog_rejects_duplicate_context_ids():
    payload = {"catalog_version": "0.1", "records": [VALID_RECORD, deepcopy(VALID_RECORD)]}
    with pytest.raises(ValueError, match="duplicate context_id"):
        InternalContextCatalog.from_dict(payload)


def test_catalog_rejects_unknown_version():
    with pytest.raises(ValueError, match="catalog_version"):
        InternalContextCatalog.from_dict({**VALID_CATALOG, "catalog_version": "9.9"})


def test_catalog_rejects_unknown_top_level_field():
    with pytest.raises(ValueError, match="unknown fields: source_url"):
        InternalContextCatalog.from_dict({**VALID_CATALOG, "source_url": "https://example.invalid"})


def test_catalog_loads_local_json(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(VALID_CATALOG), encoding="utf-8")
    catalog = InternalContextCatalog.load(path)
    assert catalog.records[0].context_id == VALID_RECORD["context_id"]


def test_catalog_load_rejects_malformed_json_without_echoing_contents(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text('{"secret-summary": ', encoding="utf-8")
    with pytest.raises(ValueError, match="invalid internal context catalog JSON") as exc:
        InternalContextCatalog.load(path)
    assert "secret-summary" not in str(exc.value)
```

- [ ] **Step 6: Run catalog tests to verify RED**

Run:

```bash
pytest tests/test_internal_context.py -q
```

Expected: failures because `InternalContextCatalog` does not exist yet.

- [ ] **Step 7: Implement the minimal catalog**

Add:

```python
@dataclass(frozen=True, slots=True)
class InternalContextCatalog:
    catalog_version: str
    records: tuple[InternalContextRecord, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "InternalContextCatalog":
        fields = {"catalog_version", "records"}
        require_fields(payload, required=fields, allowed=fields)
        version = require_text(payload["catalog_version"], "catalog_version")
        if version != CATALOG_VERSION:
            raise ValueError(f"catalog_version must be {CATALOG_VERSION}")
        if not isinstance(payload["records"], list):
            raise ValueError("records must be a list")
        records = tuple(InternalContextRecord.from_dict(item) for item in payload["records"])
        ids = [record.context_id for record in records]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate context_id in internal context catalog")
        return cls(catalog_version=version, records=records)

    @classmethod
    def load(cls, path: str | Path) -> "InternalContextCatalog":
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("invalid internal context catalog JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("internal context catalog root must be an object")
        return cls.from_dict(payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "catalog_version": self.catalog_version,
            "records": [record.to_dict() for record in self.records],
        }
```

`load()` is local file I/O only. Do not add URLs, environment-variable discovery, defaults to private paths, or automatic file creation.

- [ ] **Step 8: Run Task 1 GREEN + regression suite**

Run:

```bash
pytest tests/test_internal_context.py -q
pytest -q
python -m compileall -q src
```

Expected: Task 1 tests pass; all pre-existing 117 tests remain green; compile exits 0.

- [ ] **Step 9: Commit Task 1**

```bash
git add src/andes_context_os/internal_context.py tests/test_internal_context.py
git commit -m "feat: add internal context catalog contracts"
```

---

### Task 2: ContextSelection + content-addressed InternalContextSnapshot

**Files:**
- Modify: `src/andes_context_os/internal_context.py`
- Modify: `tests/test_internal_context.py`

**Interfaces:**
- Consumes: `InternalContextKind`, existing `sha256_json()`.
- Produces: `MatchReason`, `ContextSelection.from_dict()`, `ContextSelection.to_dict()`, `InternalContextSnapshot.build()`, `InternalContextSnapshot.from_dict()`, `InternalContextSnapshot.to_dict()`, `InternalContextSnapshot.snapshot_id` field validated against canonical content.
- Later consumed by: `InternalContextAdapter.snapshot()` in Task 3.

- [ ] **Step 1: Add RED projection tests**

Append to `tests/test_internal_context.py`:

```python
from andes_context_os.internal_context import ContextSelection, InternalContextSnapshot, MatchReason


VALID_SELECTION = {
    "context_id": "repo-geoplatform-access",
    "kind": "repository",
    "title": "GeoPlatform access capability",
    "reference": "repo:GeoPlatform#access",
    "summary": "Existing territorial access-analysis capability worth inspecting before a new spike.",
    "match_reasons": ["activity_match", "domain_match"],
    "limitations": ["Reference does not establish current road condition"],
}


def test_context_selection_round_trips_and_sorts_reasons():
    payload = {**VALID_SELECTION, "match_reasons": ["domain_match", "activity_match"]}
    selection = ContextSelection.from_dict(payload)
    assert selection.match_reasons == (MatchReason.ACTIVITY_MATCH, MatchReason.DOMAIN_MATCH)
    assert selection.to_dict()["match_reasons"] == ["activity_match", "domain_match"]


def test_context_selection_rejects_unknown_score():
    with pytest.raises(ValueError, match="unknown fields: relevance_score"):
        ContextSelection.from_dict({**VALID_SELECTION, "relevance_score": 0.9})


def test_context_selection_rejects_empty_match_reasons():
    with pytest.raises(ValueError, match="match_reasons"):
        ContextSelection.from_dict({**VALID_SELECTION, "match_reasons": []})
```

- [ ] **Step 2: Run projection tests to verify RED**

Run:

```bash
pytest tests/test_internal_context.py -q
```

Expected: import/attribute failures for `ContextSelection`, `MatchReason`, or `InternalContextSnapshot`.

- [ ] **Step 3: Implement MatchReason + ContextSelection**

Add:

```python
class MatchReason(StrEnum):
    DOMAIN_MATCH = "domain_match"
    ACTIVITY_MATCH = "activity_match"
    TERRITORY_MATCH = "territory_match"


@dataclass(frozen=True, slots=True)
class ContextSelection:
    context_id: str
    kind: InternalContextKind
    title: str
    reference: str
    summary: str
    match_reasons: tuple[MatchReason, ...]
    limitations: tuple[str, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ContextSelection":
        fields = {
            "context_id", "kind", "title", "reference", "summary",
            "match_reasons", "limitations",
        }
        require_fields(payload, required=fields, allowed=fields)
        reasons = tuple(sorted(
            (_enum_value(MatchReason, item, "match_reasons") for item in require_string_list(payload["match_reasons"], "match_reasons", allow_empty=False)),
            key=lambda item: item.value,
        ))
        return cls(
            context_id=require_text(payload["context_id"], "context_id"),
            kind=_enum_value(InternalContextKind, payload["kind"], "kind"),
            title=require_text(payload["title"], "title"),
            reference=require_text(payload["reference"], "reference"),
            summary=require_text(payload["summary"], "summary"),
            match_reasons=reasons,
            limitations=require_string_list(payload["limitations"], "limitations"),
        )

    @classmethod
    def from_record(
        cls,
        record: InternalContextRecord,
        reasons: tuple[MatchReason, ...],
    ) -> "ContextSelection":
        if not reasons:
            raise ValueError("match_reasons must not be empty")
        return cls.from_dict({
            "context_id": record.context_id,
            "kind": record.kind.value,
            "title": record.title,
            "reference": record.reference,
            "summary": record.summary,
            "match_reasons": [reason.value for reason in reasons],
            "limitations": list(record.limitations),
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "kind": self.kind.value,
            "title": self.title,
            "reference": self.reference,
            "summary": self.summary,
            "match_reasons": [reason.value for reason in self.match_reasons],
            "limitations": list(self.limitations),
        }
```

- [ ] **Step 4: Add RED snapshot/hash tests**

Append:

```python
SNAPSHOT_COMPONENTS = {
    "generated_at": "2026-08-30T10:00:00-03:00",
    "research_intent_id": "intent-filo-access-001",
    "question_profile_ref": "question-radar:profile-001",
    "territorial_scope_id": "scope-ar-j",
}


def build_snapshot(*, selections=(VALID_SELECTION,), missing_context=(), generated_at=None):
    parsed = tuple(ContextSelection.from_dict(item) for item in selections)
    return InternalContextSnapshot.build(
        generated_at=generated_at or SNAPSHOT_COMPONENTS["generated_at"],
        research_intent_id=SNAPSHOT_COMPONENTS["research_intent_id"],
        question_profile_ref=SNAPSHOT_COMPONENTS["question_profile_ref"],
        territorial_scope_id=SNAPSHOT_COMPONENTS["territorial_scope_id"],
        selections=parsed,
        missing_context=tuple(missing_context),
    )


def test_snapshot_id_is_64_lowercase_hex_and_round_trips():
    snapshot = build_snapshot()
    assert len(snapshot.snapshot_id) == 64
    assert snapshot.snapshot_id == snapshot.snapshot_id.lower()
    assert set(snapshot.snapshot_id) <= set("0123456789abcdef")
    assert InternalContextSnapshot.from_dict(snapshot.to_dict()).to_dict() == snapshot.to_dict()


def test_snapshot_id_changes_when_generated_at_changes():
    first = build_snapshot(generated_at="2026-08-30T10:00:00-03:00")
    second = build_snapshot(generated_at="2026-08-30T10:01:00-03:00")
    assert first.snapshot_id != second.snapshot_id


def test_snapshot_rejects_naive_generated_at():
    with pytest.raises(ValueError, match="timezone-aware"):
        build_snapshot(generated_at="2026-08-30T10:00:00")


def test_snapshot_rejects_tampered_snapshot_id():
    payload = build_snapshot().to_dict()
    payload["snapshot_id"] = "0" * 64
    with pytest.raises(ValueError, match="snapshot_id mismatch"):
        InternalContextSnapshot.from_dict(payload)


def test_snapshot_buckets_selection_by_kind():
    snapshot = build_snapshot()
    assert len(snapshot.related_repositories) == 1
    assert snapshot.related_vault_notes == ()
    assert snapshot.known_evidence == ()
```

- [ ] **Step 5: Run snapshot tests to verify RED**

Run:

```bash
pytest tests/test_internal_context.py -q
```

Expected: failures because `InternalContextSnapshot` is not implemented.

- [ ] **Step 6: Implement content-addressed snapshot**

Add `from andes_context_os.hashing import sha256_json` and implement the category mapping once:

```python
_CATEGORY_BY_KIND = {
    InternalContextKind.VAULT_NOTE: "related_vault_notes",
    InternalContextKind.REPOSITORY: "related_repositories",
    InternalContextKind.FEATURE: "related_features",
    InternalContextKind.KNOWN_SOURCE: "known_sources",
    InternalContextKind.KNOWN_EVIDENCE: "known_evidence",
    InternalContextKind.KNOWN_GAP: "known_gaps",
    InternalContextKind.KNOWN_DECISION: "known_decisions",
}
```

Implement `InternalContextSnapshot` as a frozen/slots dataclass with these exact fields:

```python
contract_version: str
snapshot_version: str
snapshot_id: str
generated_at: str
research_intent_id: str
question_profile_ref: str | None
territorial_scope_id: str
related_vault_notes: tuple[ContextSelection, ...]
related_repositories: tuple[ContextSelection, ...]
related_features: tuple[ContextSelection, ...]
known_sources: tuple[ContextSelection, ...]
known_evidence: tuple[ContextSelection, ...]
known_gaps: tuple[ContextSelection, ...]
known_decisions: tuple[ContextSelection, ...]
missing_context: tuple[str, ...]
```

`build()` must:

1. validate `generated_at`, IDs, optional `question_profile_ref`, and `missing_context`;
2. sort `selections` by `(selection.kind.value, selection.context_id)`;
3. bucket each selection by `_CATEGORY_BY_KIND`;
4. build a payload **without** `snapshot_id`;
5. compute `snapshot_id = sha256_json(payload_without_id)`;
6. return an immutable snapshot.

Use this canonical helper shape so `build()`, `from_dict()`, and `to_dict()` cannot disagree:

```python
def _snapshot_payload_without_id(self) -> dict[str, Any]:
    return {
        "contract_version": self.contract_version,
        "snapshot_version": self.snapshot_version,
        "generated_at": self.generated_at,
        "research_intent_id": self.research_intent_id,
        "question_profile_ref": self.question_profile_ref,
        "territorial_scope_id": self.territorial_scope_id,
        "related_vault_notes": [item.to_dict() for item in self.related_vault_notes],
        "related_repositories": [item.to_dict() for item in self.related_repositories],
        "related_features": [item.to_dict() for item in self.related_features],
        "known_sources": [item.to_dict() for item in self.known_sources],
        "known_evidence": [item.to_dict() for item in self.known_evidence],
        "known_gaps": [item.to_dict() for item in self.known_gaps],
        "known_decisions": [item.to_dict() for item in self.known_decisions],
        "missing_context": list(self.missing_context),
    }
```

`to_dict()` returns `{**payload_without_id, "snapshot_id": self.snapshot_id}` with `snapshot_id` placed in the schema position used by tests/README; key order does not affect hashing because `sha256_json()` sorts object keys.

`from_dict()` must strict-parse every category, reject a selection whose `kind` does not match its category, recompute `sha256_json(payload_without_id)`, and raise `ValueError("snapshot_id mismatch")` if it differs from supplied `snapshot_id`.

- [ ] **Step 7: Run Task 2 GREEN + regression suite**

Run:

```bash
pytest tests/test_internal_context.py -q
pytest -q
python -m compileall -q src
```

Expected: all internal-context contract/snapshot tests pass; pre-existing tests remain green; compile exits 0.

- [ ] **Step 8: Commit Task 2**

```bash
git add src/andes_context_os/internal_context.py tests/test_internal_context.py
git commit -m "feat: add content-addressed internal context snapshot"
```

---

### Task 3: InternalContextAdapter exact selection + privacy boundary

**Files:**
- Create: `src/andes_context_os/adapters/__init__.py`
- Create: `src/andes_context_os/adapters/internal_context.py`
- Create: `tests/test_internal_context_adapter.py`

**Interfaces:**
- Consumes: `ResearchIntent`, `TerritorialScope`, `InternalContextCatalog`, `InternalContextRecord`, `ContextSensitivity`, `ContextSelection`, `InternalContextSnapshot`, `MatchReason`.
- Produces: `InternalContextAdapter.snapshot(intent, scope, catalog, *, generated_at) -> InternalContextSnapshot`.

- [ ] **Step 1: Write RED adapter fixtures and exact-match tests**

Create `tests/test_internal_context_adapter.py`:

```python
from copy import deepcopy

import pytest

from andes_context_os.adapters.internal_context import InternalContextAdapter
from andes_context_os.internal_context import InternalContextCatalog
from andes_context_os.research import ResearchIntent, TerritorialScope


INTENT = {
    "contract_version": "0.1",
    "intent_id": "intent-filo-access-001",
    "question_raw": "¿Qué sabemos ya sobre acceso minero en este corredor?",
    "question_canonical": "¿Qué contexto interno existente conviene revisar antes de investigar acceso minero?",
    "question_profile_ref": "question-radar:profile-001",
    "domain": "logistics",
    "activity": "access",
    "goal": "recover prior internal context before external research",
    "constraints": ["research only"],
    "territory_hint": "San Juan Andes",
    "created_at": "2026-08-30T09:00:00-03:00",
}

SCOPE = {
    "contract_version": "0.1",
    "scope_id": "scope-agua-negra",
    "countries": ["AR"],
    "admin_units": [{
        "country_code": "AR",
        "admin_level": "1",
        "official_code": "J",
        "name": "San Juan",
        "source_id": "ar_ign_admin",
    }],
    "project_refs": [],
    "corridor_refs": ["agua-negra-v1"],
    "segment_refs": [],
    "bbox": None,
    "geometry_ref": None,
    "crs": None,
    "precision": "corridor",
    "relation_basis": "known_route",
    "notes": [],
}


def record(
    context_id,
    *,
    kind="repository",
    domains=None,
    activities=None,
    territory_refs=None,
    sensitivity="public",
):
    return {
        "contract_version": "0.1",
        "context_id": context_id,
        "kind": kind,
        "title": f"Title {context_id}",
        "reference": f"ref:{context_id}",
        "summary": f"Summary {context_id}",
        "domains": ["logistics"] if domains is None else domains,
        "activities": ["access"] if activities is None else activities,
        "territory_refs": [] if territory_refs is None else territory_refs,
        "tags": [],
        "sensitivity": sensitivity,
        "reviewed_at": "2026-08-30T08:00:00-03:00",
        "limitations": [],
    }


def make_catalog(*records):
    return InternalContextCatalog.from_dict({"catalog_version": "0.1", "records": list(records)})


def build_snapshot(*records):
    return InternalContextAdapter().snapshot(
        ResearchIntent.from_dict(INTENT),
        TerritorialScope.from_dict(SCOPE),
        make_catalog(*records),
        generated_at="2026-08-30T10:00:00-03:00",
    )


def test_generic_record_matches_domain_and_activity():
    snapshot = build_snapshot(record("generic"))
    selection = snapshot.related_repositories[0]
    assert selection.context_id == "generic"
    assert [reason.value for reason in selection.match_reasons] == ["activity_match", "domain_match"]


def test_territorial_record_requires_exact_territory_match():
    snapshot = build_snapshot(record("peru-only", territory_refs=["PE"]))
    assert snapshot.related_repositories == ()
    assert snapshot.missing_context == (
        "no internal context matched the current intent and territorial scope",
    )


def test_exact_corridor_match_adds_territory_reason():
    snapshot = build_snapshot(record("agua-negra", territory_refs=["agua-negra-v1"]))
    reasons = [reason.value for reason in snapshot.related_repositories[0].match_reasons]
    assert reasons == ["activity_match", "domain_match", "territory_match"]


def test_territory_only_record_can_match_when_semantic_vocabularies_are_empty():
    snapshot = build_snapshot(record(
        "corridor-note",
        kind="vault_note",
        domains=[],
        activities=[],
        territory_refs=["agua-negra-v1"],
    ))
    assert snapshot.related_vault_notes[0].context_id == "corridor-note"
    assert [reason.value for reason in snapshot.related_vault_notes[0].match_reasons] == ["territory_match"]
```

- [ ] **Step 2: Run targeted adapter tests to verify RED**

Run:

```bash
pytest tests/test_internal_context_adapter.py -q
```

Expected: collection fails because `andes_context_os.adapters.internal_context` does not exist.

- [ ] **Step 3: Implement exact scope-reference derivation and eligibility**

Create `src/andes_context_os/adapters/__init__.py` as an empty package marker.

Create `src/andes_context_os/adapters/internal_context.py` with these helpers:

```python
from __future__ import annotations

from andes_context_os.internal_context import (
    ContextSelection,
    ContextSensitivity,
    InternalContextCatalog,
    InternalContextRecord,
    InternalContextSnapshot,
    MatchReason,
)
from andes_context_os.research import ResearchIntent, TerritorialScope


NO_MATCH_MESSAGE = "no internal context matched the current intent and territorial scope"
RESTRICTED_OMISSION_MESSAGE = "restricted internal context was omitted"


def _scope_refs(scope: TerritorialScope) -> frozenset[str]:
    refs = set(scope.countries)
    refs.update(
        unit.official_code
        for unit in scope.admin_units
        if unit.official_code is not None
    )
    refs.update(scope.project_refs)
    refs.update(scope.corridor_refs)
    refs.update(scope.segment_refs)
    if scope.geometry_ref is not None:
        refs.add(scope.geometry_ref)
    return frozenset(refs)


def _match_reasons(
    record: InternalContextRecord,
    intent: ResearchIntent,
    scope_refs: frozenset[str],
) -> tuple[MatchReason, ...]:
    reasons: list[MatchReason] = []
    if intent.domain in record.domains:
        reasons.append(MatchReason.DOMAIN_MATCH)
    if intent.activity in record.activities:
        reasons.append(MatchReason.ACTIVITY_MATCH)
    if set(record.territory_refs) & scope_refs:
        reasons.append(MatchReason.TERRITORY_MATCH)
    return tuple(sorted(reasons, key=lambda reason: reason.value))


def _eligible(record: InternalContextRecord, reasons: tuple[MatchReason, ...]) -> bool:
    reason_set = set(reasons)
    territory_match = MatchReason.TERRITORY_MATCH in reason_set
    territorial_gate = not record.territory_refs or territory_match
    if record.domains or record.activities:
        semantic_gate = bool(
            reason_set & {MatchReason.DOMAIN_MATCH, MatchReason.ACTIVITY_MATCH}
        )
    else:
        semantic_gate = territory_match
    return territorial_gate and semantic_gate
```

Implement the adapter:

```python
class InternalContextAdapter:
    def snapshot(
        self,
        intent: ResearchIntent,
        scope: TerritorialScope,
        catalog: InternalContextCatalog,
        *,
        generated_at: str,
    ) -> InternalContextSnapshot:
        scope_refs = _scope_refs(scope)
        selections: list[ContextSelection] = []
        restricted_omitted = False

        for record in catalog.records:
            reasons = _match_reasons(record, intent, scope_refs)
            if not _eligible(record, reasons):
                continue
            if record.sensitivity is ContextSensitivity.RESTRICTED:
                restricted_omitted = True
                continue
            selections.append(ContextSelection.from_record(record, reasons))

        missing_context: list[str] = []
        if not selections:
            missing_context.append(NO_MATCH_MESSAGE)
        if restricted_omitted:
            missing_context.append(RESTRICTED_OMISSION_MESSAGE)

        return InternalContextSnapshot.build(
            generated_at=generated_at,
            research_intent_id=intent.intent_id,
            question_profile_ref=intent.question_profile_ref,
            territorial_scope_id=scope.scope_id,
            selections=tuple(selections),
            missing_context=tuple(missing_context),
        )
```

Do not log records, summaries, references, or IDs from restricted entries.

- [ ] **Step 4: Run exact-match tests to verify GREEN**

Run:

```bash
pytest tests/test_internal_context_adapter.py -q
```

Expected: first four adapter tests pass.

- [ ] **Step 5: Add RED privacy, empty, ordering and immutability tests**

Append:

```python
def test_restricted_match_is_omitted_without_metadata_leakage():
    secret_id = "restricted-secret-id"
    snapshot = build_snapshot(record(
        secret_id,
        kind="known_evidence",
        territory_refs=["agua-negra-v1"],
        sensitivity="restricted",
    ))
    serialized = repr(snapshot.to_dict())
    assert snapshot.known_evidence == ()
    assert snapshot.missing_context == (
        "no internal context matched the current intent and territorial scope",
        "restricted internal context was omitted",
    )
    assert secret_id not in serialized
    assert f"ref:{secret_id}" not in serialized
    assert f"Summary {secret_id}" not in serialized


def test_restricted_omission_message_is_emitted_once_for_many_records():
    snapshot = build_snapshot(
        record("secret-1", territory_refs=["agua-negra-v1"], sensitivity="restricted"),
        record("secret-2", territory_refs=["agua-negra-v1"], sensitivity="restricted"),
    )
    assert snapshot.missing_context.count("restricted internal context was omitted") == 1


def test_unrestricted_match_plus_restricted_match_keeps_public_selection_and_generic_warning():
    snapshot = build_snapshot(
        record("public-record"),
        record("secret-record", territory_refs=["agua-negra-v1"], sensitivity="restricted"),
    )
    assert snapshot.related_repositories[0].context_id == "public-record"
    assert snapshot.missing_context == ("restricted internal context was omitted",)


def test_catalog_order_does_not_change_snapshot_serialization_or_id():
    first_record = record("b-record")
    second_record = record("a-record")
    first = build_snapshot(first_record, second_record)
    second = build_snapshot(second_record, first_record)
    assert first.to_dict() == second.to_dict()
    assert first.snapshot_id == second.snapshot_id


def test_snapshot_categories_are_immutable_tuples():
    snapshot = build_snapshot(record("generic"))
    assert isinstance(snapshot.related_repositories, tuple)
    with pytest.raises(AttributeError):
        snapshot.related_repositories.append("x")


def test_adapter_does_not_emit_numeric_or_authorization_fields():
    payload = build_snapshot(record("generic")).to_dict()
    text = repr(payload)
    for forbidden in (
        "relevance_score",
        "confidence_score",
        "risk_score",
        "truth_score",
        "safe_to_travel",
        "road_open",
        "route_authorized",
        "community_approved",
    ):
        assert forbidden not in text
```

- [ ] **Step 6: Run privacy/order tests and full suite**

Run:

```bash
pytest tests/test_internal_context_adapter.py -q
pytest -q
python -m compileall -q src
```

Expected: all adapter tests pass, all prior tests remain green, compile exits 0.

- [ ] **Step 7: Commit Task 3**

```bash
git add src/andes_context_os/adapters tests/test_internal_context_adapter.py
git commit -m "feat: add deterministic internal context adapter"
```

---

### Task 4: Public-safe example catalog + README + release/CI gate

**Files:**
- Create: `data/internal_context.example.v0.1.json`
- Create: `tests/test_internal_context_release.py`
- Modify: `README.md`
- Do not modify: `.github/workflows/tests.yml` unless CI reveals a genuine workflow defect unrelated to V0.2.

**Interfaces:**
- Consumes: `InternalContextCatalog.load()`, `InternalContextAdapter.snapshot()`.
- Produces: public V0.2 example, accurate README claims, final branch verification.

- [ ] **Step 1: Add RED release tests before adding example/docs claims**

Create `tests/test_internal_context_release.py`:

```python
from pathlib import Path

from andes_context_os.adapters.internal_context import InternalContextAdapter
from andes_context_os.internal_context import ContextSensitivity, InternalContextCatalog
from andes_context_os.research import ResearchIntent, TerritorialScope

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_PATH = ROOT / "data" / "internal_context.example.v0.1.json"
README_PATH = ROOT / "README.md"


def test_example_catalog_loads_and_contains_only_public_safe_records():
    catalog = InternalContextCatalog.load(EXAMPLE_PATH)
    assert len(catalog.records) == 3
    assert all(record.sensitivity is ContextSensitivity.PUBLIC for record in catalog.records)
    serialized = repr(catalog.to_dict()).lower()
    for forbidden in (
        "password",
        "api_key",
        "access_token",
        "cookie",
        "private repo",
        "private aoi",
    ):
        assert forbidden not in serialized


def test_readme_describes_v02_without_claiming_live_connectors():
    text = README_PATH.read_text(encoding="utf-8")
    assert "Internal Context Adapter" in text
    assert "local deterministic catalog" in text
    assert "does not read GitHub or the private vault" in text
    assert "internal context match != evidence validation" in text
```

- [ ] **Step 2: Run release tests to verify RED**

Run:

```bash
pytest tests/test_internal_context_release.py -q
```

Expected: failures because the example file and V0.2 README section do not exist yet.

- [ ] **Step 3: Add the exact public-safe example catalog**

Create `data/internal_context.example.v0.1.json`:

```json
{
  "catalog_version": "0.1",
  "records": [
    {
      "contract_version": "0.1",
      "context_id": "example-geoplatform-access",
      "kind": "repository",
      "title": "Example territorial access capability",
      "reference": "repo:example-geoplatform#access",
      "summary": "A public-safe example of an existing geospatial capability that may be relevant to access research.",
      "domains": ["logistics"],
      "activities": ["access", "route_planning"],
      "territory_refs": [],
      "tags": ["geospatial", "access"],
      "sensitivity": "public",
      "reviewed_at": "2026-08-30T09:00:00-03:00",
      "limitations": ["Example reference does not establish current road condition"]
    },
    {
      "contract_version": "0.1",
      "context_id": "example-corridor-note",
      "kind": "vault_note",
      "title": "Example corridor research note",
      "reference": "note:example-corridor-research",
      "summary": "A fictitious high-density note reference for demonstrating exact territorial matching.",
      "domains": [],
      "activities": [],
      "territory_refs": ["example-corridor-v1"],
      "tags": ["corridor"],
      "sensitivity": "public",
      "reviewed_at": "2026-08-30T09:00:00-03:00",
      "limitations": ["Fictitious example only"]
    },
    {
      "contract_version": "0.1",
      "context_id": "example-road-freshness-gap",
      "kind": "known_gap",
      "title": "Example road-condition freshness gap",
      "reference": "gap:example-road-freshness",
      "summary": "An example known gap showing that route geometry alone does not establish current operational condition.",
      "domains": ["access"],
      "activities": ["road_condition"],
      "territory_refs": [],
      "tags": ["freshness", "roads"],
      "sensitivity": "public",
      "reviewed_at": "2026-08-30T09:00:00-03:00",
      "limitations": ["Gap description is not a live road-status observation"]
    }
  ]
}
```

- [ ] **Step 4: Update README with accurate V0.2 surface**

Add a section after the V0.1 contract flow that states, substantively, this exact boundary:

```markdown
## V0.2 — Internal Context Adapter

V0.2 adds a deterministic internal-context boundary backed by a local deterministic catalog of high-density references.

```text
ResearchIntent + TerritorialScope
              ↓
      InternalContextCatalog
              ↓
     InternalContextAdapter
              ↓
    InternalContextSnapshot
```

The adapter uses exact categorical matching only (`domain_match`, `activity_match`, `territory_match`). Territorial-specific records require an exact structured territorial reference match. It does not rank context numerically.

`restricted` records are never emitted by V0.2. A matching restricted record produces only the generic message `restricted internal context was omitted`, without exposing its metadata.

V0.2 does not read GitHub or the private vault. Those systems may later become authorized producers of `InternalContextRecord`; they are not runtime dependencies of this release.

```text
internal context match != evidence validation
known evidence reference != current operational evidence
known decision != current authorization
```
```

Also update the existing “What V0.1 does not do” wording so it remains historically accurate and does not contradict the new local V0.2 adapter. Do **not** claim live GitHub search, vault access, private-data ingestion, evidence promotion, or route safety analysis.

- [ ] **Step 5: Run release tests to verify GREEN**

Run:

```bash
pytest tests/test_internal_context_release.py -q
```

Expected: all release tests pass.

- [ ] **Step 6: Run the final local verification gate**

Run from a clean checkout/worktree of `feat/internal-context-adapter`:

```bash
python -m pip install --no-build-isolation -e ".[dev]"
pytest -q
python -m compileall -q src
```

Expected:

- editable package build succeeds;
- all V0.1 + V0.2 tests pass with zero failures;
- compile exits 0.

If the current runtime has external DNS available, also run the canonical install command used by CI:

```bash
python -m pip install -e ".[dev]"
pytest -q
```

A DNS failure while fetching build dependencies is an environment limitation, not evidence that the project passes; rely on the actual GitHub Actions run for the network-enabled install gate.

- [ ] **Step 7: Commit Task 4**

```bash
git add data/internal_context.example.v0.1.json README.md tests/test_internal_context_release.py
git commit -m "docs: publish internal context adapter v0.2"
```

- [ ] **Step 8: Verify GitHub Actions on the feature branch**

After the Task 4 push, inspect the workflow run for the exact feature-branch HEAD. Required evidence:

```text
workflow: tests
head_branch: feat/internal-context-adapter
head_sha: <exact Task 4 commit SHA>
status: completed
conclusion: success
pytest step: success
```

Fetch the job log and verify the final pytest line reports zero failures. Do not infer CI success from the existence of `.github/workflows/tests.yml`.

- [ ] **Step 9: Final requirements review before integration**

Check each frozen requirement explicitly:

```text
strict record/catalog contracts                    PASS/FAIL
exact domain/activity/territory reasons             PASS/FAIL
territorial-specific gate                           PASS/FAIL
no fuzzy/proximity/bbox matching                     PASS/FAIL
no numeric relevance/confidence/risk/truth score     PASS/FAIL
restricted records non-emitting                      PASS/FAIL
restricted omission message non-leaking              PASS/FAIL
empty result represented explicitly                  PASS/FAIL
deterministic ordering                               PASS/FAIL
content-addressed snapshot_id                        PASS/FAIL
no DiscoveryRun schema change                        PASS/FAIL
no new runtime dependency                            PASS/FAIL
public-safe example only                             PASS/FAIL
README avoids live GitHub/vault claims               PASS/FAIL
full test suite green                                PASS/FAIL
feature-branch GitHub Actions green                  PASS/FAIL
```

If any item is FAIL, do not open/merge a PR until corrected and re-verified.
