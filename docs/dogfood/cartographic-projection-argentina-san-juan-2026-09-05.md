# Cartographic projection dogfood — Argentina / San Juan

Status: research seed only. This file does not establish operational evidence, actor need, buyer intent, or outreach authority.

## Canonical question

What errors of area, scale and visual perception are introduced when Web Mercator is used for territorial maps of Argentina and San Juan, and which projection/CRS is appropriate for each objective: web visualization, spatial analysis, area measurement, or public communication?

## Question Radar handoff intent

- decision: `RESEARCH`
- route: `TERRITORIAL_RESEARCH`
- destination: `andes-context-os`
- domain: `territorial_cartography`
- activity: `decision_support`
- goal: separate geometric evidence from visualization choices and political/social interpretation

## Explicit territorial scope

This seed is intentionally territorialized before entering Andes Context OS.

- country: `country:AR`
- admin area: `admin:AR:1:J`
- territory label: San Juan, Argentina

A text mention of San Juan is not treated as a structured territorial identity by itself.

## Research questions

1. For the same trusted geometry, how do reported polygon areas differ across Web Mercator, an equal-area world projection, and an appropriate local projected CRS?
2. Which distortions are geometric properties of the projection and which are only visual/perceptual effects?
3. Which CRS/projection is appropriate for:
   - interactive web display;
   - area measurement;
   - distance measurement;
   - regional comparison;
   - public communication?
4. What limitations remain when a world equal-area projection such as Equal Earth is used for local analytical work in San Juan?

## Evidence boundary

The research must keep these layers separate:

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

## Minimal reproducible test

Use one authoritative polygon dataset for Argentina and one authoritative polygon for San Juan. Preserve the source geometry identity and transform copies into explicitly named CRSs.

At minimum compare:

- geographic/source geometry used as the common input;
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

## Expected research outcome

The expected result is not a winner-takes-all projection ranking. The useful output is a task-oriented matrix such as:

| Task | Projection / CRS class | Evidence needed | Expected limitation |
| --- | --- | --- | --- |
| Web basemap visualization | Web Mercator | rendering compatibility | area distortion grows with latitude |
| Global area comparison | equal-area world projection | preserved-area property | shape/distance distortion remains |
| Local area/distance analysis | appropriate projected local/regional CRS | authoritative CRS definition + metric validation | bounded geographic applicability |
| Public communication | projection chosen explicitly for message | stated communication objective + distortion disclosure | visual choices can affect perception |

## Opportunity boundary

This seed does **not** justify an Opportunity OS handoff yet.

A downstream handoff should occur only if research establishes a defensible `ACTOR_NEED_HYPOTHESIS` with explicit actor references, supporting evidence references, assumptions, missing context, and research status.

Until then the valid outcome is:

```text
Question Radar: RESEARCH
Andes Context OS: territorial research
Opportunity OS: NO HANDOFF YET
```

## Success criterion

This dogfood succeeds if it can answer, with provenance, **which representation is fit for which territorial decision and why**, while keeping geometric measurement, visualization, interpretation and opportunity hypotheses separate.

`NO_ACTIONABLE_CANDIDATE` remains a valid downstream result.
