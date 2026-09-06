# Cartographic projection dogfood — Argentina / San Juan

Status: research seed + compatibility-gap dogfood. This file does not establish operational evidence, actor need, buyer intent, or outreach authority.

## Canonical question

What errors of area, scale and visual perception are introduced when Web Mercator is used for territorial maps of Argentina and San Juan, and which projection/CRS is appropriate for each objective: web visualization, spatial analysis, area measurement, or public communication?

## Question Radar handoff

The question is suitable for a bounded upstream handoff:

```text
decision    = RESEARCH
route       = TERRITORIAL_RESEARCH
destination = andes-context-os
```

The handoff does not establish a downstream domain, actor, evidence, demand, or opportunity.

A sanitized executable fixture is kept at:

- `tests/fixtures/handoffs/question_research_cartography_san_juan_v01.json`

## Compatibility gap discovered in Andes

The current `ResearchDomain` contract supports:

```text
mining
geology
logistics
access
water
environment
community
workforce
```

It does **not** currently contain a cartography, geospatial, GIS, or territorial-analysis domain.

Therefore this dogfood must not silently map the question to `geology` or `environment` merely to keep the pipeline moving. Doing so would replace an explicit semantic gap with false precision.

Current downstream state:

```text
Question Radar handoff: VALID RESEARCH CANDIDATE
Andes domain selection: BLOCKED / NOT REPRESENTABLE WITHOUT SEMANTIC LOSS
Andes territorial research execution: NOT STARTED
Opportunity OS handoff: NOT JUSTIFIED
```

This is a valid research outcome. The next design decision is whether a future change should add a broader geospatial/cartography research domain, or whether this question belongs outside Andes unless tied to an existing supported domain.

## Candidate territorial scope

If and only if the domain-model gap is resolved, the intended scope is explicit rather than inferred from prose:

- country: `AR`
- admin level: `1`
- admin unit: `San Juan`
- territory label: San Juan, Argentina
- relation basis: authoritative/official geometry when a source is selected

A text mention of `San Juan, Argentina` is not itself a `TerritorialScope`.

## Intended research questions

1. For the same trusted geometry, how do reported polygon areas differ across Web Mercator, an equal-area world projection, and an appropriate local projected CRS?
2. Which distortions are geometric properties of the projection and which are visual/perceptual effects?
3. Which CRS/projection is appropriate for:
   - interactive web display;
   - area measurement;
   - distance measurement;
   - regional comparison;
   - public communication?
4. What limitations remain when a world equal-area projection such as Equal Earth is used for local analytical work in San Juan?

## Evidence boundary

The future research must keep these layers separate:

```text
source / CRS definition
        ↓
runtime observation / transformation result
        ↓
measured geometric evidence
        ↓
interpretation of suitability for a task
        ↓
optional communication or policy interpretation
```

The following statements are not accepted without direct evidence:

- a projection is politically neutral or politically biased as a geometric fact;
- Equal Earth is universally better than Mercator;
- a visualization CRS is suitable for metric analysis merely because it renders correctly;
- a country or province appears larger/smaller, therefore a specific institutional intent is proven;
- a public institutional recommendation creates a local actor need or commercial opportunity.

## Minimal reproducible research test

Once the semantic intake is representable, use one authoritative polygon dataset for Argentina and one authoritative polygon for San Juan. Preserve source geometry identity and transform copies into explicitly named CRSs.

At minimum compare:

- the geographic/source geometry used as the common input;
- `EPSG:3857` Web Mercator for web visualization;
- Equal Earth or another documented equal-area world projection for global/regional area comparison;
- an appropriate projected CRS for local/regional metric analysis in San Juan, selected explicitly from authoritative CRS metadata rather than guessed.

Record for each transformation:

- CRS identifier and definition source;
- transformation method/library version;
- polygon area result and units;
- representative distance result and units where appropriate;
- visible shape/scale limitations;
- whether the CRS is being used for visualization or analysis;
- missing context and known limitations.

Do not compare numeric areas produced in angular units.

## Expected research output

The expected result is not a winner-takes-all projection ranking. A useful output would be task-oriented:

| Task | Projection / CRS class | Evidence needed | Expected limitation |
| --- | --- | --- | --- |
| Web basemap visualization | Web Mercator | rendering compatibility | area distortion grows with latitude |
| Global area comparison | equal-area world projection | preserved-area property | shape/distance distortion remains |
| Local area/distance analysis | appropriate projected local/regional CRS | authoritative CRS definition + metric validation | bounded geographic applicability |
| Public communication | projection chosen explicitly for message | stated communication objective + distortion disclosure | visual choices can affect perception |

## Opportunity boundary

This seed does **not** justify an Opportunity OS handoff.

A future downstream handoff would require a defensible `ACTOR_NEED_HYPOTHESIS` with explicit actor references, supporting evidence references, assumptions, missing context, and research status.

Until then:

```text
Question Radar: RESEARCH
Andes Context OS: STOP AT DOMAIN GAP
Opportunity OS: NO HANDOFF
```

## Success criterion

This dogfood already succeeds if it exposes that the current domain contract cannot represent the question faithfully. If the gap is later resolved, the research succeeds by answering, with provenance, **which representation is fit for which territorial decision and why**, while keeping geometric measurement, visualization, interpretation and opportunity hypotheses separate.

`NO_ACTIONABLE_CANDIDATE` and `NOT REPRESENTABLE WITHOUT SEMANTIC LOSS` are both valid outcomes when supported by the current contracts.
