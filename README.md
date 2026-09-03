# Andes Context OS

> **Territorial research without collapsing source, evidence, context and authorization into the same thing.**

Andes Context OS is a small, deterministic research core for mining and Andean operations. It turns a question and an explicit territorial scope into reproducible context: **which sources are registered, what was actually observed, what is still only an evidence candidate, what is missing or contradictory, and which internal references were explicitly authorized for use**.

It is deliberately conservative. The system does not turn proximity into impact, public information into verified fact, or prior internal knowledge into current operational authorization.

---

## The problem it is designed for

A territorial research task often starts with a deceptively simple question:

> **What do we know about this project, corridor or segment — and how strong is that knowledge?**

The dangerous shortcut is to merge everything into one bucket: source metadata, live observations, internal notes, candidate evidence, old decisions and operational claims.

Andes Context OS keeps those layers separate.

```text
Question
   ↓
Where exactly?
   ↓
Which sources are registered?
   ↓
What did those sources actually return?
   ↓
What can become an evidence candidate?
   ↓
What is missing / contradictory / restricted?
   ↓
Reproducible research snapshot
```

---

## Two explicit context paths

### 1. Public research core

```text
question
  ↓
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

This path distinguishes a **registered source** from what happened when that source was actually checked.

A source can be known but unavailable. An observation can be partial. A candidate can require review. Missing context stays missing.

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

The public core ships no GitHub client, vault client, LLM summarizer, embedding search or crawler.

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
research action != authorization
```

These are not documentation disclaimers added after the fact; they shape the contracts themselves.

Operational fields such as `safe_to_travel`, `road_open`, `route_authorized` and `community_approved` are rejected by strict parsing rather than accepted as generic metadata.

---

## What it does today

| Capability | Purpose |
| --- | --- |
| **Research intent** | preserves the original question, canonical question, domain, activity and constraints |
| **Territorial scope** | makes country, admin area, project, corridor, segment, bbox and geometry scope explicit |
| **Source registry** | records authority, access, coverage, rights, limitations and adapter identity without claiming liveness |
| **Runtime observations** | records what actually happened when a source was checked |
| **Evidence candidates** | keeps provenance, territorial relation, time context, corroboration and review state explicit |
| **Evidence quality vector** | describes evidence across multiple dimensions without collapsing them into a confidence/truth/risk score |
| **Discovery runs** | freezes lineage, observations, contradictions, missing context, warnings and research action into a reproducible run |
| **Internal context adapter** | selects curated internal references deterministically using exact categorical and territorial matches |
| **Authorized context producer** | resolves only explicitly authorized private references and emits source receipts without leaking raw source content |

The current implementation includes the V0.2 internal-context boundary and the V0.3 authorized-context producer on top of the original discovery contracts.

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

V0.4 adds a small interpretation layer above evidence for one controlled benchmark: three Argentine lithium assets seeded from exact Atlas Geotech baseline references.

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

The benchmark currently covers Río Grande / NOA Lithium, Hombre Muerto Oeste and Cauchari-Olaroz. It tests whether meaningful project changes can be represented reproducibly without turning a public signal into verified demand.

The boundary remains strict:

```text
baseline record != current state
movement != opportunity
opportunity hypothesis != confirmed demand
actor participation != durable relationship
```

V0.4 **does not add live scraping**, a relationship graph, contact discovery, outreach, a database, a UI, scoring, agents or MCP. The checked-in hypotheses remain research prompts with explicit assumptions and missing context, not proof of procurement intent or willingness to pay.

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

That is intentional: **relevance can be reviewed later; scope identity should not be guessed.**

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

There is deliberately no function that sums those dimensions into a single confidence, truth or operational-risk value.

Two corroboration references can be recorded without pretending that their independence has automatically been proven.

---

## Determinism and provenance

Reproducibility is part of the contract.

- source registries use deterministic canonical hashing;
- discovery runs freeze registry identity, adapter versions, observations and lineage;
- internal-context snapshots are content-addressed;
- duplicate match reasons and duplicate context IDs are rejected;
- authorized producer receipts use SHA-256 source identity;
- content-hash or source-identity mismatches fail closed;
- resolver failures are sanitized so private locators, source content and exception text are not leaked.

A partial research run can still be valid when optional sources fail, as long as the missing context remains explicit.

---

## Source registry

The seed registry currently contains 12 declarative source references spanning Argentine and Andean public sources, global terrain/OSM context, research references and a public human-signal source.

Examples include:

- SEGEMAR / SIGAM;
- SIACAM;
- San Juan mining cadastre;
- DNV routes;
- IGN administrative context;
- OpenStreetMap;
- SERNAGEOMIN;
- INGEMMET / GEOCATMIN;
- Copernicus DEM;
- AutoMine and AMPilot as research references;
- Reddit as a public human-signal source only.

Registration is metadata, not a liveness claim. Unknown reuse terms remain `unknown_review_required` instead of being guessed open.

---

## What it deliberately does not do

Andes Context OS is not a live territorial intelligence platform by itself.

It does not currently:

- crawl the web, GitHub or a private vault;
- scrape Reddit;
- recursively discover neighboring documents;
- summarize private source content with an LLM;
- use embeddings or fuzzy matching;
- infer route safety or transitability;
- promote evidence automatically;
- produce global confidence, risk or truth scores;
- run a database, public API or UI;
- authorize travel, access, outreach or operations.

Those capabilities can be implemented around the contracts later without weakening the evidence boundaries established here.

---

## Quick start

Requires **Python 3.11+**.

```bash
python -m pip install -e ".[dev]"
pytest -q
```

Runtime dependencies are intentionally **empty**. The development dependency is `pytest>=8,<9`.

Load the seed registry and inspect its deterministic identity:

```python
from andes_context_os.registry import SourceRegistry

registry = SourceRegistry.load("data/source_registry.v0.1.json")
print(registry.registry_hash)
```

---

## Verification

The public repository verifies the same dependency-light Python core used by the contracts.

Recent merged work progressed through TDD and fresh CI, including the V0.3 authorized-context producer with deterministic success/failure behavior, privacy guards and exact source-receipt checks.

The important acceptance criterion is not simply that a resolver can return content. It is that **only the exact authorized source can produce the expected context record and receipt**.

---

## Design documentation

Deep implementation and design detail lives outside the landing page:

- `docs/superpowers/specs/2026-08-30-andes-context-os-v0.2-internal-context-adapter-design.md`
- `docs/superpowers/plans/2026-08-30-andes-context-os-v0.2-internal-context-adapter.md`
- V0.3 authorized-context producer design / implementation records under `docs/superpowers/`

The README focuses on the product boundary; the specs preserve the contract-level detail.

---

## License

MIT License.
