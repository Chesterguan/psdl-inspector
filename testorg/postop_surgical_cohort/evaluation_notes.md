# Evaluation Notes: PSDL for Perioperative Cohort Definition

*2026-04-09*

## What PSDL Captures Well

1. **Inclusion/exclusion criteria** - The `population` block expresses age, surgery
   status, and hospitalization clearly. Exclusions (comfort-care, outside ICU transfer)
   map naturally.

2. **Surgical episode phases** - Logic rules distinguish pre-surgical, intra-op, and
   post-surgical states, making the dynamic cohort window explicit.

3. **Post-op surveillance** - Trends + logic provide built-in complication screening
   (AKI, bleeding, perfusion) on top of the cohort definition.

4. **Audit trail** - Intent, rationale, and provenance are first-class citizens,
   which matters for governance.

## What Falls Outside PSDL's Current Scope

PSDL defines **what to detect** (clinical logic), not **where data lives** or
**how to extract it**. Several data elements in the requirements are extraction
concerns, not detection logic:

| Requirement | PSDL Layer | Handling |
|-------------|-----------|----------|
| Labs, vitals, dialysis status | `signals` | Expressed as abstract refs |
| Diagnoses (ICD) | `signals` / `population` | Can be inclusion/exclusion criteria |
| Procedures (ICD + CPT split) | `datasetSpec` | Physical binding, not scenario logic |
| Billing Accounts | `datasetSpec` | ETL extraction concern |
| Provider Info | `datasetSpec` | ETL extraction concern |
| Mortality / SSDI | `signals` | Can be a signal (death_indicator) |
| Height / Weight | `signals` | Expressed as signals |

The **datasetSpec** layer (created by site data analysts) is where physical table
bindings, procedure code splits (ICD vs CPT), billing account joins, and provider
lookups get defined. PSDL intentionally separates this.

## Answer: primary_encounter_id Across Days

**Yes, but it lives in the datasetSpec, not the PSDL scenario.**

The PSDL scenario declares `primary_encounter_id` as an output evidence field -
it says "this value must be present in pipeline output." The actual column binding
happens in the datasetSpec:

```
Execution chain:
  PSDL scenario (declares need for encounter ID)
  -> datasetSpec (binds it to encounters.primary_encounter_id column)
  -> Executor (ensures it persists across daily runs)
```

For a daily pipeline, the executor should:
1. Use `primary_encounter_id` as the stable grain for the patient-surgery episode
2. Carry it forward on each daily run until `discharge_date` is populated
3. Use it as the join key across all data domains (labs, meds, procedures, etc.)

The encounter ID is inherently stable (it's assigned at admission), so it naturally
works across days. The datasetSpec just needs to map it correctly.

## Proposed Extension: Signal Groups (RFC 2026-04-09)

Based on this test case, we proposed a `signal_groups` extension to PSDL.
See full spec: `docs/superpowers/specs/2026-04-09-signal-groups-design.md`

Signal groups add two capabilities:
1. **Domain-level groups**: `all_labs: { domain: laboratory }` - bulk data requests
2. **Custom panels**: `renal_panel: { members: [creatinine, hemoglobin, dialysis_active] }`

Groups are data extraction declarations only - they do NOT feed into trends or logic.
Modeled after OHDSI Concept Sets, leveraging existing OMOP vocabulary integration.

## Verdict

PSDL handles the **cohort logic** (who's in, who's out, what phase, what alerts)
clearly and readably. The data extraction concerns (billing, provider, procedure
code splits) are intentionally delegated to the datasetSpec layer. This separation
is a feature, not a gap - it means the same PSDL scenario works at any site
regardless of their schema.

For a full pipeline, you need both:
- `postop_surgical_cohort.yaml` (this PSDL - defines the logic)
- A site-specific `datasetSpec` (defines the physical data bindings)
