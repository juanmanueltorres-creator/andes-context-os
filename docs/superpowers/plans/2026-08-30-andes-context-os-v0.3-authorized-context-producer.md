# Andes Context OS V0.3 — Authorized Context Producer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a strict allowlist-first producer that resolves only explicitly authorized internal references, emits unchanged curated `InternalContextRecord` objects, and preserves exact source provenance through sanitized SHA-256 receipts.

**Architecture:** V0.3 adds one new stdlib-only producer module in front of the existing V0.2.1 internal-context selector. A private manifest supplies exact opaque locators plus curated context metadata; caller-injected resolvers return exact source bytes; the producer verifies optional identity/hash pins, emits a deterministic `InternalContextCatalog`, and keeps resolution provenance/failures separate from stable context semantics.

**Tech Stack:** Python 3.11+, stdlib (`dataclasses`, `enum`, `hashlib`, `json`, `pathlib`, `typing`), pytest 8.x. Runtime dependencies remain empty.

**Spec:** `docs/superpowers/specs/2026-08-30-andes-context-os-v0.3-authorized-context-producer-design.md`

## Global Constraints

- `manifest_version = "0.1"`.
- Reuse `InternalContextRecord` and `InternalContextCatalog` unchanged.
- Runtime remains Python 3.11+ stdlib-only; `pyproject.toml` production `dependencies = []` stays unchanged.
- No GitHub SDK, MCP client, HTTP library, database client, LLM SDK, embeddings, fuzzy matching, repository search, vault search, tree enumeration, recursive scan, glob expansion, or link-following.
- Only manifest-listed `source_locator` values may reach a resolver.
- `source_locator` is opaque to the producer and must never appear in `AuthorizedContextProduction.to_dict()`.
- Manifest metadata is curated; source bytes never generate or rewrite title, summary, domain, activity, territory refs, tags, sensitivity, limitations, or `reviewed_at`.
- Source bytes are hashed exactly as returned; no newline, Unicode, JSON, Markdown, or whitespace normalization.
- `resolved successfully now != reviewed semantically now`; V0.3 never updates `reviewed_at` implicitly.
- A failed entry emits no `InternalContextRecord` and no `ContextSourceReceipt`.
- Resolver exceptions are converted to `resolution_failed`; raw exception text is never serialized.
- Failure serialization omits locator, source bytes, expected/actual identity, expected/actual hash, and exception text.
- No aggregate confidence, relevance, freshness, risk, or truth score.
- Real manifests, receipts, private paths/refs, AOIs, contacts, credentials, and sensitive operational details must never be committed to the public repository.

## File Structure

- Create `src/andes_context_os/producers/__init__.py` — public producer package boundary; export only stable V0.3 producer types.
- Create `src/andes_context_os/producers/authorized_context.py` — manifest contracts, resolver protocol, production contracts, exact producer algorithm.
- Create `tests/test_authorized_context_manifest.py` — strict manifest parsing/round-trip/fail-closed tests.
- Create `tests/test_authorized_context_producer.py` — success, pinning, failure, privacy, status, and determinism tests using fake exact resolvers.
- Create `data/authorized_context.example.v0.1.json` — fictitious/public-safe manifest only.
- Create `tests/test_authorized_context_release.py` — public-safety, dependency, README, and non-goal release gates.
- Modify `README.md` — concise V0.3 description and explicit non-goals.
- Do **not** modify `src/andes_context_os/internal_context.py`, `src/andes_context_os/adapters/internal_context.py`, or the stabilized `DiscoveryRun` contract.

---

### Task 1: Strict Authorized Manifest Contracts

**Files:**
- Create: `src/andes_context_os/producers/__init__.py`
- Create: `src/andes_context_os/producers/authorized_context.py`
- Create: `tests/test_authorized_context_manifest.py`

**Interfaces:**
- Consumes: `InternalContextRecord.from_dict(payload: dict[str, Any]) -> InternalContextRecord` and `.to_dict()` from `andes_context_os.internal_context`; `require_fields()` and `require_text()` from `andes_context_os.common`.
- Produces:
  - `MANIFEST_VERSION = "0.1"`
  - `AuthorizedContextManifestEntry.from_dict(payload: dict[str, Any]) -> AuthorizedContextManifestEntry`
  - `AuthorizedContextManifestEntry.to_dict() -> dict[str, Any]`
  - `AuthorizedContextManifest.from_dict(payload: dict[str, Any]) -> AuthorizedContextManifest`
  - `AuthorizedContextManifest.load(path: str | Path) -> AuthorizedContextManifest`
  - `AuthorizedContextManifest.to_dict() -> dict[str, Any]`

- [ ] **Step 1: Write RED tests for valid manifest parsing and canonical round-trip**

Create `tests/test_authorized_context_manifest.py` with a reusable valid context payload and these tests:

```python
import json

import pytest

from andes_context_os.producers.authorized_context import (
    MANIFEST_VERSION,
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


def test_manifest_round_trip_is_canonical_by_context_id_then_entry_id():
    second_context = {**CONTEXT, "context_id": "a-context", "reference": "example:a"}
    payload = {
        "manifest_version": MANIFEST_VERSION,
        "entries": [
            entry_payload(),
            entry_payload(
                entry_id="entry-a",
                source_locator="example://context/a",
                context=second_context,
            ),
        ],
    }
    manifest = AuthorizedContextManifest.from_dict(payload)
    assert [item.context.context_id for item in manifest.entries] == [
        "a-context",
        "example-access-context",
    ]
    assert AuthorizedContextManifest.from_dict(manifest.to_dict()) == manifest


def test_manifest_load_reads_local_json_only(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"manifest_version": "0.1", "entries": []}), encoding="utf-8")
    assert AuthorizedContextManifest.load(path).entries == ()
```

- [ ] **Step 2: Run the focused tests and verify RED for missing module/types**

Run:

```bash
pytest -q tests/test_authorized_context_manifest.py
```

Expected: collection/import failure because `andes_context_os.producers.authorized_context` does not exist.

- [ ] **Step 3: Implement the minimal strict manifest contracts**

Create `src/andes_context_os/producers/__init__.py` and `src/andes_context_os/producers/authorized_context.py` with frozen/slots dataclasses. The core shape must be:

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


def _optional_text(value: Any, field: str) -> str | None:
    return None if value is None else require_text(value, field)


def _optional_sha256(value: Any, field: str) -> str | None:
    if value is None:
        return None
    text = require_text(value, field)
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
            source_locator=require_text(payload["source_locator"], "source_locator"),
            expected_source_identity=_optional_text(payload.get("expected_source_identity"), "expected_source_identity"),
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
        return cls(
            manifest_version=version,
            entries=tuple(sorted(parsed, key=lambda item: (item.context.context_id, item.entry_id))),
        )

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
        return {
            "manifest_version": self.manifest_version,
            "entries": [item.to_dict() for item in self.entries],
        }
```

`src/andes_context_os/producers/__init__.py` must export `AuthorizedContextManifest` and `AuthorizedContextManifestEntry` without importing any external client.

- [ ] **Step 4: Add RED tests for fail-closed manifest boundaries**

Append:

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
            "entries": [entry_payload(), entry_payload(entry_id="entry-other")],
        })


def test_unknown_secret_like_field_is_rejected_without_echoing_value():
    secret_value = "never-echo-this-token"
    payload = entry_payload(access_token=secret_value)
    with pytest.raises(ValueError) as exc_info:
        AuthorizedContextManifestEntry.from_dict(payload)
    assert "access_token" in str(exc_info.value)
    assert secret_value not in str(exc_info.value)


@pytest.mark.parametrize("bad_hash", ["ABC", "g" * 64, "A" * 64, "0" * 63])
def test_expected_sha256_requires_lowercase_64_hex(bad_hash):
    with pytest.raises(ValueError, match="64 lowercase hex"):
        AuthorizedContextManifestEntry.from_dict(entry_payload(expected_content_sha256=bad_hash))


def test_unsupported_manifest_version_is_rejected():
    with pytest.raises(ValueError, match="manifest_version must be 0.1"):
        AuthorizedContextManifest.from_dict({"manifest_version": "9.9", "entries": []})
```

- [ ] **Step 5: Run the task suite and full regression**

Run:

```bash
pytest -q tests/test_authorized_context_manifest.py
pytest -q
python -m compileall -q src tests
```

Expected: all focused tests pass; existing suite remains green; compileall exits 0.

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
  - `class ExactContentResolver(Protocol): resolve(locator: str) -> ResolvedContextSource`
  - `ResolvedContextSource(source_identity: str, content: bytes)`
  - `ContextProductionStatus` values `complete`, `partial`, `failed`
  - `ContextProductionFailureReason` values `resolver_not_registered`, `resolution_failed`, `source_identity_mismatch`, `content_hash_mismatch`, `invalid_resolved_source`
  - `ContextSourceReceipt(entry_id, context_id, resolver_id, source_identity, source_content_sha256)`
  - `ContextProductionFailure(entry_id, context_id, reason)`
  - `AuthorizedContextProduction(manifest_version, status, catalog, receipts, failures)` with `.to_dict()`
  - `AuthorizedContextProducer.produce(manifest, resolvers) -> AuthorizedContextProduction`

- [ ] **Step 1: Write RED success-path tests with a call-recording exact resolver**

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


def test_successful_unpinned_entry_emits_exact_record_and_receipt():
    content = b"line-1\r\nline-2\n"
    resolver = RecordingResolver(ResolvedContextSource("example-source:v1", content))
    production = AuthorizedContextProducer().produce(
        manifest_with(manifest_entry()),
        {"fixture": resolver},
    )
    assert production.status is ContextProductionStatus.COMPLETE
    assert [item.context_id for item in production.catalog.records] == ["example-context"]
    assert production.catalog.records[0].to_dict() == CONTEXT
    assert resolver.calls == ["example://source"]
    assert production.receipts[0].source_content_sha256 == sha256(content).hexdigest()
    assert production.receipts[0].source_identity == "example-source:v1"
    assert production.failures == ()


def test_exact_bytes_are_hashed_without_normalization():
    a = RecordingResolver(ResolvedContextSource("source:a", b"x\n"))
    b = RecordingResolver(ResolvedContextSource("source:a", b"x\r\n"))
    producer = AuthorizedContextProducer()
    first = producer.produce(manifest_with(manifest_entry()), {"fixture": a})
    second = producer.produce(manifest_with(manifest_entry()), {"fixture": b})
    assert first.receipts[0].source_content_sha256 != second.receipts[0].source_content_sha256


def test_empty_bytes_are_valid_and_hashable():
    resolver = RecordingResolver(ResolvedContextSource("empty:v1", b""))
    production = AuthorizedContextProducer().produce(manifest_with(manifest_entry()), {"fixture": resolver})
    assert production.status is ContextProductionStatus.COMPLETE
    assert production.receipts[0].source_content_sha256 == sha256(b"").hexdigest()
```

- [ ] **Step 2: Run focused tests and verify RED for missing production types**

Run:

```bash
pytest -q tests/test_authorized_context_producer.py
```

Expected: import/attribute failure because producer contracts are not implemented yet.

- [ ] **Step 3: Implement the production contracts and exact success algorithm**

Extend `authorized_context.py` with:

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
    source_identity: Any
    content: Any


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
        return {
            "entry_id": self.entry_id,
            "context_id": self.context_id,
            "reason": self.reason.value,
        }


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

Then implement `AuthorizedContextProducer.produce()` using the exact mapping key as resolver identity. Successful entries must append the manifest's **existing** `entry.context` object unchanged and one receipt. Use:

```python
actual_hash = sha256(resolved.content).hexdigest()
```

Do not inspect or parse `resolved.content`.

Build the catalog with:

```python
catalog = InternalContextCatalog(
    catalog_version=CATALOG_VERSION,
    records=tuple(sorted(records, key=lambda item: item.context_id)),
)
```

Status logic must be exactly:

```python
if not manifest.entries or len(records) == len(manifest.entries):
    status = ContextProductionStatus.COMPLETE
elif records:
    status = ContextProductionStatus.PARTIAL
else:
    status = ContextProductionStatus.FAILED
```

Canonicalize receipts by `(context_id, entry_id)` and failures by `(context_id, entry_id, reason.value)` before returning.

- [ ] **Step 4: Add RED pinning and resolver-selection tests**

Append:

```python
def test_resolver_mapping_key_selects_exact_resolver():
    first = RecordingResolver(ResolvedContextSource("wrong", b"wrong"))
    second = RecordingResolver(ResolvedContextSource("right", b"right"))
    entry = manifest_entry(resolver_id="second")
    production = AuthorizedContextProducer().produce(manifest_with(entry), {"first": first, "second": second})
    assert first.calls == []
    assert second.calls == ["example://source"]
    assert production.receipts[0].resolver_id == "second"


def test_exact_source_identity_pin_succeeds():
    resolver = RecordingResolver(ResolvedContextSource("source:v1", b"payload"))
    production = AuthorizedContextProducer().produce(
        manifest_with(manifest_entry(expected_source_identity="source:v1")),
        {"fixture": resolver},
    )
    assert production.status is ContextProductionStatus.COMPLETE


def test_exact_content_hash_pin_succeeds():
    content = b"payload"
    resolver = RecordingResolver(ResolvedContextSource("source:v1", content))
    production = AuthorizedContextProducer().produce(
        manifest_with(manifest_entry(expected_content_sha256=sha256(content).hexdigest())),
        {"fixture": resolver},
    )
    assert production.status is ContextProductionStatus.COMPLETE
```

- [ ] **Step 5: Run Task 2 tests and full regression**

```bash
pytest -q tests/test_authorized_context_manifest.py tests/test_authorized_context_producer.py
pytest -q
python -m compileall -q src tests
```

Expected: all pass.

- [ ] **Step 6: Export stable producer symbols and commit**

Update `src/andes_context_os/producers/__init__.py` to export the V0.3 public types used above, then:

```bash
git add src/andes_context_os/producers tests/test_authorized_context_producer.py
git commit -m "feat: add exact authorized context producer"
```

---

### Task 3: Fail-Closed Runtime Errors, Privacy Boundary, and Determinism

**Files:**
- Modify: `src/andes_context_os/producers/authorized_context.py`
- Modify: `tests/test_authorized_context_producer.py`

**Interfaces:**
- Consumes: Task 2 producer and failure enums.
- Produces: complete per-entry failure handling with sanitized output, deterministic status/order, and no source locator/content leakage.

- [ ] **Step 1: Write RED tests for every closed runtime failure reason**

Append:

```python
import pytest

from andes_context_os.producers.authorized_context import ContextProductionFailureReason


class RaisingResolver:
    def resolve(self, locator):
        raise RuntimeError(f"private locator={locator} token=never-serialize")


class WrongReturnResolver:
    def resolve(self, locator):
        return {"source_identity": "not-a-contract", "content": b"x"}


@pytest.mark.parametrize(
    ("resolvers", "entry", "reason"),
    [
        ({}, manifest_entry(), ContextProductionFailureReason.RESOLVER_NOT_REGISTERED),
        ({"fixture": RaisingResolver()}, manifest_entry(), ContextProductionFailureReason.RESOLUTION_FAILED),
        ({"fixture": WrongReturnResolver()}, manifest_entry(), ContextProductionFailureReason.INVALID_RESOLVED_SOURCE),
    ],
)
def test_failed_entry_emits_no_record_or_receipt(resolvers, entry, reason):
    production = AuthorizedContextProducer().produce(manifest_with(entry), resolvers)
    assert production.status is ContextProductionStatus.FAILED
    assert production.catalog.records == ()
    assert production.receipts == ()
    assert production.failures[0].reason is reason


def test_source_identity_mismatch_fails_closed():
    resolver = RecordingResolver(ResolvedContextSource("actual:v2", b"payload"))
    production = AuthorizedContextProducer().produce(
        manifest_with(manifest_entry(expected_source_identity="approved:v1")),
        {"fixture": resolver},
    )
    assert production.failures[0].reason is ContextProductionFailureReason.SOURCE_IDENTITY_MISMATCH
    assert production.catalog.records == ()


def test_content_hash_mismatch_fails_closed():
    resolver = RecordingResolver(ResolvedContextSource("source:v1", b"changed"))
    production = AuthorizedContextProducer().produce(
        manifest_with(manifest_entry(expected_content_sha256=sha256(b"approved").hexdigest())),
        {"fixture": resolver},
    )
    assert production.failures[0].reason is ContextProductionFailureReason.CONTENT_HASH_MISMATCH
    assert production.catalog.records == ()


def test_malformed_resolved_source_fields_are_invalid_not_serialized():
    resolver = RecordingResolver(ResolvedContextSource("", "not-bytes"))
    production = AuthorizedContextProducer().produce(manifest_with(manifest_entry()), {"fixture": resolver})
    assert production.failures[0].reason is ContextProductionFailureReason.INVALID_RESOLVED_SOURCE
```

- [ ] **Step 2: Run focused tests and verify RED because failure handling is incomplete**

```bash
pytest -q tests/test_authorized_context_producer.py
```

Expected: one or more failure-path tests fail until the producer adds all closed branches.

- [ ] **Step 3: Implement sanitized failure handling**

Inside `produce()`:

1. Missing mapping key → append `ContextProductionFailure(..., RESOLVER_NOT_REGISTERED)` and continue.
2. Wrap only `resolver.resolve(entry.source_locator)` in `try/except Exception`; exception → `RESOLUTION_FAILED`; never serialize `str(exc)`.
3. Validate `isinstance(resolved, ResolvedContextSource)`, non-empty `source_identity` via `require_text`, and `isinstance(resolved.content, bytes)`; validation failure → `INVALID_RESOLVED_SOURCE`.
4. If pinned identity differs → `SOURCE_IDENTITY_MISMATCH`.
5. Compute exact byte hash.
6. If pinned hash differs → `CONTENT_HASH_MISMATCH`.
7. Only after all checks append `entry.context` and a receipt.

Use a local helper that never accepts locator/source content:

```python
def _failure(entry: AuthorizedContextManifestEntry, reason: ContextProductionFailureReason) -> ContextProductionFailure:
    return ContextProductionFailure(
        entry_id=entry.entry_id,
        context_id=entry.context.context_id,
        reason=reason,
    )
```

- [ ] **Step 4: Add RED privacy/status/order tests**

Append:

```python
def test_production_serialization_never_contains_locator_content_or_exception_text():
    locator = "private://vault/secret-note"
    production = AuthorizedContextProducer().produce(
        manifest_with(manifest_entry(source_locator=locator)),
        {"fixture": RaisingResolver()},
    )
    text = repr(production.to_dict())
    assert locator not in text
    assert "never-serialize" not in text
    assert "private locator" not in text


def test_partial_status_keeps_only_independent_successes():
    ok_context = {**CONTEXT, "context_id": "a-ok", "reference": "example:a-ok"}
    good = manifest_entry(entry_id="entry-ok", source_locator="example://ok", context=ok_context)
    bad = manifest_entry(entry_id="entry-bad", resolver_id="missing")
    resolver = RecordingResolver(ResolvedContextSource("ok:v1", b"ok"))
    production = AuthorizedContextProducer().produce(manifest_with(bad, good), {"fixture": resolver})
    assert production.status is ContextProductionStatus.PARTIAL
    assert [item.context_id for item in production.catalog.records] == ["a-ok"]
    assert [item.context_id for item in production.receipts] == ["a-ok"]
    assert [item.context_id for item in production.failures] == ["example-context"]


def test_empty_manifest_is_complete_empty_production():
    production = AuthorizedContextProducer().produce(manifest_with(), {})
    assert production.status is ContextProductionStatus.COMPLETE
    assert production.catalog.records == ()
    assert production.receipts == ()
    assert production.failures == ()


def test_manifest_order_does_not_change_serialized_production():
    context_a = {**CONTEXT, "context_id": "a", "reference": "example:a"}
    context_b = {**CONTEXT, "context_id": "b", "reference": "example:b"}
    a = manifest_entry(entry_id="entry-a", source_locator="example://a", context=context_a)
    b = manifest_entry(entry_id="entry-b", source_locator="example://b", context=context_b)

    class DictResolver:
        def resolve(self, locator):
            return ResolvedContextSource(f"identity:{locator}", locator.encode())

    producer = AuthorizedContextProducer()
    first = producer.produce(manifest_with(b, a), {"fixture": DictResolver()})
    second = producer.produce(manifest_with(a, b), {"fixture": DictResolver()})
    assert first.to_dict() == second.to_dict()
```

- [ ] **Step 5: Add a direct allowlist test proving an unauthorized ninth locator is never called**

```python
def test_resolver_never_receives_locator_absent_from_manifest():
    resolver = RecordingResolver(ResolvedContextSource("approved:v1", b"approved"))
    AuthorizedContextProducer().produce(manifest_with(manifest_entry()), {"fixture": resolver})
    assert resolver.calls == ["example://source"]
    assert "example://unauthorized-ninth" not in resolver.calls
```

This is intentionally structural: there is no producer search/enumeration API from which a ninth locator could appear.

- [ ] **Step 6: Run the full Task 3 gate and commit**

```bash
pytest -q tests/test_authorized_context_producer.py
pytest -q
python -m compileall -q src tests
```

Expected: all pass.

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
- Consumes: public manifest parser and producer contracts from Tasks 1–3.
- Produces: safe public example and release assertions proving no private runtime integration or dependency creep was introduced.

- [ ] **Step 1: Write RED release tests before creating sample/docs**

Create `tests/test_authorized_context_release.py`:

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


def test_public_example_manifest_is_fictitious_and_safe():
    manifest = AuthorizedContextManifest.load(SAMPLE)
    assert len(manifest.entries) >= 2
    for entry in manifest.entries:
        assert entry.context.sensitivity.value == "public"
        assert entry.resolver_id == "example"
        assert entry.source_locator.startswith("example://")
        assert "github.com" not in entry.source_locator
        assert "juanmanueltorres" not in repr(entry.to_dict()).lower()


def test_public_example_contains_no_secret_like_keys():
    payload = json.loads(SAMPLE.read_text(encoding="utf-8"))
    text = repr(payload).lower()
    for forbidden in ("password", "api_key", "access_token", "authorization", "cookie", "private_aoi"):
        assert forbidden not in text


def test_v03_adds_no_runtime_dependency_or_network_client():
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    assert pyproject["project"]["dependencies"] == []
    source = PRODUCER.read_text(encoding="utf-8").lower()
    for forbidden in ("requests", "httpx", "github", "mcp", "openai", "anthropic", "supabase"):
        assert f"import {forbidden}" not in source
        assert f"from {forbidden}" not in source


def test_readme_describes_v03_allowlist_boundary_without_live_connector_claim():
    text = README.read_text(encoding="utf-8")
    assert "## V0.3 — Authorized Context Producer" in text
    assert "exact authorized references" in text
    assert "does not search GitHub or the private vault" in text
    assert "source content is not copied into the produced catalog" in text
```

- [ ] **Step 2: Run release tests and verify RED because sample/README section are missing**

```bash
pytest -q tests/test_authorized_context_release.py
```

Expected: failures for missing sample and README V0.3 section.

- [ ] **Step 3: Create a fictitious public example manifest**

Create `data/authorized_context.example.v0.1.json` with exactly two safe entries:

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

- [ ] **Step 4: Add a concise README V0.3 section**

Immediately after the V0.2 section, add text equivalent to:

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

Do not claim that V0.3 already has a live GitHub/Vault connector.

- [ ] **Step 5: Run public release gate, full regression, compile, and dependency check**

```bash
pytest -q tests/test_authorized_context_release.py
pytest -q
python -m compileall -q src tests
python - <<'PY'
import tomllib
from pathlib import Path
payload = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
assert payload["project"]["requires-python"] == ">=3.11"
assert payload["project"]["dependencies"] == []
print("runtime_dependency_gate=PASS")
PY
```

Expected: all tests pass, compileall exits 0, dependency gate prints `PASS`.

- [ ] **Step 6: Commit Task 4**

```bash
git add data/authorized_context.example.v0.1.json tests/test_authorized_context_release.py README.md
git commit -m "docs: publish authorized context producer v0.3"
```

---

### Task 5: Private Agua Negra/Filo Acceptance Benchmark and Final Verification

**Files:**
- Public repo: **no new private fixture or manifest is committed**.
- Private vault output: create `04 - Proyectos/Andes Context OS - Benchmark V0.3 Authorized Producer Agua Negra Filo.md` in `juanmanueltorres-creator/geoplatform-knowledge-base` after the benchmark succeeds.

**Interfaces:**
- Consumes: `AuthorizedContextProducer`, `AuthorizedContextManifest`, existing `InternalContextAdapter`, benchmark intent/scope from the V0.2 private benchmark, and the eight already-curated semantic records.
- Produces: private evidence that the manual catalog-translation bottleneck can be replaced by an eight-entry authorized manifest without widening resolver scope.

- [ ] **Step 1: Re-read the canonical private benchmark and recover only the eight approved references**

Read:

```text
04 - Proyectos/Andes Context OS - Benchmark V0.2 Agua Negra Filo.md
```

Use exactly these existing benchmark context IDs:

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

Do not add a ninth context entry during the benchmark. Do not commit source locators to the public repo.

- [ ] **Step 2: Build the private eight-entry manifest using the already-curated semantic payloads**

Each private manifest entry must contain:

```text
entry_id
resolver_id
exact private source_locator
optional expected_source_identity / expected_content_sha256 where a stable pin is available
context = the previously curated InternalContextRecord payload
```

The `context` objects must remain semantically identical to the benchmark values for `context_id`, `kind`, `title`, `reference`, `summary`, `domains`, `activities`, typed `territory_refs`, `tags`, `sensitivity`, `reviewed_at`, and `limitations`.

The manifest is a runtime/private artifact only. Do not write it under the public repo tree.

- [ ] **Step 3: Run production through an exact private/runtime resolver and record call boundaries**

The runtime resolver must record every locator it receives. Execute:

```python
production = AuthorizedContextProducer().produce(private_manifest, {private_resolver_id: private_resolver})
```

Acceptance assertions:

```python
assert production.status.value == "complete"
assert len(production.catalog.records) == 8
assert len(production.receipts) == 8
assert production.failures == ()
assert len(private_resolver.calls) == 8
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

Also assert the resolver call log contains only the eight locators named in the private manifest. An unauthorized ninth locator must not be present.

- [ ] **Step 4: Feed the produced catalog into the existing V0.2.1 adapter and compare semantic selection**

Reuse the benchmark intent/scope:

```text
domain = logistics
activity = access
country = AR
admin = admin:AR:1:J
project = project:filo-del-sol-access-v1
corridor = corridor:agua-negra-v1
```

Call:

```python
snapshot = InternalContextAdapter().snapshot(
    benchmark_intent,
    benchmark_scope,
    production.catalog,
    generated_at="2026-08-30T12:00:00-03:00",
)
```

Assert the selected semantic context IDs match the eight expected records. Do **not** assert the old V0.2 snapshot SHA `1a92271a...`: V0.2.1 now projects `reviewed_at`, so the correct acceptance property is deterministic identity for the current contract.

Run the same production + snapshot twice with identical bytes and fixed `generated_at`, and assert:

```python
assert production_a.to_dict() == production_b.to_dict()
assert snapshot_a.to_dict() == snapshot_b.to_dict()
assert snapshot_a.snapshot_id == snapshot_b.snapshot_id
```

- [ ] **Step 5: Create the private V0.3 benchmark note**

Write `04 - Proyectos/Andes Context OS - Benchmark V0.3 Authorized Producer Agua Negra Filo.md` with:

```text
status: complete
public repo branch/head used
manifest entries: 8
successful records: 8
receipts: 8
failures: 0
resolver calls: exactly 8 authorized locators
unauthorized ninth locator resolved: no
selected context IDs: the eight canonical IDs
new deterministic snapshot_id: <record the actual current value>
private manifest committed publicly: no
private receipts committed publicly: no
```

Do not paste source content, private locator values, credentials, contacts, AOIs, or sensitive operational route details into the public repo.

- [ ] **Step 6: Run the final public verification on the exact feature HEAD**

Fresh commands:

```bash
python -m pip install -e ".[dev]"
pytest -q
python -m compileall -q src tests
python - <<'PY'
from pathlib import Path
import tomllib
p = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
assert p["project"]["dependencies"] == []
for path in (
    "src/andes_context_os/internal_context.py",
    "src/andes_context_os/adapters/internal_context.py",
):
    assert Path(path).exists()
print("v0.3_final_gate=PASS")
PY
```

Expected: install succeeds, full pytest has zero failures, compileall exits 0, final gate prints `PASS`.

- [ ] **Step 7: Verify GitHub Actions on the exact feature HEAD**

Push `feat/v0.3-authorized-context-producer`, then require the `tests` workflow to finish `conclusion=success` on the exact HEAD SHA with Python 3.11 and `pytest -q` green. Record run ID, job ID, exact HEAD SHA, and test count in the private benchmark note.

- [ ] **Step 8: Commit only the private benchmark note to the private vault**

Commit the V0.3 benchmark note in `geoplatform-knowledge-base`. Do **not** add the private manifest or receipts to `andes-context-os`.

---

## Final Requirement Checklist

Before asking to integrate V0.3, verify each item explicitly:

- [ ] Exact manifest only; no search/enumeration API exists.
- [ ] `InternalContextRecord` and `InternalContextCatalog` contracts were reused unchanged.
- [ ] Manifest metadata is curated and never extracted from content.
- [ ] Every successful record has exactly one receipt.
- [ ] Exact bytes determine `source_content_sha256`.
- [ ] Optional source identity and content pins fail closed.
- [ ] Missing resolver, resolver exception, malformed return, identity mismatch, and hash mismatch map to the five closed reasons.
- [ ] Failed entries emit no record and no receipt.
- [ ] Partial/failed/complete statuses follow the spec exactly.
- [ ] Production output never serializes locator, content, raw exception, or pin mismatch details.
- [ ] Output ordering is deterministic under manifest reorder.
- [ ] Empty manifest returns complete empty production.
- [ ] Public sample is fictitious/public-safe.
- [ ] No concrete GitHub/Vault resolver is in the public core.
- [ ] No runtime dependency was added.
- [ ] V0.2.1 regression suite remains green.
- [ ] Private Agua Negra/Filo benchmark produces 8/8 records + 8 receipts + 0 failures.
- [ ] Unauthorized ninth reference is never resolved.
- [ ] Feature-branch GitHub Actions is green on the exact reviewed HEAD.
