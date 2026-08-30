# Andes Context OS V0.2 — Internal Context Adapter Design

Date: 2026-08-30
Status: review
Branch: `feat/internal-context-adapter`
Applies to: Andes Context OS V0.1 contract core

## 1. Decision

V0.2 adds the first internal-context subsystem to Andes Context OS.

The subsystem converts a small, explicit catalog of internal references into an immutable `InternalContextSnapshot` for a `ResearchIntent` + `TerritorialScope` pair.

The implementation is intentionally local and deterministic:

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

V0.2 does **not** connect directly to GitHub, the private vault, a database, an LLM, embeddings, or any external service.

A later authorized adapter may translate Vault/GitHub/private workspace material into the same public `InternalContextRecord` contract without changing the core selection semantics defined here.

## 2. Why this slice exists

Andes Context OS V0.1 can preserve questions, territory, external-source metadata, runtime source observations, evidence candidates and reproducible discovery runs.

It cannot yet represent the small amount of existing internal knowledge that should be checked before starting a new research pass.

The canonical discovery recipe requires progressive retrieval:

```text
small snapshot
→ identify exact item
→ fetch only the needed detail
```

The value of V0.2 is therefore not "search the whole vault". The value is a stable, auditable boundary that answers:

> Which previously known internal references are relevant enough to inspect next, and why were they selected?

## 3. Design principles

### 3.1 Internal context informs; it does not prove

An internal reference may indicate prior work, a known gap, a decision, a feature or an evidence lead.

It must not become verified evidence merely because it exists in a private note or repository.

```text
internal context match != evidence validation
known evidence reference != current operational evidence
known decision != current authorization
```

### 3.2 Progressive retrieval is mandatory

The snapshot stores high-density references and short summaries only.

It must not copy full vault notes, private documents, source payloads or repository contents.

### 3.3 Public contract, private runtime data

The public repository contains:

- contracts;
- deterministic selection logic;
- tests;
- fictitious example catalog;
- documentation.

Private runtime may contain:

- real vault references;
- private repository references;
- sensitive internal evidence references;
- private decisions or gaps.

Real private context is not committed to the public repository.

### 3.4 No synthetic relevance score

V0.2 must not add a generic `relevance_score`, `confidence_score` or weighted ranking.

Selection reasons are explicit and categorical.

### 3.5 Missing context degrades safely

An empty catalog or no matching records produces a valid empty snapshot with explicit missing-context information.

Malformed catalog data fails closed.

## 4. Core contracts

### 4.1 `InternalContextKind`

Closed vocabulary:

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

Closed vocabulary:

```text
public
internal
restricted
```

Semantics:

- `public`: safe to serialize into public/fictitious examples;
- `internal`: may be used locally but should not be published automatically;
- `restricted`: metadata may exist locally but must never be emitted by the public adapter unless an explicit future authorization layer allows it.

V0.2 selection excludes `restricted` records from snapshots by default.

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
- `context_id`, `title`, `reference`, and `summary` are non-empty;
- `domains[]` use the existing `ResearchDomain` vocabulary;
- `activities[]` use the existing `ResearchActivity` vocabulary;
- `territory_refs[]` are opaque stable references, not free-form claims of territorial identity;
- `reviewed_at`, when present, is timezone-aware ISO-8601;
- unknown fields fail closed;
- secret-like fields are rejected through strict top-level parsing;
- `limitations[]` remain separate from selection reasons.

### 4.4 `InternalContextCatalog`

```text
catalog_version
records[]: InternalContextRecord
```

V0.2 catalog version:

```text
0.1
```

Rules:

- duplicate `context_id` values are rejected;
- record order is not semantically meaningful;
- catalog loading is local JSON only;
- no network access;
- no catalog hash is required in V0.2 because `DiscoveryRun` already preserves explicit input refs and run lineage. If future private catalogs require snapshot identity, a catalog hash can be added in a later version rather than pre-optimizing V0.2.

## 5. Selection semantics

The adapter consumes:

```python
snapshot(
    intent: ResearchIntent,
    scope: TerritorialScope,
    catalog: InternalContextCatalog,
    *,
    generated_at: str,
) -> InternalContextSnapshot
```

A non-restricted record is selected when it has at least one explicit match to the current research context.

Supported match reasons:

```text
domain_match
activity_match
territory_match
```

### 5.1 Domain matching

A record matches the intent domain when:

```text
intent.domain ∈ record.domains
```

No synonym expansion, embeddings or fuzzy classification exist in V0.2.

### 5.2 Activity matching

A record matches when:

```text
intent.activity ∈ record.activities
```

### 5.3 Territory matching

The adapter derives stable scope references only from explicit structured scope fields:

```text
countries[]
admin_units[].official_code when present
project_refs[]
corridor_refs[]
segment_refs[]
geometry_ref when present
```

A record receives `territory_match` only when one of its `territory_refs[]` exactly equals one of those derived scope references.

The adapter must not infer territorial equivalence from names, proximity or bbox overlap in V0.2.

### 5.4 Inclusion rule

A record is included when at least one match reason exists.

The snapshot preserves all reasons that applied.

Example:

```text
GeoPlatform / Filo access note
→ domain_match
→ activity_match
→ territory_match
```

No numeric rank is produced.

### 5.5 Deterministic ordering

Selected records are sorted by:

```text
kind
context_id
```

so catalog input order cannot change snapshot serialization.

## 6. Snapshot contract

### 6.1 `ContextSelection`

Each selected item is projected to:

```text
context_id
kind
title
reference
summary
match_reasons[]
limitations[]
```

The projection deliberately omits selection metadata not needed downstream, including tags and full matching vocabularies.

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

Each category contains immutable `ContextSelection` tuples.

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

`snapshot_id` is caller-supplied or deterministically derived by a small helper from intent ID + scope ID + generated timestamp. It is identity, not evidence quality.

## 7. Empty and restricted behavior

### Empty catalog / no matches

Produce a valid snapshot with empty category tuples and:

```text
missing_context = ["no internal context matched the current intent and territorial scope"]
```

This is not an adapter failure.

### Restricted record

A `restricted` record is not emitted by V0.2.

If a restricted record would otherwise match, the snapshot adds:

```text
"restricted internal context was omitted"
```

to `missing_context` without leaking its title, reference, summary or ID.

This prevents the omission message itself from becoming a side channel.

## 8. Error behavior

Fail closed for:

- malformed JSON catalog;
- unsupported catalog version;
- duplicate `context_id`;
- unsupported kind or sensitivity;
- unsupported domain/activity values;
- naive `reviewed_at` or `generated_at`;
- unknown contract fields;
- malformed list values;
- empty required strings.

Error messages must not echo private summaries or references.

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

No changes to runtime dependencies are required.

## 10. Example catalog policy

`data/internal_context.example.v0.1.json` contains fictitious/public-safe examples only.

It may reference generic examples such as:

- a public GeoPlatform repository capability;
- a fictional San Juan corridor note;
- a known-gap example about road-condition freshness.

It must not include:

- private vault note contents;
- private repository URLs;
- contact names;
- private AOIs;
- unpublished institutional context;
- secrets or credentials.

## 11. DiscoveryRun integration

V0.2 does not add the full snapshot object directly inside `DiscoveryRun`.

Instead, a caller that uses internal context records the snapshot through existing lineage fields:

```text
lineage.internal_snapshot_ref
lineage.input_refs[]
```

This preserves V0.1 compatibility and avoids mutating a stabilized run contract merely to ship the first adapter.

A future DiscoveryRun contract version may embed a snapshot hash or richer internal-context lineage if real usage demonstrates the need.

## 12. Testing strategy

Required tests:

1. strict `InternalContextRecord` parsing;
2. closed kind/sensitivity/domain/activity vocabularies;
3. timezone-aware `reviewed_at`;
4. duplicate catalog IDs fail closed;
5. JSON catalog load;
6. exact domain match;
7. exact activity match;
8. exact structured territory match;
9. no match produces valid empty snapshot;
10. multiple match reasons are preserved without scores;
11. catalog order does not change snapshot content ordering;
12. restricted matching records are omitted without metadata leakage;
13. generated timestamp must be timezone-aware;
14. snapshot/category tuples are immutable;
15. secret-like/unknown fields are rejected;
16. full V0.1 regression suite remains green;
17. GitHub Actions remains green on Python 3.11.

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

1. a strict local catalog can be loaded without runtime dependencies;
2. a `ResearchIntent` + `TerritorialScope` pair yields a deterministic `InternalContextSnapshot`;
3. every selected item preserves explicit categorical match reasons;
4. no synthetic relevance/confidence score exists;
5. restricted records cannot leak through the public snapshot;
6. empty context is represented explicitly rather than treated as provider failure;
7. the snapshot can be referenced through existing `DiscoveryRun` lineage without changing the run contract;
8. the existing V0.1 suite remains green;
9. CI is green on the feature branch.

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

Once this deterministic boundary is proven, later slices may add authorized producers:

```text
VaultContextAdapter
GitHubProjectAdapter
QuestionRadarAdapter
```

Those adapters should translate external/private systems into `InternalContextRecord` or a compatible provider interface rather than bypassing the V0.2 snapshot contract.

The immediate next candidate after V0.2 remains the Public Dataset Adapter unless the internal-context benchmark demonstrates a higher-value integration first.
