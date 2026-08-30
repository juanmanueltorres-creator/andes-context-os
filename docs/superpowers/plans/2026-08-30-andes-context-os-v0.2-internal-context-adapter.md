# Andes Context OS V0.2 — Internal Context Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, dependency-free internal-context adapter that converts a strict local reference catalog into an immutable, content-addressed `InternalContextSnapshot` for a `ResearchIntent` + `TerritorialScope` pair.

**Architecture:** Contracts, serialization and content hashing live in `src/andes_context_os/internal_context.py`; exact selection logic lives in `src/andes_context_os/adapters/internal_context.py`. The adapter never reads GitHub, the private vault, a database, an LLM or an external service. It emits categorical match reasons only and never promotes matched context into evidence or authorization.

**Tech Stack:** Python 3.11+, stdlib only (`dataclasses`, `enum.StrEnum`, `json`, `pathlib`, `re`), existing `andes_context_os.common` helpers, existing `sha256_json()`, pytest >=8,<9, GitHub Actions Python 3.11.

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
- Snapshot category order is deterministic and independent of input catalog order.
- `snapshot_id = sha256_json(serialized_snapshot_without_snapshot_id)`.
- `DiscoveryRun` schema is unchanged; callers may store `snapshot_id` in existing lineage refs.
- Baseline: V0.1 has 117 tests green. Preserve the full suite after every task.

## File map

```text
src/andes_context_os/internal_context.py
    enums + InternalContextRecord + InternalContextCatalog
    MatchReason + ContextSelection + InternalContextSnapshot

src/andes_context_os/adapters/__init__.py
src/andes_context_os/adapters/internal_context.py
    exact scope refs + eligibility + restricted omission + snapshot orchestration

data/internal_context.example.v0.1.json
    fictitious/public-safe sample only

tests/test_internal_context.py
    contract/catalog/snapshot behavior

tests/test_internal_context_adapter.py
    matching/privacy/determinism behavior

tests/test_internal_context_release.py
    example + README release claims

README.md
    V0.2 public surface and explicit non-goals
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

Create `tests/test_internal_context.py`:

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

- [ ] **Step 2: Run RED**

```bash
pytest tests/test_internal_context.py -q
```

Expected: `ModuleNotFoundError: No module named 'andes_context_os.internal_context'`.

- [ ] **Step 3: Implement the minimal record contract**

Create `src/andes_context_os/internal_context.py` with:

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
    if value is None:
        return None
    return require_text(value, field)


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

Expected: record tests pass.

- [ ] **Step 5: Add RED catalog tests, including malformed record objects**

Append:

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


def test_catalog_rejects_unknown_version():
    with pytest.raises(ValueError, match="catalog_version"):
        InternalContextCatalog.from_dict({**VALID_CATALOG, "catalog_version": "9.9"})


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

Expected: failures because `InternalContextCatalog` is not implemented.

- [ ] **Step 7: Implement the catalog exactly**

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
        return {
            "catalog_version": self.catalog_version,
            "records": [record.to_dict() for record in self.records],
        }
```

- [ ] **Step 8: Verify Task 1 and regression suite**

```bash
pytest tests/test_internal_context.py -q
pytest -q
python -m compileall -q src
```

Expected: Task 1 green, existing 117 tests still green, compile exit 0.

- [ ] **Step 9: Commit Task 1**

```bash
git add src/andes_context_os/internal_context.py tests/test_internal_context.py
git commit -m "feat: add internal context catalog contracts"
```

---

### Task 2: Selection projection + content-addressed snapshot

**Files:**
- Modify: `src/andes_context_os/internal_context.py`
- Modify: `tests/test_internal_context.py`

**Interfaces:**
- Produces: `MatchReason`, `ContextSelection`, `InternalContextSnapshot.build()`, `InternalContextSnapshot.from_dict()`, `InternalContextSnapshot.to_dict()`.

- [ ] **Step 1: Add RED selection tests**

Append imports and tests:

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


def test_selection_round_trips_and_sorts_reasons():
    payload = {**VALID_SELECTION, "match_reasons": ["domain_match", "activity_match"]}
    selection = ContextSelection.from_dict(payload)
    assert selection.match_reasons == (MatchReason.ACTIVITY_MATCH, MatchReason.DOMAIN_MATCH)
    assert selection.to_dict()["match_reasons"] == ["activity_match", "domain_match"]


def test_selection_rejects_empty_match_reasons():
    with pytest.raises(ValueError, match="match_reasons"):
        ContextSelection.from_dict({**VALID_SELECTION, "match_reasons": []})


def test_selection_rejects_numeric_score_field():
    with pytest.raises(ValueError, match="unknown fields: relevance_score"):
        ContextSelection.from_dict({**VALID_SELECTION, "relevance_score": 0.9})
```

- [ ] **Step 2: Run selection RED**

```bash
pytest tests/test_internal_context.py -q
```

Expected: missing `ContextSelection` / `MatchReason`.

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
        fields = {"context_id", "kind", "title", "reference", "summary", "match_reasons", "limitations"}
        require_fields(payload, required=fields, allowed=fields)
        raw_reasons = require_string_list(payload["match_reasons"], "match_reasons", allow_empty=False)
        reasons = tuple(sorted(
            (_enum_value(MatchReason, item, "match_reasons") for item in raw_reasons),
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
```

- [ ] **Step 4: Add RED snapshot/hash tests**

Append:

```python
def build_snapshot(*, selections=(VALID_SELECTION,), missing_context=(), generated_at="2026-08-30T10:00:00-03:00"):
    return InternalContextSnapshot.build(
        generated_at=generated_at,
        research_intent_id="intent-filo-access-001",
        question_profile_ref="question-radar:profile-001",
        territorial_scope_id="scope-ar-j",
        selections=tuple(ContextSelection.from_dict(item) for item in selections),
        missing_context=tuple(missing_context),
    )


def test_snapshot_id_is_64_lowercase_hex_and_round_trips():
    snapshot = build_snapshot()
    assert len(snapshot.snapshot_id) == 64
    assert snapshot.snapshot_id == snapshot.snapshot_id.lower()
    assert set(snapshot.snapshot_id) <= set("0123456789abcdef")
    assert InternalContextSnapshot.from_dict(snapshot.to_dict()).to_dict() == snapshot.to_dict()


def test_snapshot_id_changes_when_generated_at_changes():
    assert build_snapshot(generated_at="2026-08-30T10:00:00-03:00").snapshot_id != build_snapshot(generated_at="2026-08-30T10:01:00-03:00").snapshot_id


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
```

- [ ] **Step 5: Run snapshot RED**

```bash
pytest tests/test_internal_context.py -q
```

Expected: missing `InternalContextSnapshot`.

- [ ] **Step 6: Implement canonical snapshot construction and validation**

Add `from andes_context_os.hashing import sha256_json`, then:

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
_KIND_BY_CATEGORY = {field: kind for kind, field in _CATEGORY_BY_KIND.items()}
_CATEGORY_FIELDS = tuple(_KIND_BY_CATEGORY)


def _sha256_text(value: Any, field: str) -> str:
    text = require_text(value, field)
    if _SHA256_RE.fullmatch(text) is None:
        raise ValueError(f"{field} must be 64 lowercase hex characters")
    return text


def _parse_selection_list(value: Any, field: str, expected_kind: InternalContextKind) -> tuple[ContextSelection, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    parsed: list[ContextSelection] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError(f"each {field} item must be an object")
        selection = ContextSelection.from_dict(item)
        if selection.kind is not expected_kind:
            raise ValueError(f"{field} contains incompatible kind")
        parsed.append(selection)
    return tuple(sorted(parsed, key=lambda item: item.context_id))


@dataclass(frozen=True, slots=True)
class InternalContextSnapshot:
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

    @classmethod
    def build(
        cls,
        *,
        generated_at: str,
        research_intent_id: str,
        question_profile_ref: str | None,
        territorial_scope_id: str,
        selections: tuple[ContextSelection, ...],
        missing_context: tuple[str, ...],
    ) -> "InternalContextSnapshot":
        generated = require_aware_iso8601(generated_at, "generated_at")
        intent_id = require_text(research_intent_id, "research_intent_id")
        scope_id = require_text(territorial_scope_id, "territorial_scope_id")
        question_ref = _optional_text(question_profile_ref, "question_profile_ref")
        missing = require_string_list(list(missing_context), "missing_context")
        ordered = tuple(sorted(selections, key=lambda item: (item.kind.value, item.context_id)))
        buckets = {field: [] for field in _CATEGORY_FIELDS}
        for selection in ordered:
            buckets[_CATEGORY_BY_KIND[selection.kind]].append(selection)
        provisional = cls(
            contract_version=CONTRACT_VERSION,
            snapshot_version=SNAPSHOT_VERSION,
            snapshot_id="0" * 64,
            generated_at=generated,
            research_intent_id=intent_id,
            question_profile_ref=question_ref,
            territorial_scope_id=scope_id,
            related_vault_notes=tuple(buckets["related_vault_notes"]),
            related_repositories=tuple(buckets["related_repositories"]),
            related_features=tuple(buckets["related_features"]),
            known_sources=tuple(buckets["known_sources"]),
            known_evidence=tuple(buckets["known_evidence"]),
            known_gaps=tuple(buckets["known_gaps"]),
            known_decisions=tuple(buckets["known_decisions"]),
            missing_context=missing,
        )
        snapshot_id = sha256_json(provisional._payload_without_id())
        return cls(**{**provisional.__dict__, "snapshot_id": snapshot_id})

    def _payload_without_id(self) -> dict[str, Any]:
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

Because `slots=True` dataclasses do not expose `__dict__`, implement the final `build()` return explicitly instead of using the illustrative `provisional.__dict__` expression above:

```python
return cls(
    contract_version=provisional.contract_version,
    snapshot_version=provisional.snapshot_version,
    snapshot_id=snapshot_id,
    generated_at=provisional.generated_at,
    research_intent_id=provisional.research_intent_id,
    question_profile_ref=provisional.question_profile_ref,
    territorial_scope_id=provisional.territorial_scope_id,
    related_vault_notes=provisional.related_vault_notes,
    related_repositories=provisional.related_repositories,
    related_features=provisional.related_features,
    known_sources=provisional.known_sources,
    known_evidence=provisional.known_evidence,
    known_gaps=provisional.known_gaps,
    known_decisions=provisional.known_decisions,
    missing_context=provisional.missing_context,
)
```

Implement `to_dict()` as:

```python
def to_dict(self) -> dict[str, Any]:
    payload = self._payload_without_id()
    payload["snapshot_id"] = self.snapshot_id
    return payload
```

Implement `from_dict()` with these exact rules:

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

Then validate versions/timestamps/IDs, parse every category with `_parse_selection_list()`, validate `snapshot_id` with `_sha256_text()`, construct the object, recompute `sha256_json(snapshot._payload_without_id())`, and raise `ValueError("snapshot_id mismatch")` unless it equals the supplied ID. Do not hash the supplied `snapshot_id`.

- [ ] **Step 7: Verify Task 2 and regression suite**

```bash
pytest tests/test_internal_context.py -q
pytest -q
python -m compileall -q src
```

Expected: Task 2 green, all prior tests green, compile exit 0.

- [ ] **Step 8: Commit Task 2**

```bash
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
- Consumes: `ResearchIntent`, `TerritorialScope`, `InternalContextCatalog`, `InternalContextRecord`, `ContextSensitivity`, `ContextSelection`, `InternalContextSnapshot`, `MatchReason`.
- Produces: `InternalContextAdapter.snapshot(intent, scope, catalog, *, generated_at) -> InternalContextSnapshot`.

- [ ] **Step 1: Write RED matching tests**

Create fixtures for one logistics/access intent and an `AR` / San Juan / `agua-negra-v1` corridor scope, then add these tests:

```python
def test_generic_record_matches_domain_and_activity():
    snapshot = build_snapshot(record("generic"))
    selection = snapshot.related_repositories[0]
    assert [reason.value for reason in selection.match_reasons] == ["activity_match", "domain_match"]


def test_territorial_record_requires_exact_territory_match():
    snapshot = build_snapshot(record("peru-only", territory_refs=["PE"]))
    assert snapshot.related_repositories == ()
    assert snapshot.missing_context == (
        "no internal context matched the current intent and territorial scope",
    )


def test_exact_corridor_match_adds_territory_reason():
    snapshot = build_snapshot(record("agua-negra", territory_refs=["agua-negra-v1"]))
    assert [reason.value for reason in snapshot.related_repositories[0].match_reasons] == [
        "activity_match", "domain_match", "territory_match"
    ]


def test_territory_only_record_matches_when_semantic_vocabularies_are_empty():
    snapshot = build_snapshot(record(
        "corridor-note", kind="vault_note", domains=[], activities=[], territory_refs=["agua-negra-v1"]
    ))
    assert [reason.value for reason in snapshot.related_vault_notes[0].match_reasons] == ["territory_match"]
```

The local `record()` fixture must produce strict `InternalContextRecord` dicts; `build_snapshot()` must parse `ResearchIntent`, `TerritorialScope`, `InternalContextCatalog` and call `InternalContextAdapter().snapshot(..., generated_at="2026-08-30T10:00:00-03:00")`.

- [ ] **Step 2: Run adapter RED**

```bash
pytest tests/test_internal_context_adapter.py -q
```

Expected: module missing for `andes_context_os.adapters.internal_context`.

- [ ] **Step 3: Implement exact matching and eligibility**

Create empty `src/andes_context_os/adapters/__init__.py`, then `src/andes_context_os/adapters/internal_context.py`:

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
    if record.domains or record.activities:
        semantic_gate = bool(reason_set & {MatchReason.DOMAIN_MATCH, MatchReason.ACTIVITY_MATCH})
    else:
        semantic_gate = territory_match
    return territorial_gate and semantic_gate


class InternalContextAdapter:
    def snapshot(
        self,
        intent: ResearchIntent,
        scope: TerritorialScope,
        catalog: InternalContextCatalog,
        *,
        generated_at: str,
    ) -> InternalContextSnapshot:
        refs = _scope_refs(scope)
        selections: list[ContextSelection] = []
        restricted_omitted = False
        for record in catalog.records:
            reasons = _match_reasons(record, intent, refs)
            if not _eligible(record, reasons):
                continue
            if record.sensitivity is ContextSensitivity.RESTRICTED:
                restricted_omitted = True
                continue
            selections.append(ContextSelection.from_record(record, reasons))

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

- [ ] **Step 4: Run matching GREEN**

```bash
pytest tests/test_internal_context_adapter.py -q
```

Expected: matching tests pass.

- [ ] **Step 5: Add RED privacy/determinism tests**

Append:

```python
def test_restricted_match_is_omitted_without_metadata_leakage():
    secret_id = "restricted-secret-id"
    snapshot = build_snapshot(record(secret_id, kind="known_evidence", territory_refs=["agua-negra-v1"], sensitivity="restricted"))
    serialized = repr(snapshot.to_dict())
    assert snapshot.known_evidence == ()
    assert snapshot.missing_context == (
        "no internal context matched the current intent and territorial scope",
        "restricted internal context was omitted",
    )
    assert secret_id not in serialized
    assert f"ref:{secret_id}" not in serialized
    assert f"Summary {secret_id}" not in serialized


def test_restricted_omission_is_reported_once():
    snapshot = build_snapshot(
        record("secret-1", territory_refs=["agua-negra-v1"], sensitivity="restricted"),
        record("secret-2", territory_refs=["agua-negra-v1"], sensitivity="restricted"),
    )
    assert snapshot.missing_context.count("restricted internal context was omitted") == 1


def test_public_match_plus_restricted_match_keeps_public_context_and_generic_warning():
    snapshot = build_snapshot(
        record("public-record"),
        record("secret-record", territory_refs=["agua-negra-v1"], sensitivity="restricted"),
    )
    assert snapshot.related_repositories[0].context_id == "public-record"
    assert snapshot.missing_context == ("restricted internal context was omitted",)


def test_catalog_order_does_not_change_snapshot_or_id():
    a = record("a-record")
    b = record("b-record")
    first = build_snapshot(b, a)
    second = build_snapshot(a, b)
    assert first.to_dict() == second.to_dict()
    assert first.snapshot_id == second.snapshot_id


def test_adapter_output_has_no_scores_or_operational_authorizations():
    text = repr(build_snapshot(record("generic")).to_dict())
    for forbidden in (
        "relevance_score", "confidence_score", "risk_score", "truth_score",
        "safe_to_travel", "road_open", "route_authorized", "community_approved",
    ):
        assert forbidden not in text
```

- [ ] **Step 6: Verify Task 3 and regression suite**

```bash
pytest tests/test_internal_context_adapter.py -q
pytest -q
python -m compileall -q src
```

Expected: Task 3 green, full suite green, compile exit 0.

- [ ] **Step 7: Commit Task 3**

```bash
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
- Consumes: `InternalContextCatalog.load()` and public V0.2 contracts.
- Produces: a safe sample catalog, accurate README claims, feature-branch CI evidence.

- [ ] **Step 1: Write RED release tests**

Create:

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

- [ ] **Step 2: Run release RED**

```bash
pytest tests/test_internal_context_release.py -q
```

Expected: sample and README assertions fail.

- [ ] **Step 3: Create the exact fictitious/public-safe catalog**

Create `data/internal_context.example.v0.1.json` with three `sensitivity: "public"` records:

1. `example-geoplatform-access` — kind `repository`, domains `["logistics"]`, activities `["access", "route_planning"]`, no territory refs, limitation that it does not establish current road condition.
2. `example-corridor-note` — kind `vault_note`, empty domains/activities, territory ref `["example-corridor-v1"]`, limitation `"Fictitious example only"`.
3. `example-road-freshness-gap` — kind `known_gap`, domain `["access"]`, activity `["road_condition"]`, no territory refs, limitation that the gap is not a live road-status observation.

Use only fictitious references such as `repo:example-geoplatform#access`, `note:example-corridor-research`, and `gap:example-road-freshness`. Use `reviewed_at = "2026-08-30T09:00:00-03:00"` on all three. Do not include private URLs, real private note bodies, AOIs, credentials or contact data.

- [ ] **Step 4: Add the exact README V0.2 boundary**

Add this section after the existing V0.1 flow:

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

Keep the existing V0.1 limitations, but edit any wording that would falsely imply the new local adapter does not exist. Do not claim live vault/GitHub retrieval, private-data ingestion, evidence promotion or route safety analysis.

- [ ] **Step 5: Run release GREEN**

```bash
pytest tests/test_internal_context_release.py -q
```

Expected: release tests pass.

- [ ] **Step 6: Run final local gate**

```bash
python -m pip install --no-build-isolation -e ".[dev]"
pytest -q
python -m compileall -q src
```

Expected: editable build succeeds, full V0.1+V0.2 suite has zero failures, compile exit 0.

If network is available, also run the same isolated install command CI uses:

```bash
python -m pip install -e ".[dev]"
pytest -q
```

A local DNS failure is not a pass; the network-enabled install gate is the GitHub Actions run.

- [ ] **Step 7: Commit Task 4**

```bash
git add data/internal_context.example.v0.1.json README.md tests/test_internal_context_release.py
git commit -m "docs: publish internal context adapter v0.2"
```

- [ ] **Step 8: Verify GitHub Actions for the exact feature-branch HEAD**

Required evidence:

```text
workflow: tests
head_branch: feat/internal-context-adapter
head_sha: <Task 4 commit SHA>
status: completed
conclusion: success
pytest step: success
final pytest output: zero failures
```

Do not infer success from workflow-file existence.

- [ ] **Step 9: Run final requirement checklist before PR/integration**

```text
strict record/catalog contracts                     PASS/FAIL
malformed records fail with ValueError               PASS/FAIL
exact categorical match reasons                      PASS/FAIL
territorial-specific gate                            PASS/FAIL
no fuzzy/proximity/bbox matching                     PASS/FAIL
no numeric score                                     PASS/FAIL
restricted records non-emitting                      PASS/FAIL
restricted omission non-leaking                      PASS/FAIL
empty context explicit                               PASS/FAIL
deterministic ordering                               PASS/FAIL
content-addressed snapshot_id                        PASS/FAIL
DiscoveryRun unchanged                               PASS/FAIL
no new runtime dependency                            PASS/FAIL
public-safe sample only                              PASS/FAIL
README avoids live GitHub/vault claims               PASS/FAIL
full tests green                                     PASS/FAIL
feature-branch CI green                              PASS/FAIL
```

If any line is `FAIL`, stop before PR/integration and fix it with a new RED/GREEN cycle.
