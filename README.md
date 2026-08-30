# Andes Context OS

**A small territorial discovery engine for mining and Andean operations.**

V0.1 does not search the web or decide whether a road is safe. It defines strict, versioned contracts that keep questions, territory, source metadata, runtime source state, evidence quality, rights, limitations, and discovery-run lineage separate and auditable.

## Contract flow

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

The design intentionally preserves distinctions that are easy to collapse in research and geospatial systems:

```text
registered source != live source
public signal != verified fact
proximity != impact
downloadable != reusable
candidate != operational evidence
research action != authorization
```

## What V0.1 includes

- `ResearchIntent` for preserving the original question, canonical question, domain, activity, constraints, and creation time.
- `TerritorialScope` for explicit countries, administrative units, projects, corridors, segments, bounding boxes, geometry references, precision, and relation basis.
- `SourceRecord` for declarative source identity, authority, access, coverage, rights, limitations, and adapter binding.
- `SourceRuntimeObservation` for what actually happened when a source was checked: `available`, `empty`, `partial`, `unavailable`, `omitted`, `unsupported`, or `unknown`.
- `EvidenceQualityVector` for multidimensional evidence description without a synthetic confidence, risk, or truth score.
- `EvidenceCandidate` as a minimal research projection with provenance, temporal context, territorial relation, corroboration references, and review state.
- `SourceRegistry` with deterministic canonical hashing and a conservative V0.1 seed registry.
- `DiscoveryRun` with immutable lineage, registry compatibility checks, adapter versions, observations, missing context, contradictions, warnings, omitted sources, recommended research action, and reproducible run hashing.

## Source Registry

The seed registry currently contains 12 declarative source references:

```text
ar_segemar_sigam
ar_siacam
ar_sanjuan_mining_cadastre
ar_dnv_routes
ar_ign_admin
osm_global
cl_sernageomin
pe_ingemmet_geocatmin
eu_copernicus_dem
research_automine
research_ampilot
reddit_public
```

Registration is metadata, not a liveness claim. Except where rights are explicitly known in the seed, unresolved reuse terms remain `unknown_review_required` rather than being guessed open.

OpenStreetMap is represented as ODbL with attribution and conditional redistribution obligations. AutoMine and AMPilot are reference-only entries. Reddit is represented only as a public human-signal source; public visibility does not imply bulk reuse permission or verified operational truth.

## Quick start

Requires Python 3.11+.

```bash
python -m pip install -e ".[dev]"
pytest -q
```

Load the seed registry and inspect its deterministic hash:

```python
from andes_context_os.registry import SourceRegistry

registry = SourceRegistry.load("data/source_registry.v0.1.json")
print(registry.registry_hash)
```

The registry hash excludes `generated_at` and canonicalizes sources by `source_id`, so array ordering does not change registry identity while meaningful metadata changes do.

## Evidence semantics

`EvidenceQualityVector` keeps quality dimensions separate:

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

There is deliberately no function that sums these dimensions into a single score.

`multiple_independent_sources` requires at least two distinct corroboration references. Distinct references alone do not prove true independence; independence remains a source-lineage and review judgment.

## Discovery runs

A `DiscoveryRun` freezes a reproducible research execution:

```text
intent + territory
+ registry version/hash
+ adapter versions
+ runtime observations
+ candidate refs
+ contradictions
+ missing context
+ warnings
+ omitted sources
+ action + reason
+ lineage
```

Valid run states are `complete`, `partial`, and `failed`. A partial run can be valid when optional sources are unavailable, as long as the missing context is explicit.

Recommended actions are research actions only: `watch`, `research`, `validate`, `build_spike`, or `discard`.

Operational authorization fields such as `safe_to_travel`, `road_open`, `route_authorized`, and `community_approved` are rejected by strict parsing.

## What V0.1 does not do

V0.1 intentionally does **not** include:

- live web or dataset ingestion;
- Reddit scraping;
- scheduled source health checks;
- a database, API, CLI, or UI;
- GeoPlatform or FleetFlow integration;
- transitability or route-safety decisions;
- automatic evidence promotion;
- synthetic confidence or risk scoring.

Those capabilities can be added later through adapters without weakening the contract boundaries established here.

## Development

Runtime dependencies: **none**.

Development dependency:

```text
pytest>=8,<9
```

Run the full test suite:

```bash
pytest -q
```

GitHub Actions runs the same suite on pushes and pull requests with Python 3.11.

## License

MIT License.
