# Cross-repo territorial handoff v0.1

Andes Context OS can consume a versioned JSON artifact produced by Question Radar without importing Question Radar as a Python dependency.

## Contract 1 intake

Accepted contract:

```text
question-research-handoff/v0.1
```

Andes accepts only:

```text
routing.kind        = TERRITORIAL_RESEARCH
routing.destination = andes-context-os
investigation       = DO_NOW | RESEARCH
```

The handoff is treated as `AS_OF_EXPORT`: it describes the source state when the artifact was exported. Andes does not pretend that the source decision is live or current forever.

The parser validates the contract independently and fails closed on unknown fields, unsupported routes, malformed fingerprints, non-actionable decisions, and naive timestamps.

## Research intent preview

A valid handoff still does not contain enough authority to start territorial research automatically.

The operator explicitly supplies:

- `ResearchDomain`;
- `ResearchActivity`;
- `goal`;
- optional `territory_hint`.

The preview preserves the upstream question, decision references, fingerprint, constraints, and freshness. It sets `territorial_scope_required = true` but does not manufacture a `TerritorialScope`.

`decision_support` is an additive `ResearchActivity` for research whose purpose is to assemble evidence for a recurring decision without mislabeling the work as field operations, route planning, or procurement.

## Contract 2 export

Andes can export an existing `OpportunityHypothesis` as:

```text
research-opportunity-handoff/v0.1
candidate.kind = ACTOR_NEED_HYPOTHESIS
```

The export preserves exactly:

- need category;
- statement;
- actor refs;
- supporting evidence refs;
- assumptions;
- missing context;
- source research status.

It does not dereference trigger movements to invent extra evidence and does not promote `researching` to `supported`.

No Contract 2 actor-need payload asserts a buyer, willingness to pay, hiring intent, procurement intent, or contact permission.

## Operational boundary

```text
question != problem
actor != problem owner
problem owner != buyer
opportunity hypothesis != confirmed demand
handoff != evidence
current_at_export != current_now
```

The handoff layer is a traceable boundary between systems. It is not an orchestrator, event bus, shared database, cross-repo runtime dependency, or automatic action engine.
