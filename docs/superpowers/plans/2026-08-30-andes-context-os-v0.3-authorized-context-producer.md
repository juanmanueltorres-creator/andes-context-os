# Andes Context OS V0.3 — Authorized Context Producer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a strict allowlist-first producer that resolves only explicitly authorized internal references, emits unchanged curated `InternalContextRecord` objects, and preserves exact source provenance through sanitized SHA-256 receipts.

**Architecture:** V0.3 adds one stdlib-only producer boundary before the existing V0.2.1 selector. A private manifest supplies exact opaque locators plus curated context metadata; caller-injected resolvers return exact bytes; the producer verifies optional identity/hash pins and returns a deterministic `InternalContextCatalog`, successful receipts, and sanitized failures without changing downstream context/evidence semantics.

**Tech Stack:** Python 3.11+, stdlib (`dataclasses`, `enum`, `hashlib`, `json`, `pathlib`, `typing`), pytest 8.x. Runtime dependencies remain empty.

**Spec:** `docs/superpowers/specs/2026-08-30-andes-context-os-v0.3-authorized-context-producer-design.md`

## Global Constraints

- `manifest_version = "0.1"`.
- Reuse `InternalContextRecord` and `InternalContextCatalog` unchanged.
- Production `dependencies = []` remains unchanged.
- No GitHub SDK, MCP client, HTTP library, database client, LLM SDK, embeddings, fuzzy matching, repository/vault search, tree enumeration, recursive scan, glob expansion, or link following.
- Only manifest-listed `source_locator` values may reach a resolver.
- `source_locator` and resolved `source_identity` are exact opaque strings: validate them without trimming or normalization; reject surrounding whitespace rather than silently changing identity.
- Source bytes are hashed exactly as returned; no newline, Unicode, JSON, Markdown, or whitespace normalization.
- Manifest metadata is curated; source content never generates or rewrites title, summary, domains, activities, territory refs, tags, sensitivity, limitations, or `reviewed_at`.
- `source resolved successfully now != source reviewed semantically now`; never update `reviewed_at` implicitly.
- Failed entries emit neither record nor receipt.
- Resolver exceptions become `resolution_failed`; raw exception text is never serialized.
- Production serialization omits source locator and source bytes. Failure serialization also omits expected/actual identities, expected/actual hashes, and exception text.
- No aggregate confidence, relevance, freshness, risk, or truth score.
- Real manifests, receipts, private paths/refs, AOIs, contacts, credentials, and sensitive operational details never enter the public repo.

## File Structure

- Create `src/andes_context_os/producers/__init__.py` — stable package exports only.
- Create `src/andes_context_os/producers/authorized_context.py` — manifest contracts, resolver protocol, production contracts, producer.
- Create `tests/test_authorized_context_manifest.py` — strict manifest parsing.
- Create `tests/test_authorized_context_producer.py` — success, pins, failures, privacy, determinism.
- Create `data/authorized_context.example.v0.1.json` — two fictitious/public-safe entries.
- Create `tests/test_authorized_context_release.py` — release/privacy/dependency gates.
- Modify `README.md` — concise V0.3 contract and non-goals.
- Do not modify `src/andes_context_os/internal_context.py`, `src/andes_context_os/adapters/internal_context.py`, or `DiscoveryRun`.

---

### Task 1: Strict Authorized Manifest Contracts

**Files:**
- Create: `src/andes_context_os/producers/__init__.py`
- Create: `src/andes_context_os/producers/authorized_context.py`
- Create: `tests/test_authorized_context_manifest.py`

**Interfaces:**
- Consumes: `InternalContextRecord.from_dict()` / `.to_dict()`, `require_fields()`, `require_text()`.
- Produces:
  - `MANIFEST_VERSION = "0.1"`
  - `AuthorizedContextManifestEntry.from_dict()` / `.to_dict()`
  - `AuthorizedContextManifest.from_dict()` / `.load()` / `.to_dict()`

- [ ] **Step 1: Write RED manifest tests**

Create `tests/test_authorized_context_manifest.py`:

```python
import json

import pytest

from andes_context_os.producers.authorized_context import (
    AuthorizedContextManifest,
    AuthorizedContextManifestEntry,
)

CONTEXT = {
    "contract_version": "0.1",
    "context_id": "example-access-context",
    "kind": "known_gap",
    "title": "Example access freshness gap",
    "reference": "example:access-gap",
    "summary": "A fictitious gap used to test authorized context production.",
    "domains": ["logistics"],
    "activities": ["access"],
    "territory_refs": ["corridor:example-corridor-v1"],
    "tags": ["example"],
    "sensitivity": "public",
    "reviewed_at": "2026-08-30T10:00:00-03:00",
    "limitations": ["Fictitious example only."],
}


def entry_payload(**overrides):
    payload = {
        "entry_id": "entry-example-access",
        "resolver_id": "fixture",
        "source_locator": "example://context/access-gap",
        "expected_source_identity": "example-source:access-gap:v1",
        "expected_content_sha256": "0" * 64,
        "context": CONTEXT,
    }
    payload.update(overrides)
    return payload


def test_manifest_entry_round_trip_preserves_curated_context():
    entry = AuthorizedContextManifestEntry.from_dict(entry_payload())
    assert entry.context.context_id == "example-access-context"
    assert entry.to_dict() == entry_payload()


def test_manifest_is_canonical_by_context_id_then_entry_id():
    second = {**CONTEXT, "context_id": "a-context", "reference": "example:a"}
    manifest = AuthorizedContextManifest.from_dict({
        "manifest_version": "0.1",
        "entries": [entry_payload(), entry_payload(entry_id="entry-a", source_locator="example://a", context=second)],
    })
    assert [item.context.context_id for item in manifest.entries] == ["a-context", "example-access-context"]
    assert AuthorizedContextManifest.from_dict(manifest.to_dict()) == manifest


def test_manifest_load_reads_local_json(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"manifest_version": "0.1", "entries": []}), encoding="utf-8")
    assert AuthorizedContextManifest.load(path).entries == ()
```

- [ ] **Step 2: Run RED**

```bash
pytest -q tests/test_authorized_context_manifest.py
```

Expected: import/collection failure because the producer module does not exist.

- [ ] **Step 3: Implement strict manifest contracts**

Create `authorized_context.py` with this contract shape:

```python
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from andes_context_os.common import require_fields, require_text
from andes_context_os.internal_context import InternalContextRecord

MANIFEST_VERSION = "0.1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _require_exact_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    if value != value.strip():
        raise ValueError(f"{field} must not contain surrounding whitespace")
    return value


def _optional_exact_text(value: Any, field: str) -> str | None:
    return None if value is None else _require_exact_text(value, field)


def _optional_sha256(value: Any, field: str) -> str | None:
    if value is None:
        return None
    text = _require_exact_text(value, field)
    if _SHA256_RE.fullmatch(text) is None:
        raise ValueError(f"{field} must be 64 lowercase hex characters")
    return text


@dataclass(frozen=True, slots=True)
class AuthorizedContextManifestEntry:
    entry_id: str
    resolver_id: str
    source_locator: str
    expected_source_identity: str | None
    expected_content_sha256: str | None
    context: InternalContextRecord

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AuthorizedContextManifestEntry":
        required = {"entry_id", "resolver_id", "source_locator", "context"}
        allowed = required | {"expected_source_identity", "expected_content_sha256"}
        require_fields(payload, required=required, allowed=allowed)
        raw_context = payload["context"]
        if not isinstance(raw_context, dict):
            raise ValueError("context must be an object")
        return cls(
            entry_id=require_text(payload["entry_id"], "entry_id"),
            resolver_id=require_text(payload["resolver_id"], "resolver_id"),
            source_locator=_require_exact_text(payload["source_locator"], "source_locator"),
            expected_source_identity=_optional_exact_text(payload.get("expected_source_identity"), "expected_source_identity"),
            expected_content_sha256=_optional_sha256(payload.get("expected_content_sha256"), "expected_content_sha256"),
            context=InternalContextRecord.from_dict(raw_context),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "entry_id": self.entry_id,
            "resolver_id": self.resolver_id,
            "source_locator": self.source_locator,
            "context": self.context.to_dict(),
        }
        if self.expected_source_identity is not None:
            payload["expected_source_identity"] = self.expected_source_identity
        if self.expected_content_sha256 is not None:
            payload["expected_content_sha256"] = self.expected_content_sha256
        return payload


@dataclass(frozen=True, slots=True)
class AuthorizedContextManifest:
    manifest_version: str
    entries: tuple[AuthorizedContextManifestEntry, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AuthorizedContextManifest":
        fields = {"manifest_version", "entries"}
        require_fields(payload, required=fields, allowed=fields)
        version = require_text(payload["manifest_version"], "manifest_version")
        if version != MANIFEST_VERSION:
            raise ValueError(f"manifest_version must be {MANIFEST_VERSION}")
        raw_entries = payload["entries"]
        if not isinstance(raw_entries, list):
            raise ValueError("entries must be a list")
        parsed = []
        for raw in raw_entries:
            if not isinstance(raw, dict):
                raise ValueError("each manifest entry must be an object")
            parsed.append(AuthorizedContextManifestEntry.from_dict(raw))
        entry_ids = [item.entry_id for item in parsed]
        context_ids = [item.context.context_id for item in parsed]
        if len(entry_ids) != len(set(entry_ids)):
            raise ValueError("duplicate entry_id in authorized context manifest")
        if len(context_ids) != len(set(context_ids)):
            raise ValueError("duplicate context_id in authorized context manifest")
        return cls(version, tuple(sorted(parsed, key=lambda item: (item.context.context_id, item.entry_id))))

    @classmethod
    def load(cls, path: str | Path) -> "AuthorizedContextManifest":
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("invalid authorized context manifest JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("authorized context manifest root must be an object")
        return cls.from_dict(payload)

    def to_dict(self) -> dict[str, Any]:
        return {"manifest_version": self.manifest_version, "entries": [item.to_dict() for item in self.entries]}
```

- [ ] **Step 4: Add RED fail-closed tests**

```python
def test_duplicate_entry_id_is_rejected():
    with pytest.raises(ValueError, match="duplicate entry_id"):
        AuthorizedContextManifest.from_dict({
            "manifest_version": "0.1",
            "entries": [entry_payload(), entry_payload(context={**CONTEXT, "context_id": "other"})],
        })


def test_duplicate_context_id_is_rejected():
    with pytest.raises(ValueError, match="duplicate context_id"):
        AuthorizedContextManifest.from_dict({
            "manifest_version": "0.1",
            "entries": [entry_payload(), entry_payload(entry_id="other-entry")],
        })


def test_unknown_secret_like_field_rejects_without_echoing_value():
    secret = "never-echo-this-token"
    with pytest.raises(ValueError) as exc_info:
        AuthorizedContextManifestEntry.from_dict(entry_payload(access_token=secret))
    assert "access_token" in str(exc_info.value)
    assert secret not in str(exc_info.value)


@pytest.mark.parametrize("field", ["source_locator", "expected_source_identity"])
def test_exact_identity_fields_reject_surrounding_whitespace(field):
    payload = entry_payload(**{field: " exact-value "})
    with pytest.raises(ValueError, match="surrounding whitespace"):
        AuthorizedContextManifestEntry.from_dict(payload)


@pytest.mark.parametrize("bad_hash", ["ABC", "g" * 64, "A" * 64, "0" * 63])
def test_expected_sha256_requires_lowercase_64_hex(bad_hash):
    with pytest.raises(ValueError, match="64 lowercase hex"):
        AuthorizedContextManifestEntry.from_dict(entry_payload(expected_content_sha256=bad_hash))


def test_unsupported_manifest_version_is_rejected():
    with pytest.raises(ValueError, match="manifest_version must be 0.1"):
        AuthorizedContextManifest.from_dict({"manifest_version": "9.9", "entries": []})
```

- [ ] **Step 5: Run Task 1 gate**

```bash
pytest -q tests/test_authorized_context_manifest.py
pytest -q
python -m compileall -q src tests
```

Expected: zero failures; compileall exits 0.

- [ ] **Step 6: Commit Task 1**

```bash
git add src/andes_context_os/producers tests/test_authorized_context_manifest.py
git commit -m "feat: add authorized context manifest contracts"
```

---

### Task 2: Exact Resolver Boundary and Successful Production

**Files:**
- Modify: `src/andes_context_os/producers/__init__.py`
- Modify: `src/andes_context_os/producers/authorized_context.py`
- Create: `tests/test_authorized_context_producer.py`

**Interfaces:**
- Consumes: `AuthorizedContextManifest`, `InternalContextCatalog`, `CATALOG_VERSION`.
- Produces:
  - `ExactContentResolver.resolve(locator: str) -> ResolvedContextSource`
  - `ResolvedContextSource(source_identity: str, content: bytes)`
  - `ContextProductionStatus`: `complete|partial|failed`
  - `ContextProductionFailureReason`: the five spec values
  - `ContextSourceReceipt`
  - `ContextProductionFailure`
  - `AuthorizedContextProduction.to_dict()`
  - `AuthorizedContextProducer.produce(manifest, resolvers)`

- [ ] **Step 1: Write RED success-path tests**

Create `tests/test_authorized_context_producer.py`:

```python
from hashlib import sha256

from andes_context_os.producers.authorized_context import (
    AuthorizedContextManifest,
    AuthorizedContextProducer,
    ContextProductionStatus,
    ResolvedContextSource,
)

CONTEXT = {
    "contract_version": "0.1",
    "context_id": "example-context",
    "kind": "repository",
    "title": "Example repository capability",
    "reference": "example:repository",
    "summary": "Fictitious repository capability.",
    "domains": ["logistics"],
    "activities": ["access"],
    "territory_refs": [],
    "tags": ["example"],
    "sensitivity": "public",
    "reviewed_at": "2026-08-30T10:00:00-03:00",
    "limitations": ["Fictitious example only."],
}


def manifest_entry(**overrides):
    payload = {
        "entry_id": "entry-example",
        "resolver_id": "fixture",
        "source_locator": "example://source",
        "context": CONTEXT,
    }
    payload.update(overrides)
    return payload


def manifest_with(*entries):
    return AuthorizedContextManifest.from_dict({"manifest_version": "0.1", "entries": list(entries)})


class RecordingResolver:
    def __init__(self, resolved):
        self.resolved = resolved
        self.calls = []

    def resolve(self, locator):
        self.calls.append(locator)
        return self.resolved


def test_unpinned_success_emits_unchanged_record_and_exact_hash_receipt():
    content = b"line-1\r\nline-2\n"
    resolver = RecordingResolver(ResolvedContextSource("example-source:v1", content))
    production = AuthorizedContextProducer().produce(manifest_with(manifest_entry()), {"fixture": resolver})
    assert production.status is ContextProductionStatus.COMPLETE
    assert production.catalog.records[0].to_dict() == CONTEXT
    assert resolver.calls == ["example://source"]
    assert production.receipts[0].source_content_sha256 == sha256(content).hexdigest()
    assert production.receipts[0].source_identity == "example-source:v1"
    assert production.failures == ()


def test_exact_bytes_are_not_normalized():
    producer = AuthorizedContextProducer()
    first = producer.produce(
        manifest_with(manifest_entry()),
        {"fixture": RecordingResolver(ResolvedContextSource("same:v1", b"x\n"))},
    )
    second = producer.produce(
        manifest_with(manifest_entry()),
        {"fixture": RecordingResolver(ResolvedContextSource("same:v1", b"x\r\n"))},
    )
    assert first.receipts[0].source_content_sha256 != second.receipts[0].source_content_sha256


def test_empty_bytes_are_valid():
    production = AuthorizedContextProducer().produce(
        manifest_with(manifest_entry()),
        {"fixture": RecordingResolver(ResolvedContextSource("empty:v1", b""))},
    )
    assert production.receipts[0].source_content_sha256 == sha256(b"").hexdigest()
```

- [ ] **Step 2: Run RED**

```bash
pytest -q tests/test_authorized_context_producer.py
```

Expected: missing producer types/behavior.

- [ ] **Step 3: Implement production contracts and success algorithm**

Add:

```python
from enum import StrEnum
from hashlib import sha256
from typing import Mapping, Protocol

from andes_context_os.internal_context import CATALOG_VERSION, InternalContextCatalog


class ContextProductionStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


class ContextProductionFailureReason(StrEnum):
    RESOLVER_NOT_REGISTERED = "resolver_not_registered"
    RESOLUTION_FAILED = "resolution_failed"
    SOURCE_IDENTITY_MISMATCH = "source_identity_mismatch"
    CONTENT_HASH_MISMATCH = "content_hash_mismatch"
    INVALID_RESOLVED_SOURCE = "invalid_resolved_source"


@dataclass(frozen=True, slots=True)
class ResolvedContextSource:
    source_identity: str
    content: bytes


class ExactContentResolver(Protocol):
    def resolve(self, locator: str) -> ResolvedContextSource:
        ...


@dataclass(frozen=True, slots=True)
class ContextSourceReceipt:
    entry_id: str
    context_id: str
    resolver_id: str
    source_identity: str
    source_content_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "context_id": self.context_id,
            "resolver_id": self.resolver_id,
            "source_identity": self.source_identity,
            "source_content_sha256": self.source_content_sha256,
        }


@dataclass(frozen=True, slots=True)
class ContextProductionFailure:
    entry_id: str
    context_id: str
    reason: ContextProductionFailureReason

    def to_dict(self) -> dict[str, Any]:
        return {"entry_id": self.entry_id, "context_id": self.context_id, "reason": self.reason.value}


@dataclass(frozen=True, slots=True)
class AuthorizedContextProduction:
    manifest_version: str
    status: ContextProductionStatus
    catalog: InternalContextCatalog
    receipts: tuple[ContextSourceReceipt, ...]
    failures: tuple[ContextProductionFailure, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "status": self.status.value,
            "catalog": self.catalog.to_dict(),
            "receipts": [item.to_dict() for item in self.receipts],
            "failures": [item.to_dict() for item in self.failures],
        }
```

Implement `AuthorizedContextProducer.produce()` over manifest entries already canonicalized by Task 1. Successful entries append `entry.context` unchanged and compute:

```python
actual_hash = sha256(resolved.content).hexdigest()
```

Build:

```python
catalog = InternalContextCatalog(
    catalog_version=CATALOG_VERSION,
    records=tuple(sorted(records, key=lambda item: item.context_id)),
)
```

Status is exactly:

```python
if not manifest.entries or len(records) == len(manifest.entries):
    status = ContextProductionStatus.COMPLETE
elif records:
    status = ContextProductionStatus.PARTIAL
else:
    status = ContextProductionStatus.FAILED
```

Sort receipts by `(context_id, entry_id)` and failures by `(context_id, entry_id, reason.value)`.

- [ ] **Step 4: Add RED resolver selection and pin-success tests**

```python
def test_mapping_key_selects_exact_resolver():
    first = RecordingResolver(ResolvedContextSource("wrong", b"wrong"))
    second = RecordingResolver(ResolvedContextSource("right", b"right"))
    production = AuthorizedContextProducer().produce(
        manifest_with(manifest_entry(resolver_id="second")),
        {"first": first, "second": second},
    )
    assert first.calls == []
    assert second.calls == ["example://source"]
    assert production.receipts[0].resolver_id == "second"


def test_identity_pin_success():
    production = AuthorizedContextProducer().produce(
        manifest_with(manifest_entry(expected_source_identity="source:v1")),
        {"fixture": RecordingResolver(ResolvedContextSource("source:v1", b"payload"))},
    )
    assert production.status is ContextProductionStatus.COMPLETE


def test_content_pin_success():
    content = b"payload"
    production = AuthorizedContextProducer().produce(
        manifest_with(manifest_entry(expected_content_sha256=sha256(content).hexdigest())),
        {"fixture": RecordingResolver(ResolvedContextSource("source:v1", content))},
    )
    assert production.status is ContextProductionStatus.COMPLETE
```

- [ ] **Step 5: Run Task 2 gate**

```bash
pytest -q tests/test_authorized_context_manifest.py tests/test_authorized_context_producer.py
pytest -q
python -m compileall -q src tests
```

Expected: zero failures.

- [ ] **Step 6: Export stable symbols and commit**

Export V0.3 public types from `src/andes_context_os/producers/__init__.py`, then:

```bash
git add src/andes_context_os/producers tests/test_authorized_context_producer.py
git commit -m "feat: add exact authorized context producer"
```

---

### Task 3: Fail-Closed Runtime Errors, Privacy, and Determinism

**Files:**
- Modify: `src/andes_context_os/producers/authorized_context.py`
- Modify: `tests/test_authorized_context_producer.py`

**Interfaces:**
- Consumes: Task 2 producer.
- Produces: all five sanitized runtime failure branches, complete/partial/failed semantics, exact-source validation, deterministic output.

- [ ] **Step 1: Write RED failure tests**

Append:

```python
import pytest

from andes_context_os.producers.authorized_context import ContextProductionFailureReason


class RaisingResolver:
    def resolve(self, locator):
        raise RuntimeError(f"private locator={locator} token=never-serialize")


class WrongReturnResolver:
    def resolve(self, locator):
        return {"source_identity": "not-contract", "content": b"x"}


@pytest.mark.parametrize(
    ("resolvers", "entry", "reason"),
    [
        ({}, manifest_entry(), ContextProductionFailureReason.RESOLVER_NOT_REGISTERED),
        ({"fixture": RaisingResolver()}, manifest_entry(), ContextProductionFailureReason.RESOLUTION_FAILED),
        ({"fixture": WrongReturnResolver()}, manifest_entry(), ContextProductionFailureReason.INVALID_RESOLVED_SOURCE),
    ],
)
def test_failed_entry_has_no_record_or_receipt(resolvers, entry, reason):
    production = AuthorizedContextProducer().produce(manifest_with(entry), resolvers)
    assert production.status is ContextProductionStatus.FAILED
    assert production.catalog.records == ()
    assert production.receipts == ()
    assert production.failures[0].reason is reason


def test_identity_mismatch_fails_closed():
    production = AuthorizedContextProducer().produce(
        manifest_with(manifest_entry(expected_source_identity="approved:v1")),
        {"fixture": RecordingResolver(ResolvedContextSource("actual:v2", b"payload"))},
    )
    assert production.failures[0].reason is ContextProductionFailureReason.SOURCE_IDENTITY_MISMATCH
    assert production.catalog.records == ()


def test_hash_mismatch_fails_closed():
    production = AuthorizedContextProducer().produce(
        manifest_with(manifest_entry(expected_content_sha256=sha256(b"approved").hexdigest())),
        {"fixture": RecordingResolver(ResolvedContextSource("source:v1", b"changed"))},
    )
    assert production.failures[0].reason is ContextProductionFailureReason.CONTENT_HASH_MISMATCH
    assert production.catalog.records == ()


def test_resolved_identity_with_surrounding_whitespace_is_invalid():
    production = AuthorizedContextProducer().produce(
        manifest_with(manifest_entry()),
        {"fixture": RecordingResolver(ResolvedContextSource(" source:v1 ", b"payload"))},
    )
    assert production.failures[0].reason is ContextProductionFailureReason.INVALID_RESOLVED_SOURCE


def test_non_bytes_content_is_invalid_even_if_type_hint_is_ignored_at_runtime():
    production = AuthorizedContextProducer().produce(
        manifest_with(manifest_entry()),
        {"fixture": RecordingResolver(ResolvedContextSource("source:v1", "not-bytes"))},
    )
    assert production.failures[0].reason is ContextProductionFailureReason.INVALID_RESOLVED_SOURCE
```

- [ ] **Step 2: Run RED**

```bash
pytest -q tests/test_authorized_context_producer.py
```

Expected: failure branches are incomplete.

- [ ] **Step 3: Implement sanitized runtime failure handling**

Inside `produce()` use this order:

1. Resolver key absent → `resolver_not_registered`.
2. Call `resolver.resolve(entry.source_locator)` inside `try/except Exception` only → `resolution_failed` on exception; never keep `str(exc)`.
3. Require `isinstance(resolved, ResolvedContextSource)`.
4. Validate `resolved.source_identity` with `_require_exact_text()`; validate `isinstance(resolved.content, bytes)` → `invalid_resolved_source` on failure.
5. Check exact identity pin → `source_identity_mismatch`.
6. Compute SHA-256 over exact bytes.
7. Check exact hash pin → `content_hash_mismatch`.
8. Only then append record + receipt.

Use:

```python
def _failure(entry, reason):
    return ContextProductionFailure(entry.entry_id, entry.context.context_id, reason)
```

This helper must never accept locator, bytes, hash values, source identity, or exception text.

- [ ] **Step 4: Add RED privacy/status/determinism tests**

```python
def test_failure_serialization_does_not_leak_locator_or_exception_text():
    locator = "private://vault/secret-note"
    production = AuthorizedContextProducer().produce(
        manifest_with(manifest_entry(source_locator=locator)),
        {"fixture": RaisingResolver()},
    )
    text = repr(production.to_dict())
    assert locator not in text
    assert "never-serialize" not in text
    assert "private locator" not in text


def test_partial_keeps_only_successful_independent_entry():
    ok_context = {**CONTEXT, "context_id": "a-ok", "reference": "example:a-ok"}
    good = manifest_entry(entry_id="entry-ok", source_locator="example://ok", context=ok_context)
    bad = manifest_entry(entry_id="entry-bad", resolver_id="missing")
    production = AuthorizedContextProducer().produce(
        manifest_with(bad, good),
        {"fixture": RecordingResolver(ResolvedContextSource("ok:v1", b"ok"))},
    )
    assert production.status is ContextProductionStatus.PARTIAL
    assert [item.context_id for item in production.catalog.records] == ["a-ok"]
    assert [item.context_id for item in production.receipts] == ["a-ok"]
    assert [item.context_id for item in production.failures] == ["example-context"]


def test_empty_manifest_is_complete_and_empty():
    production = AuthorizedContextProducer().produce(manifest_with(), {})
    assert production.status is ContextProductionStatus.COMPLETE
    assert production.catalog.records == ()
    assert production.receipts == ()
    assert production.failures == ()


def test_manifest_order_does_not_change_production():
    context_a = {**CONTEXT, "context_id": "a", "reference": "example:a"}
    context_b = {**CONTEXT, "context_id": "b", "reference": "example:b"}
    a = manifest_entry(entry_id="entry-a", source_locator="example://a", context=context_a)
    b = manifest_entry(entry_id="entry-b", source_locator="example://b", context=context_b)

    class DictResolver:
        def resolve(self, locator):
            return ResolvedContextSource(f"identity:{locator}", locator.encode())

    producer = AuthorizedContextProducer()
    assert producer.produce(manifest_with(b, a), {"fixture": DictResolver()}).to_dict() == producer.produce(
        manifest_with(a, b), {"fixture": DictResolver()}
    ).to_dict()


def test_resolver_never_receives_locator_absent_from_manifest():
    resolver = RecordingResolver(ResolvedContextSource("approved:v1", b"approved"))
    AuthorizedContextProducer().produce(manifest_with(manifest_entry()), {"fixture": resolver})
    assert resolver.calls == ["example://source"]
    assert "example://unauthorized-ninth" not in resolver.calls
```

- [ ] **Step 5: Run Task 3 gate**

```bash
pytest -q tests/test_authorized_context_producer.py
pytest -q
python -m compileall -q src tests
```

Expected: zero failures.

- [ ] **Step 6: Commit Task 3**

```bash
git add src/andes_context_os/producers/authorized_context.py tests/test_authorized_context_producer.py
git commit -m "test: harden authorized context producer boundaries"
```

---

### Task 4: Public-Safe Example, README, and Release Gate

**Files:**
- Create: `data/authorized_context.example.v0.1.json`
- Create: `tests/test_authorized_context_release.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces: safe sample and release checks proving there is no live GitHub/Vault claim or dependency creep.

- [ ] **Step 1: Write RED release tests**

```python
import json
from pathlib import Path
import tomllib

from andes_context_os.producers.authorized_context import AuthorizedContextManifest

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "authorized_context.example.v0.1.json"
README = ROOT / "README.md"
PYPROJECT = ROOT / "pyproject.toml"
PRODUCER = ROOT / "src" / "andes_context_os" / "producers" / "authorized_context.py"


def test_public_example_is_fictitious_and_safe():
    manifest = AuthorizedContextManifest.load(SAMPLE)
    assert len(manifest.entries) == 2
    for entry in manifest.entries:
        assert entry.context.sensitivity.value == "public"
        assert entry.resolver_id == "example"
        assert entry.source_locator.startswith("example://")
        assert "github.com" not in entry.source_locator
        assert "juanmanueltorres" not in repr(entry.to_dict()).lower()


def test_public_example_has_no_secret_like_keys():
    text = repr(json.loads(SAMPLE.read_text(encoding="utf-8"))).lower()
    for forbidden in ("password", "api_key", "access_token", "authorization", "cookie", "private_aoi"):
        assert forbidden not in text


def test_v03_adds_no_runtime_dependency_or_network_client():
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    assert pyproject["project"]["dependencies"] == []
    source = PRODUCER.read_text(encoding="utf-8").lower()
    for forbidden in ("requests", "httpx", "github", "mcp", "openai", "anthropic", "supabase"):
        assert f"import {forbidden}" not in source
        assert f"from {forbidden}" not in source


def test_readme_states_v03_boundary_without_live_connector_claim():
    text = README.read_text(encoding="utf-8")
    assert "## V0.3 — Authorized Context Producer" in text
    assert "exact authorized references" in text
    assert "does not search GitHub or the private vault" in text
    assert "source content is not copied into the produced catalog" in text
```

- [ ] **Step 2: Run RED**

```bash
pytest -q tests/test_authorized_context_release.py
```

Expected: missing sample and README V0.3 section.

- [ ] **Step 3: Create the exact public example manifest**

Create `data/authorized_context.example.v0.1.json`:

```json
{
  "manifest_version": "0.1",
  "entries": [
    {
      "entry_id": "example-repository-capability",
      "resolver_id": "example",
      "source_locator": "example://repository/access-capability",
      "expected_source_identity": "example-source:repository-access:v1",
      "context": {
        "contract_version": "0.1",
        "context_id": "example-repository-access",
        "kind": "repository",
        "title": "Example access mapping capability",
        "reference": "example:repository-access",
        "summary": "Fictitious repository capability for representing access context.",
        "domains": ["logistics"],
        "activities": ["access"],
        "territory_refs": [],
        "tags": ["example"],
        "sensitivity": "public",
        "reviewed_at": "2026-08-30T10:00:00-03:00",
        "limitations": ["Fictitious example only; no live operational claim."]
      }
    },
    {
      "entry_id": "example-road-freshness-gap",
      "resolver_id": "example",
      "source_locator": "example://note/road-freshness-gap",
      "context": {
        "contract_version": "0.1",
        "context_id": "example-road-freshness-gap",
        "kind": "known_gap",
        "title": "Example road freshness gap",
        "reference": "example:road-freshness-gap",
        "summary": "Fictitious reminder that mapped road geometry does not establish current road condition.",
        "domains": ["logistics"],
        "activities": ["road_condition"],
        "territory_refs": ["corridor:example-corridor-v1"],
        "tags": ["example"],
        "sensitivity": "public",
        "reviewed_at": "2026-08-30T10:00:00-03:00",
        "limitations": ["Fictitious example only; requires current external evidence before operational use."]
      }
    }
  ]
}
```

- [ ] **Step 4: Add README V0.3 section**

Immediately after V0.2, add:

```markdown
## V0.3 — Authorized Context Producer

V0.3 can turn a private manifest of exact authorized references into an `InternalContextCatalog` before V0.2 selection.

```text
private manifest
→ exact authorized references
→ injected exact resolver
→ exact source bytes + SHA-256 receipt
→ unchanged curated InternalContextRecord
→ InternalContextCatalog
```

The manifest, not the resolver, decides what may be read. The producer does not search GitHub or the private vault, enumerate repositories, recursively scan directories, follow links, infer neighboring files, or summarize source content. Concrete GitHub/vault resolvers are runtime concerns and are not dependencies of the public core.

Curated context metadata remains separate from source-resolution provenance. Source content is not copied into the produced catalog, resolver exceptions are sanitized, and failed entries emit neither records nor receipts.
```

- [ ] **Step 5: Run release and regression gate**

```bash
pytest -q tests/test_authorized_context_release.py
pytest -q
python -m compileall -q src tests
python - <<'PY'
import tomllib
from pathlib import Path
p = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
assert p["project"]["requires-python"] == ">=3.11"
assert p["project"]["dependencies"] == []
print("runtime_dependency_gate=PASS")
PY
```

Expected: zero failures and `runtime_dependency_gate=PASS`.

- [ ] **Step 6: Commit Task 4**

```bash
git add data/authorized_context.example.v0.1.json tests/test_authorized_context_release.py README.md
git commit -m "docs: publish authorized context producer v0.3"
```

---

### Task 5: Private Agua Negra/Filo Acceptance Benchmark and Final Verification

**Files:**
- Public repo: no private fixture/manifest/receipt is committed.
- Private vault: create `04 - Proyectos/Andes Context OS - Benchmark V0.3 Authorized Producer Agua Negra Filo.md` after acceptance passes.

**Interfaces:**
- Consumes: V0.3 producer, V0.2.1 adapter, V0.2 private benchmark intent/scope, eight previously curated semantic records.
- Produces: private acceptance evidence that the manual catalog translation is replaced by an eight-entry allowlist without widening resolver scope.

- [ ] **Step 1: Re-read only the canonical private benchmark context**

Read `04 - Proyectos/Andes Context OS - Benchmark V0.2 Agua Negra Filo.md` and use exactly these context IDs:

```text
agua-negra-architecture
agua-negra-markers
agua-negra-profile
andes-recipe-v0
filo-access-design
filo-validation-gap
premobilization-flow
premobilization-use-case
```

No ninth manifest entry. No locator is copied to the public repo.

- [ ] **Step 2: Build the private eight-entry manifest**

For each approved reference create one entry with `resolver_id = "private-exact"`, its exact private `source_locator`, any stable identity/hash pin available, and the previously curated `InternalContextRecord` payload. Preserve all semantic fields exactly: context ID, kind, title, reference, summary, domains, activities, typed territory refs, tags, sensitivity, `reviewed_at`, limitations.

Keep this manifest only in runtime/private memory or private workspace; do not write it under `andes-context-os`.

- [ ] **Step 3: Resolve only manifest-listed sources and use an explicit temporary exact resolver**

Using the connected private GitHub/vault reader, iterate over `private_manifest.entries` only. For each entry, perform one exact read of `entry.source_locator`; store the returned stable source identity and exact content bytes in an in-memory mapping keyed by that locator. Do not search, enumerate, recurse, or fetch any locator absent from the manifest.

Then run this temporary harness outside the public repo:

```python
class RecordingDictResolver:
    def __init__(self, resolved_by_locator):
        self.resolved_by_locator = resolved_by_locator
        self.calls = []

    def resolve(self, locator):
        self.calls.append(locator)
        return self.resolved_by_locator[locator]


private_resolver = RecordingDictResolver(resolved_by_locator)
production = AuthorizedContextProducer().produce(
    private_manifest,
    {"private-exact": private_resolver},
)
```

Acceptance assertions:

```python
assert production.status.value == "complete"
assert len(production.catalog.records) == 8
assert len(production.receipts) == 8
assert production.failures == ()
assert len(private_resolver.calls) == 8
assert set(private_resolver.calls) == {entry.source_locator for entry in private_manifest.entries}
assert set(item.context_id for item in production.catalog.records) == {
    "agua-negra-architecture",
    "agua-negra-markers",
    "agua-negra-profile",
    "andes-recipe-v0",
    "filo-access-design",
    "filo-validation-gap",
    "premobilization-flow",
    "premobilization-use-case",
}
```

Because `resolved_by_locator` is built only from manifest entries and the resolver call set must equal that manifest locator set, an unauthorized ninth reference cannot be resolved.

- [ ] **Step 4: Feed the produced catalog into V0.2.1 and prove current-contract determinism**

Reuse:

```text
domain = logistics
activity = access
country = AR
admin = admin:AR:1:J
project = project:filo-del-sol-access-v1
corridor = corridor:agua-negra-v1
```

Use fixed `generated_at="2026-08-30T12:00:00-03:00"`.

Do not assert the old V0.2 SHA `1a92271a...`; V0.2.1 now projects `reviewed_at`. Run production + snapshot twice with identical source bytes and assert:

```python
assert production_a.to_dict() == production_b.to_dict()
assert snapshot_a.to_dict() == snapshot_b.to_dict()
assert snapshot_a.snapshot_id == snapshot_b.snapshot_id
```

Also assert the selected context IDs are the same eight canonical benchmark IDs.

- [ ] **Step 5: Write the private V0.3 benchmark note**

Record these concrete facts in `04 - Proyectos/Andes Context OS - Benchmark V0.3 Authorized Producer Agua Negra Filo.md`:

```text
status: complete
public repo branch/head used: write the exact feature branch and HEAD SHA used by the run
manifest entries: 8
successful records: 8
receipts: 8
failures: 0
resolver calls: exactly the 8 manifest-listed locators
unauthorized ninth locator resolved: no
selected context IDs: list the 8 canonical IDs
new deterministic snapshot_id: write the exact value returned by snapshot_a.snapshot_id
private manifest committed publicly: no
private receipts committed publicly: no
```

Do not paste private locator values, source content, credentials, contacts, AOIs, or sensitive operational details into the public repo.

- [ ] **Step 6: Run final public verification on exact feature HEAD**

```bash
python -m pip install -e ".[dev]"
pytest -q
python -m compileall -q src tests
python - <<'PY'
from pathlib import Path
import tomllib
p = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
assert p["project"]["dependencies"] == []
assert Path("src/andes_context_os/internal_context.py").exists()
assert Path("src/andes_context_os/adapters/internal_context.py").exists()
print("v0.3_final_gate=PASS")
PY
```

Expected: install succeeds; pytest has zero failures; compileall exits 0; gate prints `PASS`.

- [ ] **Step 7: Verify GitHub Actions on exact feature HEAD**

Push `feat/v0.3-authorized-context-producer`. Require workflow `tests` to finish `conclusion=success` on the exact HEAD with Python 3.11 and `pytest -q` green. Record run ID, job ID, HEAD SHA, and exact test count in the private benchmark note.

- [ ] **Step 8: Commit only the benchmark note to the private vault**

Commit the V0.3 benchmark note to `geoplatform-knowledge-base`. Do not add private manifest or receipts to `andes-context-os`.

---

## Final Requirement Checklist

Before integration, verify explicitly:

- [ ] No search/enumeration API exists.
- [ ] `InternalContextRecord` and `InternalContextCatalog` remain unchanged.
- [ ] Metadata stays curated, never extracted from source bytes.
- [ ] Exact locator/source identities are not normalized.
- [ ] Every success has exactly one receipt.
- [ ] SHA-256 hashes exact bytes.
- [ ] Identity/hash pins fail closed.
- [ ] Five closed failure reasons are implemented.
- [ ] Failed entries emit no record/receipt.
- [ ] Complete/partial/failed semantics match spec.
- [ ] Production omits locator/content; failures omit mismatch details and exception text.
- [ ] Input reordering does not change production serialization.
- [ ] Empty manifest yields complete empty production.
- [ ] Public example is fictitious/public-safe.
- [ ] No concrete GitHub/Vault resolver or new runtime dependency exists in public core.
- [ ] V0.2.1 regressions remain green.
- [ ] Private Agua Negra/Filo benchmark produces 8 records, 8 receipts, 0 failures.
- [ ] Resolver receives exactly the 8 allowlisted locators and no ninth reference.
- [ ] Feature-branch GitHub Actions is green on exact reviewed HEAD.
