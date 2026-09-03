# Andes Context OS V0.4 — Asset Movement Dogfood Design

Date: 2026-09-02
Status: review
Proposed branch: `feat/v0.4-asset-movement-dogfood`
Applies to: Andes Context OS V0.3 public research/evidence core

> **Versioning note:** `V0.4` is the repository feature milestone. New payloads continue to use the repository's existing `CONTRACT_VERSION = "0.1"` unless a separate repository-wide contract-version migration is explicitly designed later.

## 1. Decision

V0.4 adds a small interpretation layer above the existing research and evidence contracts so Andes Context OS can dogfood one question:

> **Can we reconstruct, reproducibly and without collapsing signal into fact, how actors change around real mining assets as those assets move through exploration, construction, production and expansion?**

The initial benchmark uses three Argentine lithium assets already present in the checked-in Atlas Geotech snapshot:

- `project_id:258` — Río Grande / NOA Lithium, Salta;
- `project_id:137` — Hombre Muerto Oeste, Catamarca;
- `project_id:52` — Cauchari-Olaroz, Jujuy.

Atlas Geotech is used only as a **baseline asset reference**. It is not treated as a live source or as proof that a project stage, ownership structure or operating condition is still current.

The V0.4 flow is:

```text
Atlas Geotech baseline reference
        ↓
Asset
        ↓
ResearchIntent + TerritorialScope
        ↓
registered source + runtime observation
        ↓
EvidenceCandidate
        ↓
Movement
        ↓
Actor participation
        ↓
OpportunityHypothesis
        ↓
missing context / next research question
```

V0.4 deliberately keeps these statements distinct:

```text
baseline record != current state
signal != fact
evidence candidate != movement
movement != opportunity
actor proximity != relationship
opportunity hypothesis != demand
supporting evidence != commercial validation
```

## 2. Why this slice exists

Andes Context OS already has strong contracts for:

- `ResearchIntent`;
- `TerritorialScope`;
- `SourceRegistry`;
- `SourceRuntimeObservation`;
- `EvidenceCandidate`;
- `EvidenceQualityVector`;
- `DiscoveryRun`;
- authorized internal context.

Those contracts answer questions such as:

- what did we ask?;
- where exactly?;
- which source was registered?;
- what happened when it was checked?;
- what evidence candidate was produced?;
- how fresh, complete, corroborated and reviewable is it?;
- what is missing or contradictory?

The current core does **not** model the next interpretive layer:

- what changed around an asset?;
- which actors participated in that change?;
- what role did each actor play in that specific movement?;
- what potential need or opportunity is worth investigating next?

V0.4 adds only that layer. It does not replace the evidence subsystem and does not weaken its boundaries.

## 3. Architectural choice

Three approaches were considered.

### 3.1 Extend `EvidenceCandidate` with actor and opportunity fields

Rejected.

This would mix source-supported evidence with downstream interpretation and make it difficult to distinguish:

```text
what a source supports
from
what the research process infers from it
```

### 3.2 Add a small asset-movement layer above evidence

Selected.

New contracts reference existing evidence IDs rather than embedding or rewriting evidence semantics.

```text
EvidenceCandidate[]
       ↓
Movement
       ↓
OpportunityHypothesis
```

### 3.3 Introduce a fully generic graph engine

Deferred.

A node/edge/event graph may become useful later, especially if cross-project actor relationships become a repeated query. It is premature for the first benchmark and would add abstraction before the dogfood demonstrates that it is needed.

## 4. Core design principles

### 4.1 Evidence remains the authority boundary

A `Movement` may summarize a change only by referencing one or more existing `EvidenceCandidate` IDs.

A movement never upgrades the quality, freshness, corroboration or review state of its supporting evidence.

### 4.2 Asset identity is not asset truth

`Asset` is a stable research anchor, not a live project record.

It may preserve:

- stable asset identity;
- canonical name;
- commodity;
- territorial scope reference;
- baseline source identity;
- baseline record reference.

It must not silently preserve mutable claims such as current stage, current ownership or current operating status as timeless attributes.

Those claims belong in evidence and, when a change is observed, in movements.

### 4.3 Actor identity is separate from actor role

An actor can play different roles in different contexts.

For example, an organization may be:

- operator in one asset;
- partner in another;
- contractor in a third;
- financier or offtaker in a later event.

Therefore `Actor` stores stable identity. Role is recorded in each movement through `MovementActorRef`.

### 4.4 Movement is an evidence-linked interpretation

A movement is not raw source content.

It is a **candidate or reviewed research interpretation** that a meaningful change occurred, linked back to the evidence candidates that support that interpretation.

A movement's `review_state` determines whether an operator has accepted that interpretation for research use.

### 4.5 Opportunity is explicitly hypothetical

`OpportunityHypothesis` is the only V0.4 contract allowed to express a possible need or commercial implication.

It must preserve:

- triggering movement IDs;
- supporting evidence IDs;
- assumptions;
- missing context;
- review status.

No hypothesis may be represented as confirmed demand solely because an asset changed stage or an actor appeared.

### 4.6 No magic score

V0.4 introduces no global score for:

- opportunity quality;
- actor relevance;
- market attractiveness;
- likelihood of demand;
- truth;
- confidence.

Existing evidence dimensions remain separate. Opportunity review state remains categorical.

### 4.7 Runtime remains dependency-light

V0.4 stays inside the current stdlib-first Python core.

It does not add:

- HTTP clients;
- GitHub clients;
- web scraping;
- Reddit scraping;
- databases;
- LLM SDKs;
- embeddings;
- graph databases;
- FastAPI;
- React;
- MCP;
- n8n.

External research can continue to happen outside the core and be imported through existing observation/evidence contracts.

## 5. New contracts

### 5.1 `AssetType`

V0.4 initially supports one value:

```text
mining_project
```

The enum exists so later benchmark domains can extend the contract without overloading free text.

### 5.2 `Asset`

```text
contract_version
asset_id
name
asset_type
commodity
territorial_scope_ref
baseline_source_id
baseline_record_ref
notes[]
```

Rules:

- unknown fields fail closed;
- all IDs and required text fields are non-empty;
- `asset_type` must parse through `AssetType`;
- `territorial_scope_ref` must be explicit and non-empty;
- `baseline_source_id` identifies the source system, not a liveness claim;
- `baseline_record_ref` must identify one exact source record;
- mutable project claims such as current stage and current ownership are prohibited from the V0.4 `Asset` schema;
- duplicate `asset_id` values are rejected by benchmark/catalog loaders.

Initial assets:

```text
asset:ar:li:rio-grande-noa
  baseline_source_id: atlas-geotech
  baseline_record_ref: project_id:258

asset:ar:li:hombre-muerto-oeste
  baseline_source_id: atlas-geotech
  baseline_record_ref: project_id:137

asset:ar:li:cauchari-olaroz
  baseline_source_id: atlas-geotech
  baseline_record_ref: project_id:52
```

### 5.3 `ActorKind`

```text
organization
government_body
person
community
other
```

The kind describes stable identity shape, not commercial role.

### 5.4 `Actor`

```text
contract_version
actor_id
canonical_name
actor_kind
jurisdiction optional
external_refs[]
notes[]
```

Rules:

- `actor_id` and `canonical_name` are non-empty;
- `actor_kind` must parse through `ActorKind`;
- `external_refs` are explicit identifiers or canonical references supplied by the caller;
- V0.4 performs no fuzzy name matching, entity resolution or automatic deduplication;
- duplicate `actor_id` values are rejected by benchmark/catalog loaders;
- actor records do not imply a relationship to any asset.

### 5.5 `ActorRole`

V0.4 movement-local roles:

```text
operator
owner
partner
contractor
consultant
supplier
financier
offtaker
regulator
state_partner
community_actor
other
```

Roles are intentionally attached to movements rather than actors.

### 5.6 `MovementActorRef`

```text
actor_id
role
notes[]
```

Rules:

- `actor_id` must reference an actor in the benchmark/catalog context used for validation;
- `role` must parse through `ActorRole`;
- the same actor may appear across different movements with different roles;
- duplicate `(actor_id, role)` pairs inside one movement are rejected.

### 5.7 `MovementType`

Initial values:

```text
stage_change
drilling
permit
capital
ownership
partnership
contractor
consulting
offtake
construction
infrastructure
production
expansion
hiring
other
```

The enum is deliberately small and may only be expanded after dogfood evidence shows a recurring missing category.

### 5.8 `MovementReviewState`

```text
unreviewed
evidence_linked
reviewed
rejected
superseded
```

Semantics:

- `unreviewed`: candidate movement assembled but not checked by an operator;
- `evidence_linked`: evidence references are structurally valid but interpretation has not been reviewed;
- `reviewed`: operator accepts the movement as a defensible research interpretation of the referenced evidence;
- `rejected`: interpretation is not accepted;
- `superseded`: a later movement record replaces this interpretation while preserving lineage.

`reviewed` does not mean institutionally verified or universally true. Evidence quality remains authoritative for those dimensions.

### 5.9 `Movement`

```text
contract_version
movement_id
asset_id
movement_type
observed_at
actor_refs[]: MovementActorRef
evidence_candidate_refs[]
factual_summary
previous_state optional
new_state optional
review_state
reviewed_at optional
derived_from_movement_ids[]
limitations[]
```

Rules:

- `asset_id` must reference an existing `Asset` in the validation context;
- at least one `evidence_candidate_ref` is required;
- evidence references must be unique;
- `factual_summary` must be non-empty;
- keeping demand/opportunity claims out of `factual_summary` is an operator/fixture acceptance rule, not a parser-level semantic classifier in V0.4;
- `observed_at` must be timezone-aware ISO-8601 and means **when this movement interpretation was recorded by the research process**, not necessarily the exact time the real-world event occurred;
- `stage_change` requires both `previous_state` and `new_state`, and the two values must differ;
- other movement types may optionally include state fields when the source explicitly supports a before/after transition;
- `reviewed_at` is required for `reviewed`, `rejected` and `superseded` states and must be null for `unreviewed` and `evidence_linked`;
- `reviewed_at`, when present, must be timezone-aware ISO-8601;
- `derived_from_movement_ids` cannot contain the movement's own ID;
- duplicate derived IDs are rejected;
- unknown fields fail closed.

### 5.10 `OpportunityStatus`

```text
proposed
researching
supported
contradicted
discarded
```

Semantics:

- `proposed`: plausible research hypothesis generated from observed movement;
- `researching`: additional evidence is actively being sought;
- `supported`: collected evidence supports continued consideration of the hypothesis;
- `contradicted`: evidence materially undermines the hypothesis;
- `discarded`: operator chooses to stop pursuing it.

`SUPPORTED` is not equivalent to confirmed demand, signed procurement intent, willingness to pay or commercial validation.

### 5.11 `OpportunityHypothesis`

```text
contract_version
hypothesis_id
asset_id
trigger_movement_refs[]
actor_refs[]
need_category
statement
supporting_evidence_refs[]
assumptions[]
missing_context[]
status
created_at
reviewed_at optional
```

Rules:

- at least one `trigger_movement_ref` is required;
- trigger movement IDs must be unique;
- `asset_id` must match the asset referenced by every trigger movement in V0.4;
- `actor_refs` must be unique and resolve to existing actors in the validation context;
- `statement` and `need_category` are non-empty;
- `assumptions` and `missing_context` remain explicit lists and are never silently removed when status changes;
- `supported` requires at least one `supporting_evidence_ref` that is **not merely evidence already used to establish the triggering movement(s)**;
- `contradicted` requires at least one supporting evidence reference whose research interpretation materially challenges the hypothesis;
- `reviewed_at` is required for `supported`, `contradicted` and `discarded`, and must be null for `proposed` and `researching`;
- `created_at` and `reviewed_at`, when present, must be timezone-aware ISO-8601;
- unknown fields fail closed.

The parser validates local shape. Whether a supporting evidence reference is additional to trigger evidence is checked by the cross-object validator, which has access to both movements and evidence IDs.

## 6. Existing contracts reused unchanged

V0.4 does not modify the semantics of:

```text
ResearchIntent
TerritorialScope
SourceRegistry
SourceRuntimeObservation
EvidenceCandidate
EvidenceQualityVector
DiscoveryRun
InternalContextRecord
InternalContextSnapshot
```

In particular, `EvidenceCandidate` remains the provenance-rich unit for source-supported research claims.

V0.4 may reference evidence IDs but must not mutate the evidence object to attach movements, actors or opportunity fields.

## 7. Atlas Geotech boundary

Atlas Geotech is a sibling repository and remains independent.

V0.4 does not add a network dependency on Atlas Geotech and does not import its R/Shiny runtime.

For the initial benchmark, each `Asset` stores only an exact baseline reference such as:

```text
baseline_source_id = "atlas-geotech"
baseline_record_ref = "project_id:258"
```

The dogfood fixture may include a manually curated note stating which Atlas snapshot was inspected, but mutable claims copied from Atlas must enter the research flow as evidence if they are compared with later information.

Future work may define an Atlas adapter only after the benchmark demonstrates that repeated manual translation is a real bottleneck.

## 8. Initial dogfood benchmark

### 8.1 Río Grande / NOA Lithium — Salta

Purpose: observe actor formation around an exploration/development asset.

Baseline:

```text
asset:ar:li:rio-grande-noa
atlas-geotech project_id:258
```

Initial research prompts:

- what drilling or hydrogeological work changed recently?;
- which contractors or consultants were explicitly named?;
- which permitting or government actors appeared?;
- which needs are facts and which are only plausible downstream hypotheses?

### 8.2 Hombre Muerto Oeste — Catamarca

Purpose: observe transition from construction toward commissioning/production.

Baseline:

```text
asset:ar:li:hombre-muerto-oeste
atlas-geotech project_id:137
```

Initial research prompts:

- which evidence supports a stage transition after the Atlas baseline?;
- which operating, commercial or technical partners appear during ramp-up?;
- which potential service needs become worth researching without being assumed?

### 8.3 Cauchari-Olaroz — Jujuy

Purpose: observe how an operating asset generates new movements during expansion.

Baseline:

```text
asset:ar:li:cauchari-olaroz
atlas-geotech project_id:52
```

Initial research prompts:

- what expansion, capital, permitting or infrastructure movements are supported?;
- which current actors are explicitly connected to those movements?;
- which supplier or service hypotheses deserve a next research run?

## 9. Dogfood fixture shape

V0.4 adds checked-in, public, non-sensitive benchmark fixtures under:

```text
data/dogfood/argentina-lithium/
├── assets.json
├── actors.json
├── movements.json
└── opportunity_hypotheses.json
```

The fixtures contain only structured research outputs and references suitable for the public repository.

They must not contain:

- private contact details;
- private vault content;
- Gmail bodies;
- Apollo payloads;
- secrets;
- guessed emails;
- copyrighted article text beyond minimal source references;
- operational authorization claims.

Evidence candidates remain represented through existing evidence fixtures/contracts or exact IDs produced by a benchmark run. The movement fixture does not duplicate raw source content.

## 10. Validation boundary

Individual `from_dict()` contracts validate local shape and enum semantics.

Cross-object validation is handled by a small deterministic benchmark validator rather than by hidden global state.

The validator receives explicit collections:

```text
assets
actors
movements
evidence_candidates
opportunity_hypotheses
```

It verifies:

- referenced assets exist;
- referenced actors exist;
- referenced evidence candidates exist;
- referenced trigger movements exist;
- trigger movements belong to the same asset as the hypothesis;
- opportunity actor refs resolve and are unique;
- `supported` hypotheses contain at least one evidence reference beyond the evidence already used by all trigger movements;
- rejected movements cannot be the sole trigger basis for a `supported` hypothesis;
- duplicate IDs are rejected;
- duplicate actor-role references inside a movement are rejected;
- self-referential movement lineage is rejected.

The validator performs no network calls and no fuzzy resolution.

## 11. Error handling

V0.4 follows the current fail-closed style.

Examples:

- unknown enum value → `ValueError`;
- unknown field → `ValueError`;
- missing required reference → validation failure;
- `stage_change` without two distinct states → validation failure;
- reviewed movement without `reviewed_at` → validation failure;
- `supported` hypothesis without additional supporting evidence → validation failure;
- duplicate IDs → validation failure;
- malformed timestamp → validation failure.

Error messages must identify the failing field or ID but must not echo source payload bodies or secret-like locators.

A partially populated benchmark is allowed only when every missing element is explicit. The validator must never manufacture placeholder actors, evidence or states to make the graph complete.

## 12. Testing strategy

Implementation follows TDD and the existing contract-test style.

New test files:

```text
tests/test_assets.py
tests/test_movements.py
tests/test_asset_movement_benchmark.py
```

### 12.1 Asset tests

Cover:

- valid asset round-trip;
- unsupported `AssetType`;
- unknown fields;
- empty IDs/text;
- exact baseline reference preservation;
- rejection of mutable unapproved fields such as `current_stage` if added to payload.

### 12.2 Actor tests

Cover:

- valid actor round-trip;
- actor kind parsing;
- stable identity independent of role;
- duplicate actor IDs in benchmark validation;
- no fuzzy alias merging.

### 12.3 Movement tests

Cover:

- valid movement round-trip;
- every movement type enum;
- required evidence reference;
- actor-role uniqueness;
- stage change state requirements;
- aware timestamps;
- review-state / `reviewed_at` combinations;
- self-lineage rejection;
- rejected/superseded semantics remain explicit.

### 12.4 Opportunity hypothesis tests

Cover:

- valid proposed/researching/supported/contradicted/discarded states;
- at least one trigger movement;
- actor refs resolve and are unique;
- supported requires evidence beyond trigger evidence;
- reviewed states require `reviewed_at`;
- assumptions and missing context survive round-trip;
- same-asset trigger rule.

### 12.5 Benchmark integration tests

Use the three checked-in assets to verify:

- every cross-reference resolves;
- no opportunity hypothesis exists without a movement trigger;
- no movement exists without evidence references;
- Atlas baseline references remain exact;
- deterministic serialization produces stable output for the same fixture;
- fixture order does not change semantic validation results.

## 13. Acceptance criteria

V0.4 is complete when the repository can represent the three benchmark assets and answer, from structured public fixtures:

```text
WHAT CHANGED?
WHEN WAS THE CHANGE RECORDED BY THE RESEARCH PROCESS?
WHICH ACTORS PARTICIPATED?
WHAT ROLE DID EACH ACTOR PLAY IN THAT MOVEMENT?
WHICH EVIDENCE CANDIDATES SUPPORT THE MOVEMENT?
WHAT IS STILL ONLY AN OPPORTUNITY HYPOTHESIS?
WHAT ADDITIONAL EVIDENCE SUPPORTS THAT HYPOTHESIS?
WHAT ASSUMPTIONS DOES THAT HYPOTHESIS REQUIRE?
WHAT CONTEXT IS STILL MISSING?
```

Additional requirements:

1. all existing tests remain green;
2. new contracts round-trip deterministically;
3. cross-object references fail closed;
4. there is no network dependency;
5. there is no LLM dependency;
6. there is no automatic evidence promotion;
7. there is no automatic opportunity score;
8. there is no automatic outreach or contact resolution;
9. the three dogfood assets are reproducible from checked-in structured fixtures;
10. README changes, if any, describe V0.4 as an experimental dogfood layer rather than a proven market-intelligence product.

## 14. Explicit non-goals

V0.4 does **not** implement:

- a public Opportunity Feed;
- a landing page;
- a marketplace;
- contact discovery;
- Apollo integration;
- Gmail integration;
- outreach drafting or sending;
- RFQ/RFI generation;
- quote comparison;
- live scraping;
- scheduled monitoring;
- Reddit scraping;
- LinkedIn scraping;
- automatic entity resolution;
- relationship graph queries;
- geospatial proximity-based relationship inference;
- database persistence;
- REST API;
- web UI;
- MCP server;
- agents;
- n8n workflows;
- opportunity ranking;
- commercial scoring.

These remain possible future layers only if repeated dogfood demonstrates a concrete need.

## 15. Deferred relationship model

V0.4 intentionally does not add a generic `Relationship` object.

The benchmark first records:

```text
Movement
  └── MovementActorRef(actor_id, role)
```

A generic actor-to-actor or actor-to-asset relationship model should be introduced only if repeated benchmark questions require durable relations beyond individual movements, for example:

- Which contractors repeatedly appear across lithium projects?;
- Which consultant works with multiple operators?;
- How has an actor's role changed over time?;
- Which partnerships persist across multiple movements?

If those questions become common, V0.5 may extract durable relationships from reviewed movement history without changing the evidence boundary.

## 16. Future gates

After the three-asset benchmark, review the observed workflow before opening the next implementation slice.

Possible next gates, only if justified by repetition:

1. **Atlas adapter** — if exact asset seeding from Atlas becomes repetitive;
2. **relationship model** — if cross-asset actor queries become common;
3. **source adapters** — if manual runtime observations become the bottleneck;
4. **public feed renderer** — if reviewed movements are repeatedly worth publishing;
5. **outreach layer** — if supported opportunities repeatedly lead to a concrete communication task;
6. **stable tool contracts** — if research operations repeat enough to expose as callable tools;
7. **MCP** — only after those tool contracts stabilize.

The order is deliberately:

```text
dogfood
→ repeated pattern
→ contract
→ adapter/tool
→ automation
```

not:

```text
agent
→ scraper
→ MCP
→ discover what the product was supposed to do
```

## 17. Product boundary after V0.4

If this benchmark succeeds, Andes Context OS remains a conservative research core with one new capability:

> **It can preserve an evidence-linked history of meaningful movements around territorial assets and keep potential opportunities explicitly separate from observed facts.**

That is the V0.4 claim.

It is not yet a market-intelligence platform, supplier marketplace, autonomous research agent or commercial opportunity engine.
