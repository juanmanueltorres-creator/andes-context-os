# Andes Context OS — Roadmap

Andes Context OS exists to make territorial research reproducible **without collapsing source, evidence, context, interpretation, opportunity and authorization into one layer**.

The project evolves by adding narrow contracts around real research problems while keeping uncertainty explicit.

The governing rule is:

> preserve provenance, keep territorial scope explicit, and never promote a research hypothesis beyond what the evidence supports.

---

## How to read the milestones

The `V0.x` labels below are public contract / research milestones. They are not promises of a monolithic platform release.

The runtime remains intentionally dependency-light and the repositories in the wider workflow remain independent.

---

## Implemented

### ✅ V0.1 — Deterministic territorial discovery core

The original research path establishes the base contracts:

```text
ResearchIntent
  ↓
TerritorialScope
  ↓
SourceRegistry
  ↓
SourceRuntimeObservation
  ↓
EvidenceCandidate
  ↓
EvidenceQualityVector
  ↓
DiscoveryRun
```

Core boundaries:

```text
registered source != live source
public signal != verified fact
candidate != operational evidence
proximity != impact
```

The system freezes observations, missing context, contradictions, warnings and lineage rather than converting them into one confidence score.

### ✅ V0.2 — Internal Context Adapter

Adds deterministic selection from an explicitly curated local catalog.

Internal context can be matched by domain, activity and exact typed territorial identity, but it remains context rather than current evidence.

Boundary:

```text
internal context match != evidence validation
known evidence reference != current operational evidence
known decision != current authorization
```

No GitHub/vault crawling, fuzzy matching, embeddings or hidden search scope is introduced.

### ✅ V0.3 — Authorized Context Producer

Adds a producer for exact allowlisted references through an injected resolver.

It verifies identity and optional content pins, emits SHA-256 receipts, sanitizes failures and does not copy raw source content into the produced semantic catalog.

Boundary:

```text
manifest allowlist != search scope
resolved source != reviewed source
internal context != operational evidence
```

### ✅ V0.4 — Asset / Movement / Opportunity-Hypothesis dogfood

Adds a controlled interpretation layer for real-world project research:

```text
Asset baseline
  ↓
EvidenceCandidate
  ↓
Movement + actor roles
  ↓
OpportunityHypothesis
  ↓
assumptions + missing context
```

Initial Argentina lithium assets:

- Río Grande / NOA Lithium;
- Hombre Muerto Oeste;
- Cauchari-Olaroz.

Boundary:

```text
baseline record != current state
movement != opportunity
opportunity hypothesis != confirmed demand
actor participation != durable relationship
```

This milestone is explicitly dogfood, not a claim of validated market intelligence.

### ✅ V0.4.1 — Research-loop evidence refinement

Adds public evidence fixtures and exercises how a hypothesis changes when better evidence appears.

The important behavior is conservative state change:

```text
proposed → researching
```

without automatically producing:

```text
researching → supported
```

The Cauchari-Olaroz and Río Grande cases demonstrate that additional evidence can narrow a hypothesis without turning it into an externally addressable procurement package.

### ✅ V0.4.2 — HMW actor and evidence refinement

Adds Authium as an explicit Hombre Muerto Oeste actor with bounded roles and preserves an independent laboratory as unnamed where identity is not defensible.

Planned pond expansion remains planned work, not an awarded package.

Boundary:

```text
planned work != awarded work
named operator != inferred procurement owner
researching != confirmed demand
```

### ✅ Cross-Repo Territorial Handoff v0.1

Adds the Andes side of the bounded three-repository workflow.

Contract 1 intake:

```text
Question Radar
  ↓
question-research-handoff/v0.1
  ↓
TERRITORIAL_RESEARCH
  ↓
Andes Context OS
```

The parser validates the artifact independently. Only `DO_NOW` or `RESEARCH` upstream decisions are accepted.

A valid handoff produces a `ResearchIntentPreview`, not an automatic investigation. Domain, activity, goal and territorial scope remain explicit operator inputs.

Contract 2 export:

```text
OpportunityHypothesis
  ↓
research-opportunity-handoff/v0.1
  ↓
ACTOR_NEED_HYPOTHESIS
  ↓
Opportunity OS
```

Boundary:

```text
question != problem
actor != problem owner
problem owner != buyer
opportunity hypothesis != confirmed demand
handoff != evidence
current_at_export != current_now
```

No shared database, cross-repo Python dependency, auto-routing or external action is introduced.

---

## Current system shape

```text
Question Radar
    │
    │ operator-authorized TERRITORIAL_RESEARCH
    ▼
Andes Context OS
    │
    ├── explicit ResearchIntent
    ├── explicit TerritorialScope
    ├── registered sources / runtime observations
    ├── authorized internal context
    ├── EvidenceCandidate
    ├── Movement / actor roles
    ├── OpportunityHypothesis
    └── missing / contradictory context
    │
    │ optional ACTOR_NEED_HYPOTHESIS
    ▼
Opportunity OS
```

The workflow is intentionally asymmetric:

- Question Radar decides whether a question deserves bounded research;
- Andes Context OS determines what territorial context/evidence/hypothesis can actually be defended;
- Opportunity OS decides whether any downstream candidate deserves a next step.

A pipeline that ends without an opportunity is valid.

---

## Current dogfood

### Argentina lithium

The lithium corpus is used to test evidence discipline around project movement and supplier-entry hypotheses.

Current research lessons include:

- a project expansion is not automatically an open package;
- incumbent supplier ecosystems matter;
- named contractors/operators constrain interpretation but do not prove unrelated procurement;
- actor roles should be movement-scoped rather than converted into a generic relationship graph;
- new evidence should narrow missing context before it increases confidence.

The research loop should continue only when a new source can change a concrete hypothesis or missing-context question.

### San Juan water decision support

The sanitized handoff case tests a different domain:

> What recurring water-related decision in San Juan could improve with territorial or satellite evidence, who makes it today, and what information is missing?

The Andes-side input explicitly uses:

```text
domain   = water
activity = decision_support
```

The territorial scope is supplied separately.

The current sanitized output intentionally contains no defensible actor refs or evidence refs. That preserves an important outcome:

```text
NO_ACTIONABLE_CANDIDATE != failed research
```

The next meaningful research step is not “find a customer”. It is to establish, with evidence:

- which recurrent decision actually changes;
- who holds decision authority;
- what lead time matters;
- what territorial/satellite signal could alter the decision;
- who validates that signal;
- what evidence is missing;
- and what action/no-action consequence follows.

---

## Near-term direction

These are research directions, not release promises.

### 1. Exercise `decision_support` with real bounded cases

Use additional sanitized environmental / water / territorial cases where a recurring decision can be named explicitly.

A useful case should answer more than “monitor X”. It should identify:

```text
observation
  ↓
decision
  ↓
authority
  ↓
lead time
  ↓
evidence threshold
  ↓
action / no-action
```

### 2. Improve source adapters only when a research case needs them

Do not add generic crawling or connector breadth for its own sake.

A source adapter should enter only when:

- the source is authoritative/relevant enough to change a real research question;
- rights/access can be represented safely;
- runtime observation can remain distinct from registration metadata;
- failure and freshness can be recorded explicitly.

### 3. Keep hypothesis state evidence-driven

Future work should strengthen the transition criteria among:

```text
proposed
researching
supported
contradicted / discarded where applicable
```

without replacing review with a magic opportunity score.

### 4. Keep cross-repo handoffs boring and strict

New routes should be added only when a real downstream workflow requires them.

The handoff layer should remain:

- versioned;
- deterministic;
- independently validated;
- fail-closed;
- non-orchestrating;
- explicit about `AS_OF_EXPORT` freshness.

### 5. Keep documentation aligned with merged behavior

README should describe the current product boundary.

This roadmap should carry milestone history, dogfood lessons and future research criteria.

Detailed specs and execution plans remain under `docs/superpowers/`.

---

## Later, only with evidence

Potential future directions include:

- additional environmental baseline / decision-support dogfood;
- richer source-runtime adapters;
- explicit contradiction/supersession workflows for hypotheses;
- stronger evidence-independence review;
- deterministic reports over research runs;
- additional bounded handoff candidate kinds if a real workflow needs them;
- better operator ergonomics for reviewing missing context and evidence lineage.

None should enter merely because the architecture can support it.

---

## Out of scope by design

Andes Context OS is not trying to become:

- a general web crawler;
- an autonomous OSINT agent;
- a GIS platform UI;
- a route-safety authority;
- a procurement/tender inference engine;
- a customer detector;
- a relationship CRM;
- an outreach/contact-discovery system;
- an LLM truth judge;
- a universal confidence/risk score;
- a shared database or agent bus for Question Radar and Opportunity OS.

The invariant remains:

> **Territorial research may narrow uncertainty and produce a defensible hypothesis. It must not silently convert that hypothesis into evidence, demand or permission to act.**
