# San Juan Water Decision-Support Handoff — Sanitized Dogfood

Date: 2026-09-04

## Purpose

Exercise the territorial cross-repo path without turning research into customer discovery by default.

The upstream Question Radar artifact asks:

> ¿Qué decisión recurrente relacionada con agua en San Juan podría mejorar utilizando evidencia territorial o satelital, quién toma hoy esa decisión y qué información le falta?

Question Radar routes the question to Andes Context OS as `RESEARCH`. The route authorizes bounded research only; it does not establish a problem owner, buyer, demand, evidence, or permission to contact anyone.

## Explicit Andes semantics

The intake dogfood supplies these values explicitly:

```text
domain   = water
activity = decision_support
goal     = identify a recurring water decision and document what territorial evidence is missing
```

None of those values are inferred from the question text by the runtime.

A territorial scope is also separate. The test constructs an explicit San Juan administrative scope before treating the work as territorially bounded. A text hint such as `San Juan, Argentina` is not itself a `TerritorialScope`.

## Sanitized research output

The fixed Contract 2 fixture contains one `ACTOR_NEED_HYPOTHESIS` in state `researching`, but deliberately keeps:

```text
actor_refs    = []
evidence_refs = []
```

This is intentional. The fixture demonstrates that a useful research state can exist before a defensible actor or supporting evidence has been established.

The hypothesis remains non-actionable for actor-oriented work. No customer, buyer, problem owner, procurement package, willingness to pay, or contact permission is asserted.

## Boundaries preserved

```text
question != problem
actor != problem owner
problem owner != buyer
evidence candidate != operational evidence
opportunity hypothesis != confirmed demand
route != opportunity
handoff != evidence
current_at_export != current_now
NO_ACTIONABLE_CANDIDATE != failed research
```

The last distinction is especially important: research may validly conclude that there is not yet an actionable candidate. The system must preserve that result rather than manufacture one to complete a pipeline.

## Fixtures

- `tests/fixtures/handoffs/question_research_water_san_juan_v01.json`
- `tests/fixtures/handoffs/research_opportunity_water_san_juan_v01.json`

Executable regression:

- `tests/test_cross_repo_water_dogfood.py`

All identifiers are sanitized or synthetic. The fixtures are contract/regression artifacts, not claims about a real provincial agency, buyer, customer, or procurement process.
