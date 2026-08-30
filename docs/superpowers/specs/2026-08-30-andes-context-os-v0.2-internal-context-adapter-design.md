# Andes Context OS V0.2 — Internal Context Adapter Design

Date: 2026-08-30
Status: review
Branch: `feat/internal-context-adapter`
Applies to: Andes Context OS V0.1 contract core

## 1. Decision

V0.2 adds the first internal-context subsystem to Andes Context OS.

The subsystem converts a small, explicit catalog of internal references into an immutable `InternalContextSnapshot` for a `ResearchIntent` + `TerritorialScope` pair.

```text
ResearchIntent + TerritorialScope
              ↓
      InternalContextCatalog
              ↓
     InternalContextAdapter
              ↓
    InternalContextSnapshot
              ↓
         DiscoveryRun lineage
```

The implementation is local and deterministic. V0.2 does **not** connect directly to GitHub, the private vault, a database, an LLM, embeddings, or any external service.

Later authorized producers may translate Vault/GitHub/private workspace material into the same public `InternalContextRecord` contract without changing the core selection semantics defined here.

## 2. Purpose

V0.1 can preserve questions, territory, external-source metadata, runtime source observations, evidence candidates and reproducible discovery runs. It cannot yet represent the small amount of existing internal knowledge that should be checked before a new research pass.

The canonical discovery recipe requires progressive retrieval:

```text
small snapshot
→ identify exact item
→ fetch only the needed detail
```

V0.2 therefore answers:

> Which previously known internal references are relevant enough to inspect next, and why were they selected?

It is not a vault search engine.

## 3. Design principles

### 3.1 Internal context informs; it does not prove

```text
internal context match != evidence validation
known evidence reference != current operational evidence
known decision != current authorization
```

### 3.2 Progressive retrieval is mandatory

Snapshots contain short summaries and stable references only. They do not copy full notes, private documents, source payloads or repository contents.

### 3.3 Public contract, private runtime data

The public repository contains contracts, deterministic selection logic, tests, fictitious example data and documentation.

Private runtime may contain real vault references, private repository references, sensitive evidence references, decisions and gaps. Real private context is not committed to the public repository.

### 3.4 No synthetic relevance score

V0.2 adds no `relevance_score`, `confidence_score`, weighted rank or aggregate score. Match reasons remain categorical and explicit.

### 3.5 Missing context degrades safely

No match is a valid empty result, not provider failure. Malformed catalog data fails closed.

## 4. Core contracts

### 4.1 `InternalContextKind`

```text
vault_note
repository
feature
known_source
known_evidence
known_gap
known_decision
```

### 4.2 `ContextSensitivity`

```text
public
internal
restricted
```

- `public`: safe for public/fictitious examples;
- `internal`: usable locally but not publishable automatically;
- `restricted`: may exist locally but is never emitted by V0.2.

A future authorization layer may define a different restricted-data policy. V0.2 does not.

### 4.3 `InternalContextRecord`

```text
contract_version
context_id
kind
title
reference
summary
domains[]
activities[]
territory_refs[]
tags[]
sensitivity
reviewed_at optional
limitations[]
```

Rules:

- `contract_version = "0.1"` to remain compatible with the V0.1 contract core;
- `context_id`, `title`, `reference`, and `summary` are non-empty strings;
- `domains[]` use the existing `ResearchDomain` vocabulary;
- `activities[]` use the existing `ResearchActivity` vocabulary;
- `territory_refs[]` are stable typed references used for exact matching, not inferred territorial claims;
- `reviewed_at`, when present, is timezone-aware ISO-8601;
- unknown fields fail closed;
- malformed lists fail closed;
- `limitations[]` remain separate from match reasons.

### 4.4 `InternalContextCatalog`

```text
catalog_version
records[]: InternalContextRecord
```

V0.2 catalog version is `0.1`.

Rules:

- duplicate `context_id` values are rejected;
- record order is not semantically meaningful;
- catalog loading is local JSON only;
- no network access;
- no separate catalog hash is required in V0.2 because the resulting snapshot is content-addressed.

## 5. Selection semantics

The adapter interface is:

```python
snapshot(
    intent: ResearchIntent,
    scope: TerritorialScope,
    catalog: InternalContextCatalog,
    *,
    generated_at: str,
) -> InternalContextSnapshot
```

The adapter computes these categorical reasons:

```text
domain_match
activity_match
territory_match
```

### 5.1 Domain match

```text
intent.domain ∈ record.domains
```

No synonym expansion, fuzzy matching, embeddings or LLM classification exists in V0.2.

### 5.2 Activity match

```text
intent.activity ∈ record.activities
```

### 5.3 Territory match

Stable scope references are derived only from structured fields and are namespaced by reference type:

```text
country:<country_code>
admin:<country_code>:<admin_level>:<official_code>
project:<project_ref>
corridor:<corridor_ref>
segment:<segment_ref>
geometry:<geometry_ref>
```

Examples include `country:AR`, `admin:AR:1:J`, and `corridor:agua-negra-v1`. An unprefixed administrative code such as `J` is intentionally not matchable.

`territory_match` requires exact equality with one of `record.territory_refs[]`. Namespacing prevents collisions between countries, administrative systems, and different reference types.

V0.2 does not infer equivalence from names, bbox overlap, proximity or administrative hierarchy.

### 5.4 Eligibility rule

A non-restricted record is eligible only when both gates below pass.

**Territorial gate**

```text
record.territory_refs is empty
OR territory_match is true
```

A territorial-specific record therefore cannot enter a Peru or Chile snapshot merely because it shares the same mining domain.

**Semantic gate**

```text
if record.domains or record.activities are non-empty:
    domain_match OR activity_match must be true
else:
    territory_match must be true
```

This allows generic domain/activity references while keeping territorial-specific records tied to explicit scope identity.

Every selected item preserves all match reasons that applied. No numeric rank is produced.

### 5.5 Deterministic ordering

Selected records are sorted by:

```text
kind
context_id
```

so catalog input order cannot alter serialized snapshot content.

## 6. Snapshot contract

### 6.1 `ContextSelection`

```text
context_id
kind
title
reference
summary
match_reasons[]
limitations[]
```

`match_reasons[]` are sorted deterministically and duplicate reasons are rejected rather than silently collapsed. Tags and full matching vocabularies are not projected downstream.

### 6.2 `InternalContextSnapshot`

```text
contract_version
snapshot_version
snapshot_id
generated_at
research_intent_id
question_profile_ref optional
territorial_scope_id
related_vault_notes[]
related_repositories[]
related_features[]
known_sources[]
known_evidence[]
known_gaps[]
known_decisions[]
missing_context[]
```

`snapshot_version = "0.1"`.

`question_profile_ref` is copied from `ResearchIntent.question_profile_ref`.

Each category contains immutable `ContextSelection` tuples. A `context_id` may appear at most once across the complete snapshot; both `build()` and `from_dict()` reject duplicates.

Category mapping:

```text
vault_note      -> related_vault_notes
repository      -> related_repositories
feature         -> related_features
known_source    -> known_sources
known_evidence  -> known_evidence
known_gap       -> known_gaps
known_decision  -> known_decisions
```

### 6.3 Content-addressed `snapshot_id`

`snapshot_id` has one rule only: it is the lowercase SHA-256 returned by the existing canonical `sha256_json()` helper over the complete serialized snapshot payload **excluding `snapshot_id` itself**.

Consequences:

- changing selected context changes snapshot identity;
- changing a selected summary or limitation changes snapshot identity;
- changing `generated_at` changes snapshot identity;
- changing only catalog input order does not change snapshot identity because selections are canonicalized first.

This makes the snapshot self-identifying without introducing a separate catalog hash.

## 7. Empty and restricted behavior

### 7.1 Empty catalog or no eligible matches

Produce a valid snapshot with empty category tuples and:

```text
missing_context = ["no internal context matched the current intent and territorial scope"]
```

This is not adapter failure.

### 7.2 Restricted matching records

A `restricted` record is never emitted.

If one or more restricted records would otherwise be eligible, append exactly one generic message:

```text
"restricted internal context was omitted"
```

The message must not leak IDs, counts, titles, references, summaries, tags or territorial metadata.

If unrestricted matches also exist, the snapshot contains those matches plus the generic omission message.

## 8. Error behavior

Fail closed for:

- malformed JSON catalog;
- unsupported catalog version;
- duplicate catalog `context_id`;
- duplicate snapshot `context_id`;
- duplicate `match_reasons`;
- unsupported kind or sensitivity;
- unsupported domain/activity values;
- naive `reviewed_at` or `generated_at`;
- unknown contract fields;
- malformed list values;
- empty required strings.

Errors must not echo private summaries or references.

## 9. File layout

```text
src/andes_context_os/
├── internal_context.py
└── adapters/
    ├── __init__.py
    └── internal_context.py

data/
└── internal_context.example.v0.1.json

tests/
├── test_internal_context.py
└── test_internal_context_adapter.py
```

No new runtime dependency is allowed.

## 10. Example catalog policy

`data/internal_context.example.v0.1.json` contains fictitious/public-safe examples only.

Permitted examples include a public repository capability, a fictional corridor note, and a known-gap example about data freshness. Territorial examples use the same typed reference convention as runtime matching, for example `corridor:example-corridor-v1`.

It must not contain private vault text, private repository URLs, private AOIs, contact data, unpublished institutional context, credentials or secrets.

## 11. DiscoveryRun integration

V0.2 does not modify the stabilized `DiscoveryRun` contract.

A caller records the snapshot through the existing lineage field:

```text
lineage.internal_snapshot_ref = "internal-context:" + snapshot.snapshot_id
```

When selected context records materially informed the run, their stable IDs should also be represented in `lineage.input_refs[]` using:

```text
internal-context-record:<context_id>
```

This is a lineage convention, not evidence promotion.

## 12. Testing strategy

Required coverage:

1. strict `InternalContextRecord` parsing;
2. closed kind/sensitivity/domain/activity vocabularies;
3. timezone-aware `reviewed_at`;
4. duplicate catalog IDs fail closed;
5. local JSON catalog load;
6. exact domain matching;
7. exact activity matching;
8. exact typed structured territory matching;
9. administrative refs are namespaced by country and level;
10. raw ambiguous admin codes do not match;
11. territorial-specific records cannot match a different territory by domain alone;
12. empty result produces a valid explicit missing-context snapshot;
13. multiple match reasons are preserved without scores;
14. duplicate match reasons fail closed;
15. duplicate snapshot context IDs fail closed in both build and parse paths;
16. catalog order does not change snapshot ordering or `snapshot_id` when `generated_at` is fixed;
17. meaningful selected-content changes change `snapshot_id`;
18. restricted matches are omitted without metadata/count leakage;
19. generated timestamp must be timezone-aware;
20. snapshot/category tuples are immutable;
21. secret-like/unknown fields are rejected;
22. full V0.1 regression suite remains green;
23. GitHub Actions remains green on Python 3.11.

## 13. Explicit non-goals

V0.2 does not:

- search GitHub;
- read the private vault;
- query Google Drive;
- read conversation memory;
- call an LLM;
- generate embeddings;
- fuzzy-match territory names;
- compute bbox intersections;
- rank records numerically;
- validate an internal reference as factual evidence;
- promote context into operational evidence;
- authorize a route, decision or action;
- write a database;
- expose an API or CLI.

## 14. Success criteria

The slice is complete when:

1. a strict local catalog loads with stdlib-only runtime code;
2. `ResearchIntent` + `TerritorialScope` yield a deterministic content-addressed `InternalContextSnapshot`;
3. territorial-specific records cannot cross-match by domain/activity alone or by ambiguous raw admin codes;
4. every selected item preserves explicit categorical match reasons without duplicates;
5. snapshot context IDs are globally unique;
6. no synthetic relevance/confidence score exists;
7. restricted records cannot leak through the snapshot;
8. empty context is represented explicitly rather than as provider failure;
9. existing `DiscoveryRun` lineage can reference the snapshot without changing the run contract;
10. the full V0.1 suite remains green;
11. CI is green on the feature branch.

## 15. Dependency direction

```text
ResearchIntent / TerritorialScope
            ↓
InternalContextAdapter
            ↓
InternalContextCatalog
            ↓
InternalContextRecord

Discovery orchestration (later)
            ↓ consumes snapshot
InternalContextSnapshot
```

`internal_context.py` and `adapters/internal_context.py` must not import GitHub clients, vault clients, databases, web libraries, LLM SDKs or GeoPlatform runtime code.

## 16. Roadmap after V0.2

Later authorized producers may include:

```text
VaultContextAdapter
GitHubProjectAdapter
QuestionRadarAdapter
```

Those producers should translate their systems into `InternalContextRecord` or a compatible provider boundary instead of bypassing the V0.2 snapshot contract.

The next project candidate after V0.2 remains the Public Dataset Adapter unless the internal-context benchmark demonstrates a higher-value integration first.
