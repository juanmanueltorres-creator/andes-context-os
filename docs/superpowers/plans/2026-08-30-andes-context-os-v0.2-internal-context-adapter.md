# Andes Context OS V0.2 — Internal Context Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, dependency-free internal-context adapter that converts a strict local reference catalog into an immutable, content-addressed `InternalContextSnapshot` for a `ResearchIntent` + `TerritorialScope` pair.

**Architecture:** Contracts, serialization and content hashing live in `src/andes_context_os/internal_context.py`; exact selection logic lives in `src/andes_context_os/adapters/internal_context.py`. The adapter never reads GitHub, the private vault, a database, an LLM or an external service. It emits categorical match reasons only and never promotes matched context into evidence or authorization.

**Tech Stack:** Python 3.11+, stdlib only (`dataclasses`, `enum.StrEnum`, `json`, `pathlib`, `re`), existing `andes_context_os.common` helpers, existing `andes_context_os.hashing.sha256_json`, pytest >=8,<9, GitHub Actions Python 3.11.

**Spec:** `docs/superpowers/specs/2026-08-30-andes-context-os-v0.2-internal-context-adapter-design.md`

## Global Constraints

- Branch: `feat/internal-context-adapter`; no implementation commits directly to `main`.
- `contract_version = "0.1"`; `catalog_version = "0.1"`; `snapshot_version = "0.1"`.
- No new runtime dependency.
- No network, GitHub/vault/Drive client, DB, API, CLI, LLM, embeddings, fuzzy matching, bbox intersection or GeoPlatform runtime import.
- `internal context match != evidence validation`.
- `known evidence reference != current operational evidence`.
- `known decision != current authorization`.
- No `relevance_score`, `confidence_score`, `risk_score`, `truth_score`, weighted rank or aggregate score.
- Unknown contract fields fail closed with `ValueError`.
- JSON list fields are validated as lists and copied to immutable tuples.
- Persisted timestamps are timezone-aware ISO-8601.
- Territorial-specific records require exact structured territorial equality.
- Restricted records never enter the snapshot; omission messages leak no restricted metadata or count.
- Snapshot ordering is deterministic and independent of input catalog order.
- `snapshot_id = sha256_json(serialized_snapshot_without_snapshot_id)`.
- `DiscoveryRun` schema is unchanged; callers may store `snapshot_id` in existing lineage refs.
- Baseline: V0.1 has 117 tests green. Preserve the full suite after every task.

## File map

```text
src/andes_context_os/internal_context.py
src/andes_context_os/adapters/__init__.py
src/andes_context_os/adapters/internal_context.py
data/internal_context.example.v0.1.json
tests/test_internal_context.py
tests/test_internal_context_adapter.py
tests/test_internal_context_release.py
README.md
```

---

### Task 1: Strict record and catalog contracts

**Files:**
- Create: `src/andes_context_os/internal_context.py`
- Create: `tests/test_internal_context.py`

**Interfaces:**
- Consumes: `CONTRACT_VERSION`, `require_aware_iso8601`, `require_fields`, `require_string_list`, `require_text`, `ResearchDomain`, `ResearchActivity`.
- Produces: `InternalContextKind`, `ContextSensitivity`, `InternalContextRecord`, `InternalContextCatalog`.

- [ ] **Step 1: Write RED record tests**

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
    "summary": "Existing territorial access capability worth inspecting before a new spike.",
    "domains": ["logistics"],
    "activities": ["access", "route_planning"],
    "territory_refs": [],
    "tags": ["geospatial", "access"],
    "sensitivity": "public",
    "reviewed_at": "2026-08-30T09:00:00-03:00",
    "limitations": ["Reference does not establish current road condition"],
}


def test_record_round_trips():
    record = InternalContextRecord.from_dict(VALID_RECORD)
    assert record.to_dict() == VALID_RECORD
    assert record.kind is InternalContextKind.REPOSITORY
    assert record.sensitivity is ContextSensitivity.PUBLIC


@pytest.mark.parametrize("field", ["password", "api_key", "access_token", "cookie"])
def test_record_rejects_unknown_secret_like_fields(field):
    with pytest.raises(ValueError, match=f"unknown fields: {field}"):
        InternalContextRecord.from_dict({**VALID_RECORD, field: "secret"})


def test_record_rejects_unknown_kind():
    with pytest.raises(ValueError, match="kind"):
        InternalContextRecord.from_dict({**VALID_RECORD, "kind": "memory_blob"})


def test_record_rejects_unknown_domain():
    with pytest.raises(ValueError, match="domains"):
        InternalContextRecord.from_dict({**VALID_RECORD, "domains": ["magic"]})


def test_record_rejects_unknown_activity():
    with pytest.raises(ValueError, match="activities"):
        InternalContextRecord.from_dict({**VALID_RECORD, "activities": ["teleportation"]})


def test_record_rejects_naive_reviewed_at():
    with pytest.raises(ValueError, match="timezone-aware"):
        InternalContextRecord.from_dict({**VALID_RECORD, "reviewed_at": "2026-08-30T09:00:00"})
```

- [ ] **Step 2: Run RED**

```bash
pytest tests/test_internal_context.py -q
```

Expected: `ModuleNotFoundError: No module named 'andes_context_os.internal_context'`.

- [ ] **Step 3: Implement record contract**

Create `src/andes_context_os/internal_context.py` with the existing V0.1 parsing pattern:

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import Path
import re
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
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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
    return tuple(_enum_value(enum_type, item, field) for item in require_string_list(value, field))


def _optional_text(value: Any, field: str) -> str | None:
    return None if value is None else require_text(value, field)


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
        version = require_text(payload["contract_version"], "contract_version")
        if version != CONTRACT_VERSION:
            raise ValueError(f"contract_version must be {CONTRACT_VERSION}")
        reviewed_at = payload.get("reviewed_at")
        return cls(
            contract_version=version,
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
            reviewed_at=(require_aware_iso8601(reviewed_at, "reviewed_at") if reviewed_at is not None else None),
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

- [ ] **Step 4: Run record GREEN**

```bash
pytest tests/test_internal_context.py -q
```

- [ ] **Step 5: Add RED catalog tests**

```python
VALID_CATALOG = {"catalog_version": "0.1", "records": [VALID_RECORD]}


def test_catalog_round_trips():
    assert InternalContextCatalog.from_dict(VALID_CATALOG).to_dict() == VALID_CATALOG


def test_catalog_rejects_duplicate_context_ids():
    payload = {"catalog_version": "0.1", "records": [VALID_RECORD, deepcopy(VALID_RECORD)]}
    with pytest.raises(ValueError, match="duplicate context_id"):
        InternalContextCatalog.from_dict(payload)


def test_catalog_rejects_non_object_record():
    with pytest.raises(ValueError, match="each record must be an object"):
        InternalContextCatalog.from_dict({"catalog_version": "0.1", "records": ["secret-text"]})


def test_catalog_loads_local_json(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(VALID_CATALOG), encoding="utf-8")
    assert InternalContextCatalog.load(path).records[0].context_id == VALID_RECORD["context_id"]


def test_catalog_load_rejects_malformed_json_without_echoing_contents(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text('{"secret-summary": ', encoding="utf-8")
    with pytest.raises(ValueError, match="invalid internal context catalog JSON") as exc:
        InternalContextCatalog.load(path)
    assert "secret-summary" not in str(exc.value)
```

- [ ] **Step 6: Run catalog RED**

```bash
pytest tests/test_internal_context.py -q
```

- [ ] **Step 7: Implement catalog**

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
        raw_records = payload["records"]
        if not isinstance(raw_records, list):
            raise ValueError("records must be a list")
        parsed: list[InternalContextRecord] = []
        for item in raw_records:
            if not isinstance(item, dict):
                raise ValueError("each record must be an object")
            parsed.append(InternalContextRecord.from_dict(item))
        ids = [record.context_id for record in parsed]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate context_id in internal context catalog")
        return cls(catalog_version=version, records=tuple(parsed))

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
        return {"catalog_version": self.catalog_version, "records": [record.to_dict() for record in self.records]}
```

- [ ] **Step 8: Verify + commit Task 1**

```bash
pytest tests/test_internal_context.py -q
pytest -q
python -m compileall -q src
git add src/andes_context_os/internal_context.py tests/test_internal_context.py
git commit -m "feat: add internal context catalog contracts"
```

---

### Task 2: Selection projection and content-addressed snapshot

**Files:**
- Modify: `src/andes_context_os/internal_context.py`
- Modify: `tests/test_internal_context.py`

**Interfaces:**
- Produces: `MatchReason`, `ContextSelection`, `InternalContextSnapshot.build()`, `.from_dict()`, `.to_dict()`.

- [ ] **Step 1: Add RED selection/snapshot tests**

```python
from andes_context_os.internal_context import ContextSelection, InternalContextSnapshot, MatchReason

VALID_SELECTION = {
    "context_id": "repo-geoplatform-access",
    "kind": "repository",
    "title": "GeoPlatform access capability",
    "reference": "repo:GeoPlatform#access",
    "summary": "Existing territorial access capability worth inspecting before a new spike.",
    "match_reasons": ["activity_match", "domain_match"],
    "limitations": ["Reference does not establish current road condition"],
}


def build_snapshot(*, selections=(VALID_SELECTION,), missing_context=(), generated_at="2026-08-30T10:00:00-03:00"):
    return InternalContextSnapshot.build(
        generated_at=generated_at,
        research_intent_id="intent-filo-access-001",
        question_profile_ref="question-radar:profile-001",
        territorial_scope_id="scope-ar-j",
        selections=tuple(ContextSelection.from_dict(item) for item in selections),
        missing_context=tuple(missing_context),
    )


def test_selection_sorts_reasons_and_rejects_scores():
    payload = {**VALID_SELECTION, "match_reasons": ["domain_match", "activity_match"]}
    selection = ContextSelection.from_dict(payload)
    assert selection.match_reasons == (MatchReason.ACTIVITY_MATCH, MatchReason.DOMAIN_MATCH)
    with pytest.raises(ValueError, match="unknown fields: relevance_score"):
        ContextSelection.from_dict({**VALID_SELECTION, "relevance_score": 0.9})


def test_snapshot_id_is_lowercase_sha256_and_round_trips():
    snapshot = build_snapshot()
    assert len(snapshot.snapshot_id) == 64
    assert set(snapshot.snapshot_id) <= set("0123456789abcdef")
    assert InternalContextSnapshot.from_dict(snapshot.to_dict()).to_dict() == snapshot.to_dict()


def test_snapshot_id_changes_when_content_changes():
    assert build_snapshot(generated_at="2026-08-30T10:00:00-03:00").snapshot_id != build_snapshot(generated_at="2026-08-30T10:01:00-03:00").snapshot_id


def test_snapshot_rejects_tampered_id():
    payload = build_snapshot().to_dict()
    payload["snapshot_id"] = "0" * 64
    with pytest.raises(ValueError, match="snapshot_id mismatch"):
        InternalContextSnapshot.from_dict(payload)
```

- [ ] **Step 2: Run RED**

```bash
pytest tests/test_internal_context.py -q
```

- [ ] **Step 3: Implement projection and snapshot**

Add `from andes_context_os.hashing import sha256_json` and these definitions:

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
        fields = {"context_id", "kind", "title", "reference", "summary", "match_reasons", "limitations"}
        require_fields(payload, required=fields, allowed=fields)
        raw = require_string_list(payload["match_reasons"], "match_reasons", allow_empty=False)
        reasons = tuple(sorted((_enum_value(MatchReason, item, "match_reasons") for item in raw), key=lambda item: item.value))
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
    def from_record(cls, record: InternalContextRecord, reasons: tuple[MatchReason, ...]) -> "ContextSelection":
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


_CATEGORY_BY_KIND = {
    InternalContextKind.VAULT_NOTE: "related_vault_notes",
    InternalContextKind.REPOSITORY: "related_repositories",
    InternalContextKind.FEATURE: "related_features",
    InternalContextKind.KNOWN_SOURCE: "known_sources",
    InternalContextKind.KNOWN_EVIDENCE: "known_evidence",
    InternalContextKind.KNOWN_GAP: "known_gaps",
    InternalContextKind.KNOWN_DECISION: "known_decisions",
}
_KIND_BY_CATEGORY = {field: kind for kind, field in _CATEGORY_BY_KIND.items()}
_CATEGORY_FIELDS = tuple(_KIND_BY_CATEGORY)


def _sha256_text(value: Any, field: str) -> str:
    text = require_text(value, field)
    if _SHA256_RE.fullmatch(text) is None:
        raise ValueError(f"{field} must be 64 lowercase hex characters")
    return text
```

Implement `InternalContextSnapshot` as a frozen/slots dataclass with the exact fields from the spec. Its `build()` algorithm is:

```python
generated = require_aware_iso8601(generated_at, "generated_at")
intent_id = require_text(research_intent_id, "research_intent_id")
scope_id = require_text(territorial_scope_id, "territorial_scope_id")
question_ref = _optional_text(question_profile_ref, "question_profile_ref")
missing = require_string_list(list(missing_context), "missing_context")
ordered = tuple(sorted(selections, key=lambda item: (item.kind.value, item.context_id)))
buckets = {field: [] for field in _CATEGORY_FIELDS}
for selection in ordered:
    buckets[_CATEGORY_BY_KIND[selection.kind]].append(selection)
```

Construct a provisional snapshot with `snapshot_id="0" * 64`, compute:

```python
snapshot_id = sha256_json(provisional._payload_without_id())
```

and return a second immutable instance with that real ID. `_payload_without_id()` must serialize all snapshot fields except `snapshot_id`, with category lists already sorted by `(kind, context_id)`. `to_dict()` returns that payload plus `snapshot_id`.

`from_dict()` must execute this exact validation sequence:

```python
fields = {
    "contract_version", "snapshot_version", "snapshot_id", "generated_at",
    "research_intent_id", "question_profile_ref", "territorial_scope_id",
    "related_vault_notes", "related_repositories", "related_features",
    "known_sources", "known_evidence", "known_gaps", "known_decisions",
    "missing_context",
}
require_fields(payload, required=fields, allowed=fields)
```

Then:

1. require `contract_version == CONTRACT_VERSION` and `snapshot_version == SNAPSHOT_VERSION`;
2. validate `generated_at`, IDs and optional `question_profile_ref`;
3. require every category to be a JSON list;
4. parse every category item with `ContextSelection.from_dict()`;
5. require each selection kind to match its category (`repository` only in `related_repositories`, etc.);
6. sort each category by `context_id` before constructing the object;
7. validate supplied ID with `_sha256_text()`;
8. recompute `sha256_json(snapshot._payload_without_id())`;
9. raise `ValueError("snapshot_id mismatch")` when recomputed and supplied IDs differ.

Do not include `snapshot_id` in the hash input.

- [ ] **Step 4: Verify + commit Task 2**

```bash
pytest tests/test_internal_context.py -q
pytest -q
python -m compileall -q src
git add src/andes_context_os/internal_context.py tests/test_internal_context.py
git commit -m "feat: add content-addressed internal context snapshot"
```

---

### Task 3: Deterministic adapter and restricted-data boundary

**Files:**
- Create: `src/andes_context_os/adapters/__init__.py`
- Create: `src/andes_context_os/adapters/internal_context.py`
- Create: `tests/test_internal_context_adapter.py`

**Interfaces:**
- Produces: `InternalContextAdapter.snapshot(intent, scope, catalog, *, generated_at) -> InternalContextSnapshot`.

- [ ] **Step 1: Write RED adapter tests with exact fixtures**

```python
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
    "admin_units": [{"country_code": "AR", "admin_level": "1", "official_code": "J", "name": "San Juan", "source_id": "ar_ign_admin"}],
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


def record(context_id, *, kind="repository", domains=None, activities=None, territory_refs=None, sensitivity="public"):
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


def build_snapshot(*records):
    return InternalContextAdapter().snapshot(
        ResearchIntent.from_dict(INTENT),
        TerritorialScope.from_dict(SCOPE),
        InternalContextCatalog.from_dict({"catalog_version": "0.1", "records": list(records)}),
        generated_at="2026-08-30T10:00:00-03:00",
    )


def test_territorial_record_requires_exact_match():
    snapshot = build_snapshot(record("peru-only", territory_refs=["PE"]))
    assert snapshot.related_repositories == ()


def test_exact_corridor_match_preserves_all_reasons():
    snapshot = build_snapshot(record("agua-negra", territory_refs=["agua-negra-v1"]))
    assert [reason.value for reason in snapshot.related_repositories[0].match_reasons] == [
        "activity_match", "domain_match", "territory_match"
    ]


def test_territory_only_record_can_match():
    snapshot = build_snapshot(record("corridor-note", kind="vault_note", domains=[], activities=[], territory_refs=["agua-negra-v1"]))
    assert [reason.value for reason in snapshot.related_vault_notes[0].match_reasons] == ["territory_match"]
```

- [ ] **Step 2: Run RED**

```bash
pytest tests/test_internal_context_adapter.py -q
```

- [ ] **Step 3: Implement adapter**

Create empty `src/andes_context_os/adapters/__init__.py` and:

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
    refs.update(unit.official_code for unit in scope.admin_units if unit.official_code is not None)
    refs.update(scope.project_refs)
    refs.update(scope.corridor_refs)
    refs.update(scope.segment_refs)
    if scope.geometry_ref is not None:
        refs.add(scope.geometry_ref)
    return frozenset(refs)


def _match_reasons(record: InternalContextRecord, intent: ResearchIntent, scope_refs: frozenset[str]) -> tuple[MatchReason, ...]:
    reasons: list[MatchReason] = []
    if intent.domain in record.domains:
        reasons.append(MatchReason.DOMAIN_MATCH)
    if intent.activity in record.activities:
        reasons.append(MatchReason.ACTIVITY_MATCH)
    if set(record.territory_refs) & scope_refs:
        reasons.append(MatchReason.TERRITORY_MATCH)
    return tuple(sorted(reasons, key=lambda item: item.value))


def _eligible(record: InternalContextRecord, reasons: tuple[MatchReason, ...]) -> bool:
    reason_set = set(reasons)
    territory_match = MatchReason.TERRITORY_MATCH in reason_set
    territorial_gate = not record.territory_refs or territory_match
    semantic_gate = (
        bool(reason_set & {MatchReason.DOMAIN_MATCH, MatchReason.ACTIVITY_MATCH})
        if record.domains or record.activities
        else territory_match
    )
    return territorial_gate and semantic_gate


class InternalContextAdapter:
    def snapshot(self, intent: ResearchIntent, scope: TerritorialScope, catalog: InternalContextCatalog, *, generated_at: str) -> InternalContextSnapshot:
        scope_refs = _scope_refs(scope)
        selections: list[ContextSelection] = []
        restricted_omitted = False
        for item in catalog.records:
            reasons = _match_reasons(item, intent, scope_refs)
            if not _eligible(item, reasons):
                continue
            if item.sensitivity is ContextSensitivity.RESTRICTED:
                restricted_omitted = True
                continue
            selections.append(ContextSelection.from_record(item, reasons))
        missing: list[str] = []
        if not selections:
            missing.append(NO_MATCH_MESSAGE)
        if restricted_omitted:
            missing.append(RESTRICTED_OMISSION_MESSAGE)
        return InternalContextSnapshot.build(
            generated_at=generated_at,
            research_intent_id=intent.intent_id,
            question_profile_ref=intent.question_profile_ref,
            territorial_scope_id=scope.scope_id,
            selections=tuple(selections),
            missing_context=tuple(missing),
        )
```

- [ ] **Step 4: Add privacy/determinism tests**

```python
def test_restricted_match_is_non_emitting_and_non_leaking():
    secret_id = "restricted-secret-id"
    snapshot = build_snapshot(record(secret_id, kind="known_evidence", territory_refs=["agua-negra-v1"], sensitivity="restricted"))
    text = repr(snapshot.to_dict())
    assert snapshot.known_evidence == ()
    assert snapshot.missing_context == (
        "no internal context matched the current intent and territorial scope",
        "restricted internal context was omitted",
    )
    assert secret_id not in text
    assert f"ref:{secret_id}" not in text
    assert f"Summary {secret_id}" not in text


def test_restricted_message_is_emitted_once():
    snapshot = build_snapshot(
        record("secret-1", territory_refs=["agua-negra-v1"], sensitivity="restricted"),
        record("secret-2", territory_refs=["agua-negra-v1"], sensitivity="restricted"),
    )
    assert snapshot.missing_context.count("restricted internal context was omitted") == 1


def test_catalog_order_does_not_change_snapshot():
    a = record("a-record")
    b = record("b-record")
    assert build_snapshot(b, a).to_dict() == build_snapshot(a, b).to_dict()


def test_output_has_no_scores_or_operational_authorizations():
    text = repr(build_snapshot(record("generic")).to_dict())
    for forbidden in (
        "relevance_score", "confidence_score", "risk_score", "truth_score",
        "safe_to_travel", "road_open", "route_authorized", "community_approved",
    ):
        assert forbidden not in text
```

- [ ] **Step 5: Verify + commit Task 3**

```bash
pytest tests/test_internal_context_adapter.py -q
pytest -q
python -m compileall -q src
git add src/andes_context_os/adapters tests/test_internal_context_adapter.py
git commit -m "feat: add deterministic internal context adapter"
```

---

### Task 4: Public-safe sample, README and release gate

**Files:**
- Create: `data/internal_context.example.v0.1.json`
- Create: `tests/test_internal_context_release.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: public V0.2 contracts.
- Produces: safe sample catalog, accurate README claims, feature-branch CI evidence.

- [ ] **Step 1: Write RED release tests**

```python
from pathlib import Path

from andes_context_os.internal_context import ContextSensitivity, InternalContextCatalog

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_PATH = ROOT / "data" / "internal_context.example.v0.1.json"
README_PATH = ROOT / "README.md"


def test_example_catalog_loads_and_is_public_safe():
    catalog = InternalContextCatalog.load(EXAMPLE_PATH)
    assert len(catalog.records) == 3
    assert all(record.sensitivity is ContextSensitivity.PUBLIC for record in catalog.records)
    serialized = repr(catalog.to_dict()).lower()
    for forbidden in ("password", "api_key", "access_token", "cookie", "private aoi"):
        assert forbidden not in serialized


def test_readme_describes_v02_without_live_connector_claims():
    text = README_PATH.read_text(encoding="utf-8")
    assert "V0.2 — Internal Context Adapter" in text
    assert "local deterministic catalog" in text
    assert "does not read GitHub or the private vault" in text
    assert "internal context match != evidence validation" in text
```

- [ ] **Step 2: Run RED**

```bash
pytest tests/test_internal_context_release.py -q
```

- [ ] **Step 3: Create exact public-safe catalog**

`data/internal_context.example.v0.1.json`:

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

- [ ] **Step 4: Add exact README section**

````markdown
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
````

Edit any older README sentence that contradicts this local V0.2 capability; retain explicit non-goals for live GitHub/vault retrieval, private-data ingestion, evidence promotion and route-safety analysis.

- [ ] **Step 5: Verify locally and commit Task 4**

```bash
pytest tests/test_internal_context_release.py -q
python -m pip install --no-build-isolation -e ".[dev]"
pytest -q
python -m compileall -q src
git add data/internal_context.example.v0.1.json README.md tests/test_internal_context_release.py
git commit -m "docs: publish internal context adapter v0.2"
```

If external DNS is available, also run the canonical CI install path:

```bash
python -m pip install -e ".[dev]"
pytest -q
```

A DNS failure is an environment limitation, not positive verification.

- [ ] **Step 6: Verify GitHub Actions for exact HEAD**

Capture the exact branch HEAD first:

```bash
git rev-parse HEAD
```

Then inspect the GitHub Actions `tests` run whose `head_branch` is `feat/internal-context-adapter` and whose `head_sha` exactly equals that command output. Require `status=completed`, `conclusion=success`, successful `pytest` step, and zero failures in the job log.

- [ ] **Step 7: Final requirement gate before PR/integration**

Verify each item and record the actual result:

```text
strict record/catalog contracts
malformed records fail with ValueError
exact categorical match reasons
territorial-specific gate
no fuzzy/proximity/bbox matching
no numeric score
restricted records non-emitting
restricted omission non-leaking
empty context explicit
deterministic ordering
content-addressed snapshot_id
DiscoveryRun unchanged
no new runtime dependency
public-safe sample only
README avoids live GitHub/vault claims
full tests green
feature-branch CI green
```

If any requirement is not satisfied, stop before PR/integration and fix it with a new RED/GREEN cycle.
