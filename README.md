# Andes Context OS

> **Territorial research without collapsing source, evidence, context, hypothesis and authorization into the same thing.**

Andes Context OS is a small, deterministic research core for answering a deceptively simple question:

> **What do we actually know about this territory, project, corridor or operational question — and what is still missing?**

It turns an explicit research intent and territorial scope into reproducible context while keeping separate:

- registered sources;
- what those sources actually returned;
- evidence candidates;
- authorized internal context;
- interpreted movements and actor roles;
- opportunity hypotheses;
- and the authority required to continue research or hand something to another system.

It is deliberately conservative. **Proximity is not impact. A public signal is not verified fact. An actor is not automatically a problem owner. A hypothesis is not confirmed demand.**

```text
question / research handoff
          ↓
explicit research intent
          ↓
explicit territorial scope
          ↓
registered sources + authorized context
          ↓
what was actually observed?
          ↓
evidence candidates
          ↓
what movement / actor role can be defended?
          ↓
what hypothesis remains?
          ↓
missing / contradictory context stays visible
          ↓
optional bounded handoff to Opportunity OS
```

**Current product line:** discovery contracts + V0.2 Internal Context Adapter + V0.3 Authorized Context Producer + V0.4 research-loop dogfood + Cross-Repo Territorial Handoff v0.1
**Stack:** Python 3.11+ · standard-library runtime · deterministic JSON/file contracts · runtime dependencies `[]`

The milestone history and current research direction live in [`ROADMAP.md`](ROADMAP.md).

---

## The problem it is designed for

Territorial research often fails by mixing several kinds of knowledge into one bucket:

```text
source exists
        ≈
source is live
        ≈
source says something
        ≈
that thing is evidence
        ≈
we know what it means
        ≈
an actor needs something
        ≈
there is an opportunity
```

Andes Context OS rejects that collapse.

A source can be registered but unavailable. An observation can be partial. An evidence candidate can still require review. An internal note can be relevant without being current evidence. A project movement can be real without creating an external opportunity. A research loop can end with `NO_ACTIONABLE_CANDIDATE` and still be successful.

---

## Boundaries that matter

```text
registered source != live source
public signal != verified fact
proximity != impact
downloadable != reusable
candidate != operational evidence
internal context != operational evidence
known evidence reference != current evidence
known decision != current authorization
baseline record != current state
movement != opportunity
actor != problem owner
problem owner != buyer
opportunity hypothesis != confirmed demand
researching != supported
handoff != evidence
current_at_export != current_now
research action != authorization
NO_ACTIONABLE_CANDIDATE != failed research
```

These are not disclaimer text added after implementation. They shape the contracts and tests.

Operational assertions such as `safe_to_travel`, `road_open`, `route_authorized` and `community_approved` are rejected by strict parsing rather than accepted as generic metadata.

---

## What it does today

| Capability | Purpose |
| --- | --- |
| **Research intent** | preserves the original question, canonical question, domain, activity and constraints |
| **Territorial scope** | makes country, admin area, project, corridor, segment, bbox and geometry scope explicit |
| **Source registry** | records authority, access, coverage, rights, limitations and adapter identity without claiming liveness |
| **Runtime observations** | records what actually happened when a source was checked |
| **Evidence candidates** | keeps provenance, territorial relation, time context, corroboration and review state explicit |
| **Evidence quality vector** | describes evidence across multiple dimensions without collapsing them into a truth/confidence/risk score |
| **Discovery runs** | freezes observations, lineage, contradictions, missing context, warnings and research action into a reproducible run |
| **Internal context adapter** | selects curated internal references deterministically using exact categorical and territorial matches |
| **Authorized context producer** | resolves only explicitly authorized references and emits SHA-256 source receipts without leaking raw source content |
| **Asset / movement research loop** | represents baseline assets, evidence-linked movements, actor roles and conservative opportunity hypotheses |
| **Research handoff intake** | validates Question Radar `TERRITORIAL_RESEARCH` artifacts independently and produces an operator-controlled research preview |
| **Actor-need handoff export** | exports an existing hypothesis as `ACTOR_NEED_HYPOTHESIS` without promoting it to demand, buyer intent or contact permission |

The current implementation includes the original discovery contracts, the V0.2 internal-context boundary, the V0.3 authorized-context producer, V0.4/V0.4.1/V0.4.2 research-loop dogfood, and the Cross-Repo Territorial Handoff v0.1.

---

## Three explicit research paths

### 1. Public research core

```text
ResearchIntent
    ↓
TerritorialScope
    ↓
SourceRegistry
    ↓
SourceRuntimeObservation
    ↓
EvidenceCandidate + EvidenceQualityVector
    ↓
DiscoveryRun
```

This path distinguishes a registered source from what happened when it was actually checked.

A source may fail. A run may be partial. Missing context remains missing.

### 2. Authorized internal context

```text
private allowlist
      ↓
exact authorized reference
      ↓
injected exact resolver
      ↓
source identity + SHA-256 receipt
      ↓
curated InternalContextCatalog
      ↓
deterministic InternalContextSnapshot
```

The allowlist decides what may be read. The resolver does not search neighboring files, crawl repositories, infer related documents or expand its own scope.

### 3. Cross-repo research continuation

```text
Question Radar
    ↓
question-research-handoff/v0.1
    ↓
TERRITORIAL_RESEARCH
    ↓
Andes Context OS
    ↓
explicit domain + activity + goal + TerritorialScope
    ↓
research / evidence / missing context
    ↓
optional OpportunityHypothesis
    ↓
research-opportunity-handoff/v0.1
    ↓
ACTOR_NEED_HYPOTHESIS
    ↓
Opportunity OS read-only preview
```

The repositories remain independent. The integration is a strict versioned JSON boundary, not a shared database, RPC layer, cross-repo import or orchestration service.

---

## Cross-Repo Territorial Handoff v0.1

Andes independently validates the Question Radar producer contract:

```text
contract                = question-research-handoff/v0.1
routing.kind            = TERRITORIAL_RESEARCH
routing.destination     = andes-context-os
investigation           = DO_NOW | RESEARCH
source.system           = question-radar
```

Unknown fields, unsupported routes, malformed fingerprints, naive timestamps and non-actionable decisions fail closed.

### ResearchIntentPreview

A valid upstream handoff is **not enough to start territorial research automatically**.

The operator still supplies explicitly:

- `ResearchDomain`;
- `ResearchActivity`;
- `goal`;
- optional `territory_hint`.

The preview preserves upstream identity, decision fingerprint, constraints and `AS_OF_EXPORT` freshness while setting:

```text
territorial_scope_required = true
```

It does not infer a `TerritorialScope`, actor, source, evidence or opportunity.

`decision_support` is an additive research activity for assembling evidence around a recurring decision without mislabeling the work as field operations, route planning or procurement.

### Actor-need export

An existing `OpportunityHypothesis` can be exported as:

```text
contract        = research-opportunity-handoff/v0.1
candidate.kind  = ACTOR_NEED_HYPOTHESIS
```

The export preserves need category, statement, actor refs, supporting evidence refs, assumptions, missing context and research status.

It does not invent buyer status, procurement intent, hiring intent, willingness to pay or contact permission. It also does not turn `researching` into `supported`.

See [`docs/cross-repo-handoff-v0.1.md`](docs/cross-repo-handoff-v0.1.md).

---

## V0.2 — Internal Context Adapter

V0.2 selects explicitly curated records from a **local deterministic catalog** using exact categorical and territorial matching.

It **does not read GitHub or the private vault**. Repository and vault access remain outside the public core and must be supplied through explicit authorized boundaries.

The contract keeps a strict distinction:

```text
internal context match != evidence validation
```

A matched internal note can provide context for research, but it does not become current operational evidence automatically.

---

## V0.3 — Authorized Context Producer

V0.3 resolves **exact authorized references** through an injected resolver, verifies source identity/content hashes when pinned, and emits curated internal-context records plus source receipts.

It **does not search GitHub or the private vault**. The manifest decides what may be resolved; the resolver never expands its own scope.

The producer preserves another strict boundary: **source content is not copied into the produced catalog**. Source bytes are used only to confirm exact resolution and produce provenance receipts; curated semantic metadata remains explicit.

---

## V0.4 experimental asset-movement dogfood

V0.4 adds a controlled interpretation layer above evidence:

```text
Asset baseline
    ↓
EvidenceCandidate
    ↓
Movement + actor roles
    ↓
OpportunityHypothesis
    ↓
explicit assumptions + missing context
```

The checked-in Argentina lithium dogfood covers Río Grande / NOA Lithium, Hombre Muerto Oeste and Cauchari-Olaroz.

V0.4.1 and V0.4.2 then exercise the research loop with additional evidence and actor detail. Hypotheses may move from `proposed` to `researching`, but not automatically to `supported`.

This is **experimental research dogfood, not validated market intelligence**.

V0.4 **does not add live scraping**, a relationship graph, contact discovery, outreach, a database, a UI, scoring, agents or MCP.

```text
project movement != open procurement
actor participation != durable relationship
planned work != awarded work
movement != opportunity
opportunity hypothesis != confirmed demand
researching != confirmed demand
```

---

## San Juan water decision-support dogfood

The handoff path includes a sanitized question about a recurring water decision in San Juan.

The Andes-side semantics are supplied explicitly:

```text
domain   = water
activity = decision_support
```

The `TerritorialScope` is created separately. A text hint such as `San Juan, Argentina` is not treated as structured territory.

The downstream actor-need fixture deliberately remains:

```text
research_status = researching
actor_refs      = []
evidence_refs   = []
```

That is intentional. The test demonstrates that valid research may exist before a defensible actor or supporting evidence has been established.

See [`benchmarks/dogfood-water-decision-support-handoff-2026-09-04.md`](benchmarks/dogfood-water-decision-support-handoff-2026-09-04.md).

---

## Exact territory instead of fuzzy geography

Territorial references are typed so equal-looking identifiers cannot silently cross boundaries:

```text
country:AR
admin:AR:1:J
project:<ref>
corridor:<ref>
segment:<ref>
geometry:<ref>
```

Territorial-specific internal context requires exact structured reference equality.

There is no bbox proximity inference, fuzzy project-name match, embedding similarity or LLM-based relevance score in the current core.

**Relevance can be reviewed later; scope identity should not be guessed.**

---

## Evidence quality without a magic score

`EvidenceQualityVector` keeps dimensions separate:

```text
authority
source_verification
freshness
spatial_precision
temporal_precision
coverage
completeness
corroboration
method_transparency
rights_clarity
review_state
limitations
missing_context
```

There is deliberately no function that collapses those dimensions into one confidence, truth or operational-risk value.

---

## Determinism and provenance

Reproducibility is part of the contract.

- source registries use deterministic canonical hashing;
- discovery runs freeze registry identity, observations, adapter versions and lineage;
- internal-context snapshots are content-addressed;
- duplicate match reasons and context IDs are rejected;
- authorized producer receipts use SHA-256 source identity;
- identity/content-hash mismatches fail closed;
- resolver failures are sanitized;
- handoff timestamps must be timezone-aware;
- upstream decision fingerprints are validated independently;
- cross-repo exports preserve source research status rather than silently promoting it.

A partial research run can still be valid when optional sources fail, provided the missing context remains explicit.

---

## What it deliberately does not do

Andes Context OS is not a live territorial-intelligence platform by itself.

It does not currently:

- crawl the web, GitHub or a private vault;
- scrape Reddit;
- recursively discover neighboring documents;
- summarize private source content with an LLM;
- use embeddings or fuzzy matching;
- infer route safety or transitability;
- promote evidence or hypotheses automatically;
- produce global confidence, truth or risk scores;
- infer a buyer, customer, tender or job opening;
- discover contacts or send outreach;
- run a shared database, public API, agent bus or UI;
- authorize travel, access, procurement, outreach or operations.

Those capabilities may exist around the contracts later, but they should not weaken the evidence and authority boundaries established here.

---

## Quick start

Requires **Python 3.11+**.

```bash
python -m pip install -e ".[dev]"
pytest -q
python -m compileall -q src
```

Runtime dependencies are intentionally **empty**.

Load the seed registry and inspect its deterministic identity:

```python
from andes_context_os.registry import SourceRegistry

registry = SourceRegistry.load("data/source_registry.v0.1.json")
print(registry.registry_hash)
```

---

## Verification

The repository verifies the dependency-light Python core on pull requests.

The merged territorial handoff release reached **252 passing tests** on Python 3.11 and also verifies source compilation and PR whitespace integrity.

The meaningful acceptance criterion is not simply “did the pipeline produce something?”. It is whether every transformation preserved the distinction between **source, observation, evidence, interpretation, hypothesis and authority**.

---

## Documentation

- [`ROADMAP.md`](ROADMAP.md) — product evolution, current dogfood and research direction;
- [`docs/cross-repo-handoff-v0.1.md`](docs/cross-repo-handoff-v0.1.md) — exact cross-repo intake/export boundary;
- [`docs/dogfood/`](docs/dogfood/) — manual Argentina lithium research passes;
- [`benchmarks/`](benchmarks/) — sanitized executable dogfood;
- [`docs/superpowers/specs/`](docs/superpowers/specs/) — approved contract designs;
- [`docs/superpowers/plans/`](docs/superpowers/plans/) — implementation plans.

## License

MIT License.
