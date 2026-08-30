# Andes Context OS V0.3 — Authorized Context Producer Design

Date: 2026-08-30
Status: review
Branch: `feat/v0.3-authorized-context-producer`
Applies to: Andes Context OS V0.2.1 internal-context subsystem

## 1. Decision

V0.3 adds an authorized internal-context producer in front of the existing V0.2/V0.2.1 selector.

The producer converts a small, explicit private manifest of exact approved references into validated `InternalContextRecord` objects plus source-resolution receipts.

```text
private authorized manifest
        ↓
AuthorizedContextProducer
        ↓
exact resolver boundary
        ↓
source exists + exact content bytes
        ↓
content SHA-256 + source identity receipt
        ↓
InternalContextRecord[]
        ↓
InternalContextCatalog
        ↓
InternalContextAdapter V0.2
        ↓
InternalContextSnapshot
```

V0.3 does **not** add repository search, vault search, recursive discovery, LLM summarization, embeddings, fuzzy matching, bulk ingestion, automatic tagging, automatic evidence promotion, or publication of private context.

The approved design is deliberately allowlist-first: the manifest decides what may be resolved. The resolver does not decide what is relevant.

## 2. Why this slice exists

The Agua Negra/Filo benchmark showed that the V0.2 selector can recover useful internal context with zero false positives or false negatives once a catalog exists, but constructing that catalog manually is now the main bottleneck.

V0.2.1 fixed the first benchmark metadata gap by preserving `reviewed_at` in `ContextSelection` and snapshot identity.

V0.3 addresses only the next bottleneck:

```text
exact approved internal reference
→ verify it still exists
→ identify exactly what bytes were read
→ attach curated metadata
→ produce InternalContextRecord
```

The producer reduces repetitive translation work without weakening the distinction:

```text
internal context match != evidence validation
known evidence reference != current operational evidence
source exists != source is current or authoritative
source content changed != permission to infer what changed
```

## 3. Core design principles

### 3.1 Authorization precedes resolution

A resolver may only receive locators already present in an `AuthorizedContextManifest`.

There is no search API in V0.3.

The producer must not:

- enumerate a repository;
- scan a vault directory;
- follow links discovered inside source content;
- infer neighboring files or notes;
- expand globs;
- recursively traverse directories;
- query by keyword.

### 3.2 Metadata is curated, not extracted

`InternalContextRecord` fields are supplied explicitly by the manifest.

The source content is read only to:

1. confirm that the authorized reference resolves;
2. compute an exact SHA-256 over the returned bytes;
3. preserve resolver/source identity in a receipt.

V0.3 does not derive or rewrite:

- `title`;
- `summary`;
- `domains[]`;
- `activities[]`;
- `territory_refs[]`;
- `tags[]`;
- `sensitivity`;
- `limitations[]`;
- `reviewed_at`.

This prevents a content parser or model from silently changing the semantic contract.

### 3.3 Producer provenance is separate from stable context semantics

V0.3 does **not** add source hashes or resolver fields to `InternalContextRecord`.

The existing record remains the semantic unit consumed by `InternalContextAdapter`.

Resolution provenance is represented separately by `ContextSourceReceipt`.

```text
InternalContextRecord
= what curated internal context means

ContextSourceReceipt
= exactly what source reference was resolved to produce it
```

### 3.4 Partial production is explicit

A single failed authorized reference does not justify emitting stale or unverified context for that entry.

If one entry fails resolution:

- no `InternalContextRecord` is emitted for that entry;
- the failure is recorded explicitly;
- successful independent entries may still be returned;
- overall production status becomes `partial` unless all entries failed.

The caller decides whether a partial catalog is sufficient for the next research step.

### 3.5 Runtime remains dependency-light

The public core uses Python 3.11+ stdlib only.

V0.3 defines an injectable exact resolver protocol. Concrete GitHub, filesystem, vault, connector, or workspace implementations remain outside the core contract and can be supplied by the runtime environment.

The core must not import GitHub SDKs, MCP clients, databases, HTTP libraries, LLM SDKs, or GeoPlatform runtime code.

## 4. Manifest contract

### 4.1 `AuthorizedContextManifest`

```text
manifest_version
entries[]: AuthorizedContextManifestEntry
```

V0.3 manifest version is `0.1`.

Rules:

- local/private input;
- duplicate `entry_id` values are rejected;
- duplicate `context_id` values are rejected;
- entry order is not semantically meaningful;
- unknown fields fail closed;
- no runtime search is triggered by manifest parsing.

The public repository may contain a fictitious example manifest only. Real private manifests must not be committed to the public repository.

### 4.2 `AuthorizedContextManifestEntry`

```text
entry_id
resolver_id
source_locator
expected_source_identity optional
expected_content_sha256 optional
context: InternalContextRecord payload
```

Rules:

- `entry_id`, `resolver_id`, and `source_locator` are non-empty strings;
- `context` must parse through the existing strict `InternalContextRecord.from_dict()` contract;
- `expected_source_identity`, when present, is a non-empty string;
- `expected_content_sha256`, when present, is exactly 64 lowercase hexadecimal characters;
- unknown fields fail closed;
- errors must not echo source content or secret-like locator payloads.

`source_locator` is resolver-specific and opaque to the producer. Examples in the public repository must be fictitious.

Possible runtime locator shapes include exact GitHub file/ref identifiers, exact local file paths, or exact vault-note identifiers. V0.3 does not standardize or parse those schemes inside the producer.

## 5. Resolver boundary

### 5.1 `ExactContentResolver`

The core depends on an injectable protocol equivalent to:

```python
class ExactContentResolver(Protocol):
    resolver_id: str

    def resolve(self, locator: str) -> ResolvedContextSource:
        ...
```

The producer selects a resolver by exact `resolver_id` from an explicit resolver registry supplied by the caller.

No default network resolver exists in V0.3.

### 5.2 `ResolvedContextSource`

```text
source_identity
content: bytes
```

Rules:

- `source_identity` is a non-empty stable identity returned by the resolver;
- `content` must be bytes;
- empty byte content is valid if the resolver successfully resolved an empty source;
- absence/unreadability is represented by resolver failure, not by a fake empty source.

The producer computes:

```text
source_content_sha256 = sha256(content).hexdigest()
```

No normalization, trimming, Unicode rewriting, JSON canonicalization, Markdown parsing, or newline conversion occurs before hashing.

The hash describes exactly the bytes returned by the resolver.

## 6. Source identity and pinning

### 6.1 Identity check

If `expected_source_identity` is present in the manifest, the resolved `source_identity` must match exactly.

Mismatch causes that entry to fail closed.

### 6.2 Content pin check

If `expected_content_sha256` is present, the computed SHA-256 must match exactly.

Mismatch causes that entry to fail closed.

V0.3 does not automatically refresh or rewrite the manifest pin.

### 6.3 Unpinned sources

If no expected content hash is supplied, a successfully resolved source may still produce a record.

Its actual `source_content_sha256` is always captured in the receipt.

This supports two valid modes:

```text
pinned reference
→ source must be exactly the approved bytes

unpinned exact reference
→ exact locator is approved; current bytes are recorded for provenance
```

The producer never interprets a changed hash as a semantic update by itself.

## 7. Production contracts

### 7.1 `ContextProductionStatus`

Closed vocabulary:

```text
complete
partial
failed
```

Rules:

- `complete`: every manifest entry produced a record;
- `partial`: at least one entry produced a record and at least one failed;
- `failed`: no manifest entry produced a record.

An empty manifest is valid and yields `complete` with an empty catalog and no failures.

### 7.2 `ContextSourceReceipt`

```text
entry_id
context_id
resolver_id
source_identity
source_content_sha256
```

Rules:

- emitted only for successful entries;
- one receipt per emitted `InternalContextRecord`;
- `context_id` must equal the produced record's context ID;
- receipt order is canonicalized by `(context_id, entry_id)`;
- source content itself is never stored in the receipt;
- SHA-256 is lowercase hexadecimal.

Receipts may contain private source identities and are therefore local/private runtime artifacts unless explicitly sanitized by a future publisher.

### 7.3 `ContextProductionFailureReason`

Closed vocabulary:

```text
resolver_not_registered
resolution_failed
source_identity_mismatch
content_hash_mismatch
invalid_resolved_source
```

### 7.4 `ContextProductionFailure`

```text
entry_id
context_id
reason
```

The failure object intentionally omits:

- source content;
- source locator;
- expected or actual source identity;
- expected or actual content hash;
- exception text.

This keeps downstream error reporting useful without turning failures into a secret side channel.

### 7.5 `AuthorizedContextProduction`

```text
manifest_version
status
catalog: InternalContextCatalog
receipts[]
failures[]
```

Rules:

- catalog records sorted by `context_id`;
- receipts sorted by `(context_id, entry_id)`;
- failures sorted by `(context_id, entry_id, reason)`;
- successful context IDs must be unique;
- each successful catalog record has exactly one receipt;
- failed entries emit no record and no receipt;
- no aggregate confidence, freshness, risk, or relevance score exists.

V0.3 does not need a second production hash. Exact source content hashes plus the existing deterministic catalog/snapshot identities provide sufficient provenance for this slice.

## 8. Producer API

The public API is conceptually:

```python
produce(
    manifest: AuthorizedContextManifest,
    resolvers: Mapping[str, ExactContentResolver],
) -> AuthorizedContextProduction
```

Algorithm:

```text
validate manifest
      ↓
canonicalize entries by (context_id, entry_id)
      ↓
for each entry:
    exact resolver lookup by resolver_id
      ↓
    resolve source_locator exactly
      ↓
    validate ResolvedContextSource
      ↓
    exact source identity check if pinned
      ↓
    SHA-256 exact bytes
      ↓
    exact content hash check if pinned
      ↓
    emit existing curated InternalContextRecord
    + ContextSourceReceipt

failed entry
→ no record
→ no receipt
→ explicit sanitized failure
      ↓
build deterministic InternalContextCatalog
      ↓
return production status + catalog + receipts + failures
```

The producer does not call `InternalContextAdapter` itself. Keeping production and selection separate preserves testability and allows the same produced catalog to be benchmarked against multiple intents/scopes.

## 9. Privacy and secret boundary

Real manifests and receipts are private runtime artifacts by default.

The public repository must never contain:

- private vault paths or note text;
- private repository URLs or refs;
- credentials;
- tokens;
- cookies;
- private AOIs;
- private contact data;
- unpublished institutional references;
- sensitive operational route details.

Strict parser tests must reject unknown secret-like fields such as:

```text
password
api_key
access_token
cookie
authorization
secret
```

Resolver exceptions must be converted into the closed failure reason `resolution_failed` without serializing raw exception text.

The producer must not log or return source bytes.

## 10. Interaction with V0.2/V0.2.1

V0.3 reuses `InternalContextRecord` and `InternalContextCatalog` unchanged.

The downstream flow remains:

```text
AuthorizedContextProduction.catalog
        ↓
InternalContextAdapter.snapshot(...)
        ↓
InternalContextSnapshot
```

`reviewed_at` remains curated manifest metadata. Resolving a source today does not automatically update its review date.

This distinction is intentional:

```text
resolved_at now
!=
reviewed_at now
```

V0.3 therefore adds no implicit freshness claim.

## 11. Agua Negra/Filo acceptance benchmark

The first real/private acceptance benchmark is the existing Agua Negra/Filo benchmark.

The private manifest will contain eight authorized entries corresponding to the eight previously curated internal references.

Success requires:

```text
manifest entries: 8
successful records: 8
failed entries: 0
status: complete
```

The resulting `InternalContextRecord` semantic payloads must match the previously curated benchmark records for:

- `context_id`;
- `kind`;
- `title`;
- `reference`;
- `summary`;
- `domains`;
- `activities`;
- typed `territory_refs`;
- `tags`;
- `sensitivity`;
- `reviewed_at`;
- `limitations`.

Every entry must additionally produce a content SHA-256 receipt.

The producer must prove that an unauthorized ninth reference is never resolved because it is absent from the manifest.

The downstream V0.2 adapter should then recover the same eight expected records for the benchmark intent/scope, subject only to the already documented `restricted` omission policy.

No real private manifest or receipt is committed to the public repository.

## 12. Failure behavior

Fail closed at manifest-parse time for:

- malformed JSON;
- unsupported manifest version;
- duplicate entry IDs;
- duplicate context IDs;
- malformed `InternalContextRecord` payloads;
- malformed expected SHA-256 values;
- empty required strings;
- malformed lists;
- unknown fields.

Fail closed per entry at production time for:

- missing resolver registration;
- resolver exception or unreadable locator;
- non-`ResolvedContextSource`/malformed resolver return;
- pinned source identity mismatch;
- pinned content hash mismatch.

Per-entry runtime failures produce sanitized `ContextProductionFailure` values rather than raising source-specific exception text into downstream code.

Programming/configuration errors that violate the producer's own object contracts may still raise `ValueError` during strict parsing/construction.

## 13. Determinism

Given:

- the same manifest semantic payload;
- the same resolver registry identities;
- the same resolved source identities;
- the same exact source bytes;

the serialized `AuthorizedContextProduction` is deterministic regardless of manifest entry order or resolver mapping order.

Changing source bytes changes the corresponding receipt hash.

If a pin is present, changing source bytes causes the entry to fail instead of silently producing a new record.

Changing only source bytes of an unpinned entry does **not** change the `InternalContextRecord` semantic payload because metadata is curated; it changes the receipt.

## 14. File layout

Planned public files:

```text
src/andes_context_os/
├── internal_context.py                  # existing; unchanged contract
└── producers/
    ├── __init__.py
    └── authorized_context.py            # new contracts + producer

data/
└── authorized_context.example.v0.1.json # fictitious/public-safe only

tests/
├── test_authorized_context_manifest.py
├── test_authorized_context_producer.py
└── test_authorized_context_release.py
```

README receives a concise V0.3 section after implementation.

No concrete GitHub/vault resolver is committed in V0.3 core. Tests use deterministic fake resolvers.

## 15. Testing strategy

Required coverage:

1. strict manifest entry round-trip;
2. strict manifest round-trip;
3. unknown manifest fields fail closed;
4. secret-like unknown fields fail closed without echoing values;
5. duplicate `entry_id` rejected;
6. duplicate `context_id` rejected;
7. malformed/unsupported manifest version rejected;
8. malformed expected SHA-256 rejected;
9. exact resolver chosen by `resolver_id`;
10. resolver not registered yields sanitized failure and no record;
11. resolver exception yields `resolution_failed` without raw exception leakage;
12. malformed resolver return yields `invalid_resolved_source`;
13. exact source identity pin success;
14. source identity mismatch fails closed for that entry;
15. exact content hash pin success;
16. content hash mismatch fails closed for that entry;
17. unpinned exact source records actual content SHA-256;
18. hash uses exact bytes with no normalization;
19. empty resolved bytes are hashable and valid;
20. successful record is semantically identical to manifest `InternalContextRecord`;
21. source content never appears in production serialization;
22. source locator never appears in production serialization;
23. failure serialization omits raw exception/source metadata;
24. partial status when some entries succeed and some fail;
25. failed status when all non-empty entries fail;
26. empty manifest yields complete empty production;
27. production independent of manifest entry order;
28. receipt/failure ordering deterministic;
29. one receipt per successful context ID;
30. no receipt for failed entry;
31. public example manifest loads and contains fictitious/public-safe data only;
32. full V0.2.1 regression suite remains green;
33. GitHub Actions remains green on Python 3.11;
34. no new runtime dependency is added.

## 16. Explicit non-goals

V0.3 does not:

- search GitHub;
- search or scan the private vault;
- enumerate repository trees;
- recursively walk directories;
- ingest arbitrary workspace files;
- infer manifest entries;
- summarize source content;
- extract metadata from Markdown/frontmatter;
- generate tags/domains/activities/territory refs;
- update `reviewed_at` automatically;
- compare document semantics;
- explain what changed between hashes;
- call an LLM;
- use embeddings;
- rank internal context;
- validate internal context as evidence;
- query public datasets;
- authorize routes or operational decisions;
- write a database;
- expose a UI/API/CLI;
- publish private manifests or receipts.

## 17. Success criteria

V0.3 is complete when:

1. a strict private manifest can express exact authorized source refs plus curated `InternalContextRecord` metadata;
2. only manifest-listed locators can reach a resolver;
3. the core resolves exact sources through injected resolvers without network/client dependencies;
4. each successful source produces one unchanged semantic record plus one exact content-hash receipt;
5. pinned identity/hash mismatches fail closed per entry;
6. failed entries never emit records or receipts;
7. failures are explicit and sanitized;
8. partial production is represented without pretending completeness;
9. source content and source locator are absent from production serialization;
10. production is deterministic under input reordering;
11. V0.2.1 snapshot semantics remain unchanged;
12. Agua Negra/Filo can replace the manual catalog-translation step with eight authorized manifest entries and recover the same benchmark context;
13. no real private manifest, source content, receipt, credential, AOI, or sensitive operational reference is committed publicly;
14. full regression and CI are green.

## 18. Roadmap after V0.3

If the authorized producer benchmark passes, the next candidate returns to the Public Dataset Adapter.

At that point the discovery flow becomes:

```text
ResearchIntent + TerritorialScope
        ↓
Authorized internal-context production
        ↓
InternalContextSnapshot
        ↓
known gaps
        ↓
Public Dataset Adapter
        ↓
external EvidenceCandidate(s)
        ↓
corroboration / contradictions / missing context
        ↓
DiscoveryRun
```

A future version may add concrete authorized GitHub or vault resolvers, but only after the exact-resolver contract proves sufficient. Search/discovery remains a separate future design problem rather than an implicit side effect of V0.3.
