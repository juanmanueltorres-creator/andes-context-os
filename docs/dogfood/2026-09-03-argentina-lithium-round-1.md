# Argentina lithium dogfood — round 1

Date: 2026-09-03

Mode: manual public-source dogfood

Scope: three Atlas Geotech assets already seeded in V0.4.

- Río Grande / NOA Lithium — `project_id:258`
- Hombre Muerto Oeste — `project_id:137`
- Cauchari-Olaroz — `project_id:52`

## Research question

Can the current Andes Context OS contracts help reconstruct how actors move around a mineral asset as the asset changes stage, without turning public signals into facts or opportunity hypotheses into confirmed demand?

This round deliberately does **not** change the schema. Where the current contracts feel incomplete, the gap is recorded as a dogfood finding.

## Baseline

Atlas Geotech remains the immutable identity/baseline provider for this exercise. Mutable project state is researched separately.

| Asset | Atlas stage | Coordinates |
| --- | --- | --- |
| Río Grande / NOA Lithium | Evaluación Económica Preliminar | -24.978, -68.154 |
| Hombre Muerto Oeste | Construcción | -25.4099951, -67.2450136 |
| Cauchari-Olaroz | Producción | -23.41623, -66.71316 |

## 1. Río Grande / NOA Lithium

### Observed movements

#### 2026 drilling program advanced from mobilization into active drilling/testing

NOA reported on 2026-07-16 that both rigs were operating according to plan. RT-RG26-PW001 had reached 254 m and RT-RG26-PW002 had reached a planned exploratory depth of 504 m. BMR logging had been completed at PW002 and a production well had been designed.

Evidence:
- https://www.noalithium.com/_resources/news/nr-20260716.pdf

Actors directly supported by public evidence:
- NOA Lithium Brines Inc. — operator
- Hidrotec S.A. — drilling contractor; named in the earlier campaign mobilization/collaboration disclosures

#### Hidrotec relationship expanded beyond a single drilling job

On 2026-05-12 NOA announced a strategic collaboration framework with Hidrotec. The disclosure describes Hidrotec as the contractor supporting the first two rotary wells and says the framework may extend to other planned work programs in Argentina.

Evidence:
- https://www.noalithium.com/_resources/news/nr-20260512.pdf

Actor movement:
- Hidrotec changes from `contractor on one movement` to a recurring execution actor around NOA's project portfolio.

Important boundary:
- this does not prove future awards, volumes, revenue or exclusivity.

#### Hatch became a process-development and engineering actor around the PFS pathway

On 2026-06-16 NOA and Hatch announced a strategic arrangement tied to the Pre-PFS Process Development Study. Hatch agreed to take shares for approximately USD 100,000 of study services. The work compares the baseline evaporation-pond flowsheet with alternatives incorporating DLE testwork and concept-level process design.

Evidence:
- https://www.noalithium.com/_resources/news/nr-20260616.pdf

Actor:
- Hatch Ltd. — consultant / process-development partner

#### Additional external technical actors are visible before PFS

The May drilling disclosure states that Montgomery & Associates reviewed the drill program, was preparing the project water balance and would participate in the PFS.

The 2026-05-08 corporate update also names Tricone Inc. under a nine-month consulting agreement for exploration, drilling, geology and hydrogeology services, with a total stated fee of USD 700,000 paid through shares as services are completed.

Evidence:
- https://www.noalithium.com/_resources/news/nr-20260521.pdf
- https://www.noalithium.com/_resources/news/nr-20260508.pdf

Actors:
- Montgomery & Associates — consultant / hydrogeology / PFS
- Tricone Inc. — consultant / exploration / geology / hydrogeology

### Opportunity hypothesis

**Hypothesis:** as Río Grande advances from PEA toward PFS, execution is becoming more externally distributed across drilling, hydrogeology, process engineering and specialist consulting.

Status: `supported as a pattern`, not confirmed open procurement.

Support:
- Hidrotec is explicitly contracted/collaborating on drilling.
- Hatch is explicitly engaged for process-development work.
- Montgomery & Associates is explicitly involved in water balance/PFS work.
- Tricone is explicitly engaged for exploration/geology/hydrogeology consulting.

What is still unknown:
- which additional packages remain unawarded;
- whether laboratory/assay work is internal or external;
- procurement channel and supplier-registration process;
- timing and scope of any future PFS engineering packages;
- whether services are project-specific or portfolio-wide.

## 2. Hombre Muerto Oeste

### Observed movements

#### Atlas baseline is now materially stale as an operational state

Atlas records HMW as `Construcción`. Public company reporting in the June 2026 quarter says wet commissioning was completed, first processed lithium chloride was produced and the operation entered ramp-up toward stabilized production at 4 ktpa LCE.

Evidence:
- https://markets.financialcontent.com/wral/article/accwirecq-2026-7-31-quarterly-activities-report-june-2026
- https://galanlithium.com.au/

This is exactly the desired baseline-vs-movement pattern:

`Construcción (snapshot) -> commissioning -> first processed product -> ramp-up`

#### Authium is a multi-role actor, not merely a vendor

Authium's own public news page states that definitive agreements with Galan include an Offtake Agreement and an Operating Agreement and that Authium will fund, supply and operate the processing plant at HMW.

Evidence:
- https://authium.com.au/news/

Roles around the asset:
- technology supplier
- operating partner
- offtaker

Dogfood finding:
- actor roles belong to a movement/relationship context, not permanently to actor identity. V0.4 already made the right design choice here.

#### Independent laboratory validation is visible, but the laboratory is not named

Galan's June-quarter reporting says chemical assays on processed lithium chloride were performed by an independent laboratory and validated impurity-separation performance against design specifications.

Evidence:
- https://markets.financialcontent.com/wral/article/accwirecq-2026-7-31-quarterly-activities-report-june-2026

This is a useful negative-space signal:
- a real service need existed (`independent laboratory assays`),
- but the public evidence does not identify the provider.

**Do not invent the actor.**

Missing context:
- laboratory identity;
- analytical method/package;
- sample chain of custody;
- frequency of ongoing QA/QC testing;
- whether future commercial-production assays are under the same provider.

#### Near-term expansion creates another movement window

Galan's June-quarter update says pond construction for Phase 1 expansion from 4.0 to 5.2 ktpa LCE is planned to commence in the September 2026 quarter, targeting the capacity uplift in H1 2027.

Evidence:
- https://markets.financialcontent.com/wral/article/accwirecq-2026-7-31-quarterly-activities-report-june-2026

Opportunity hypothesis:
- expansion may create new construction/civil/logistics packages, but no provider or open procurement is confirmed by this source.

Status: `proposed`.

## 3. Cauchari-Olaroz

### Observed movements

#### Stage 2 moved from planning/RIGI application into approved early development

Lithium Argentina's 2026 Q2 results state that Stage 2 received RIGI approval in May 2026 and that early development activities had been approved, including additional production wells, infrastructure and site preparation. The environmental approval process remains underway.

Evidence:
- https://investors.lithium-argentina.com/news-releases/news-release-details/lithium-argentina-reports-second-quarter-2026-results

Actors directly supported:
- Minera Exar — operating entity
- Lithium Argentina — partner / owner
- Ganfeng Lithium — partner / owner and process-equipment expertise
- JEMSE — provincial state partner / owner

#### Capital actor layer expanded

On 2026-08-05 Lithium Argentina reported USD 220 million of new unsecured debt facilities at Cauchari-Olaroz, including a USD 170 million facility with a syndicate of international banks.

Evidence:
- https://investors.lithium-argentina.com/news-releases/news-release-details/lithium-argentina-announces-220-million-new-debt-facilities

The individual international banks are not named in the public release used in this round.

Missing context:
- bank identities;
- exact Stage 2 allocation vs general operating-asset flexibility;
- financing covenants relevant to procurement/execution.

#### Jujuy government explicitly introduced a local-supplier priority signal

On 2026-08-25 the Government of Jujuy reported a meeting with EXAR and project stakeholders about Phase 2. The provincial statement says the new phase will prioritize Jujuy labor and work with local companies and suppliers.

Evidence:
- https://prensa.jujuy.gob.ar/jujuy/jujuy-consolida-su-liderazgo-la-produccion-litio-y-proyecta-una-nueva-etapa-crecimiento-n124968

Named actors in that public event include:
- Government of Jujuy / Governor Carlos Sadir
- Ministry of Mining of Jujuy / José Gómez
- JEMSE / Exequiel Lello Ivacevich
- Ganfeng Lithium / Li Liangbin
- Lithium Argentina / Sam Pigott
- EXAR representatives

### Opportunity hypothesis

**Hypothesis:** Cauchari-Olaroz Stage 2 presents a supported local-supplier participation opportunity, but the categories, procurement process and award timing are still unknown.

Status: `supported` at the general local-supplier-participation level.

Why this is stronger than a generic inference:
1. company evidence confirms Stage 2 early development activities (wells, infrastructure, site preparation);
2. an independent provincial-government source explicitly says Phase 2 will prioritize local companies and suppliers.

What this still does **not** support:
- a specific open tender;
- demand for a specific service category;
- a specific contract value;
- permission to contact named people;
- any claim that a supplier will be selected.

Next research questions:
- Is there an EXAR/JEMSE supplier-registration portal or procurement channel?
- Which Stage 2 packages are already awarded vs not yet awarded?
- Which local supplier categories are being prioritized?
- Is Ganfeng procuring modular DLE/process equipment directly, while EXAR procures site/civil/wellfield packages locally?
- What is the current EIA approval status and what execution activities can proceed under existing permits?

## Cross-asset actor movement

The first real run already shows several recurring actor classes around projects as they mature:

| Project transition | Actor types observed |
| --- | --- |
| PEA -> PFS | drilling contractor, hydrogeology consultant, process engineering consultant, technical consultant, regulator |
| construction -> ramp-up | technology/operating partner, offtaker, independent laboratory, government/community actors |
| production -> expansion | owners/JV partners, state partner, financiers, regulator, local suppliers, engineering/process actors |

This is an observation from three cases, **not a universal lifecycle model**.

## Community / Reddit pass

A first Reddit pass produced broad discussion about Argentine lithium, water, financing and macro industry development, but no sufficiently specific, current, asset-level operational signal for Río Grande, HMW or Cauchari-Olaroz that should be promoted into these asset records.

Result: **no Reddit item promoted in round 1**.

This is a useful outcome. Community sources remain a problem/signal radar, not a requirement to force a signal into every research run.

## Dogfood findings about the V0.4 model

### What worked

1. `Asset` as immutable baseline identity worked well.
2. `Movement` successfully separates mutable project change from the Atlas snapshot.
3. movement-scoped actor roles are necessary: Authium alone demonstrates `partner + supplier/operator + offtaker`.
4. `OpportunityHypothesis` is useful precisely because many apparent opportunities remain unconfirmed procurement.
5. `missing_context` is not cosmetic: the unnamed independent laboratory at HMW is a real example where the need is visible but the actor is not.
6. the rule `supported opportunity requires evidence beyond trigger evidence` becomes valuable at Cauchari-Olaroz, where company activity plus provincial supplier policy support a stronger hypothesis.

### Friction / possible future schema needs — do not implement yet

1. **Validation/testwork movement type**: HMW laboratory validation currently fits only `OTHER` if represented as a movement. Wait for repetition before adding a type.
2. **Unknown actor placeholder**: an unnamed independent laboratory is relevant, but creating a fake `Actor` would violate evidence discipline. Current `missing_context` may be enough.
3. **Relationship query**: recurring actors such as Hidrotec and Hatch make future questions like "where else has this actor appeared?" likely. Do not add a relationship graph until repeated dogfood requires it.
4. **Opportunity scope**: `supported` can mean the general market condition is supported while a specific procurement remains unknown. Future UI/reporting may need to make this distinction very explicit.
5. **Source/event time**: multiple disclosures can refer to the same underlying movement. Deduplication rules will matter once ingestion becomes automated.

## Highest-value next move

Do **not** add another feature yet.

Run a second research pass focused on one question generated by round 1:

> **Cauchari-Olaroz Stage 2: which supplier categories, procurement channels and already-visible contractors can be verified from public evidence?**

Why this one:
- there is a current project movement;
- there is explicit local-supplier language;
- the question is commercial but still evidence-bounded;
- it tests whether Andes can move from `asset movement` to `supplier opportunity research` without inventing demand.
