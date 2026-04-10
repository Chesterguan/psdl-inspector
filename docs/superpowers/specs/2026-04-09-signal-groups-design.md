# RFC: Signal Groups Extension for PSDL

*Date: 2026-04-09*
*Status: Proposed*
*Affects: psdl-lang, psdl-inspector*

## Problem

Clinical teams request data by domain ("give me all labs") or by meaningful
clinical subsets ("renal panel"), not by individual data elements. PSDL currently
requires every data element to be individually declared as a signal, which:

1. Forces authors to enumerate every lab, med, or procedure they want extracted
2. Doesn't support bulk domain-level data requests ("all labs for these patients")
3. Doesn't reflect how data requests are organized in clinical workflows
4. Makes datasetSpec mapping tedious (bind each signal individually)

**Real-world trigger**: A perioperative surgical cohort definition required 11
data domains (encounters, OR cases, labs, diagnoses, dialysis, procedures,
mortality, billing, vitals, meds, providers). Most of these are bulk extraction
requests, not individually reasoned-about signals.

## Prior Art

| Platform | Fixed Domains | Custom Groups |
|----------|--------------|---------------|
| OHDSI Atlas | OMOP Domain tables | Concept Sets |
| FHIR | Observation Category | ValueSets |
| TriNetX | Data categories | N/A |

PSDL already has `ClinicalDomain` (LABORATORY, VITAL_SIGN, CONDITION,
MEDICATION, PROCEDURE, OBSERVATION, DEMOGRAPHIC) on individual signals, but
it's classification metadata, not a request mechanism.

**Chosen model**: OHDSI Concept Sets - the natural fit since psdl-inspector
already uses OMOP vocabulary for terminology anchoring.

## Design

### Phase 1 (Approach A): `signal_groups` as Top-Level Section

A new optional YAML section between `population` and `signals`.

#### YAML Schema

```yaml
signal_groups:
  # Domain-level group: request all data in a clinical domain
  <group_name>:
    domain: <ClinicalDomain value>
    description: "<required description>"

  # Custom group: named subset of individually defined signals
  <group_name>:
    members: [<signal_name>, ...]
    description: "<required description>"
```

#### Full Example

```yaml
psdl_version: "0.4"
scenario: Perioperative_Surgical_Cohort
version: "0.1.0"

signal_groups:
  # Domain-level: bulk data extraction
  all_labs:
    domain: laboratory
    description: "All lab results for cohort patients"

  all_meds:
    domain: medication
    description: "All medication orders and administrations"

  all_encounters:
    domain: observation
    description: "All clinical encounters including billing and mortality"

  all_procedures:
    domain: procedure
    description: "All procedures (ICD + CPT) for cohort patients"

  # Custom: named signal subsets
  renal_panel:
    members: [creatinine, hemoglobin, dialysis_active]
    description: "Renal function monitoring panel"

  coag_panel:
    members: [inr, platelet_count]
    description: "Coagulation monitoring panel"

signals:
  creatinine:
    ref: creatinine
    expected_unit: mg/dL
    description: "Serum creatinine"
  hemoglobin:
    ref: hemoglobin
    expected_unit: g/dL
    description: "Hemoglobin level"
  # ...
```

#### Validation Rules

1. `domain` and `members` are **mutually exclusive** (Phase 1)
2. Every group must have exactly one of `domain` or `members`
3. `members` entries must reference signal names defined in `signals`
4. `domain` must be a valid `ClinicalDomain` enum value
5. `description` is required
6. Group names must be unique and not collide with signal names
7. The entire `signal_groups` section is optional

#### Relationship to Trends and Logic

**Signal groups have zero interaction with trends or logic.** They are purely
a data extraction declaration for the datasetSpec layer.

```
signal_groups ──> datasetSpec    (tells the site "I need this data")
signals ──> trends ──> logic     (the detection/reasoning chain)
```

A domain-level group like `all_labs: { domain: laboratory }` means "extract
all lab data for these patients" but defines no trends or rules on that bulk
data. Only individually defined signals feed into trends and logic.

### Phase 2 (Approach C): Hybrid Groups (Future)

In a future version, `domain` and `members` can coexist on the same group
for domain-constrained custom panels:

```yaml
signal_groups:
  renal_labs:
    members: [creatinine, bun, urine_output]
    domain: laboratory    # validation constraint: all members must be lab domain
    description: "Renal lab panel"
```

This adds a validation check that all members belong to the declared domain,
catching miscategorization errors. Deferred to keep Phase 1 simple.

## Data Model

### psdl-lang IR (`core/ir.py`)

```python
@dataclass
class SignalGroup:
    """A named collection of signals or a domain-level data request."""
    name: str
    description: str
    domain: Optional[ClinicalDomain] = None  # Domain-level group
    members: Optional[List[str]] = None       # Custom group (signal names)
```

Add to `PSDLScenario`:

```python
@dataclass
class PSDLScenario:
    # ...existing fields...
    signal_groups: Dict[str, SignalGroup] = field(default_factory=dict)
```

### Certified Bundle (v1.2)

Signal groups appear in the exported bundle:

```json
{
  "bundle_version": "1.2",
  "scenario": { "..." },
  "signal_groups": {
    "all_labs": {
      "domain": "laboratory",
      "description": "All lab results for cohort patients"
    },
    "renal_panel": {
      "members": ["creatinine", "hemoglobin", "dialysis_active"],
      "description": "Renal function monitoring panel"
    }
  },
  "terminology_anchors": { "..." },
  "validation": { "..." }
}
```

### datasetSpec Interaction

Signal groups enable bulk mapping in the datasetSpec:

```yaml
# Without groups: map each signal individually
bindings:
  creatinine: { table: lab_results, column: result_value, filter: "loinc = '2160-0'" }
  hemoglobin: { table: lab_results, column: result_value, filter: "loinc = '718-7'" }
  # ...20 more signals...

# With groups: map entire domain at once
group_bindings:
  all_labs: { table: lab_results, value_column: result_value, code_column: loinc_code }
  all_meds: { table: medication_admin, value_column: dose, code_column: rxnorm_code }
```

## Implementation Impact

### Layer-by-Layer Changes

| Layer | Change | Scope | Priority |
|-------|--------|-------|----------|
| **psdl-lang parser** | Parse `signal_groups` section | Core | Must land first |
| **psdl-lang IR** | New `SignalGroup` dataclass | Core | Must land first |
| **psdl-lang validation** | Validate members/domain rules | Core | Must land first |
| **Inspector backend API** | Expose groups in outline + export responses | Small | Second |
| **Inspector OutlineTree** | Display groups as a section in the tree | Medium | Third |
| **Inspector BundlePanel** | Include groups in bundle preview | Small | Third |
| **Inspector Builder UI** | Group creation in visual builder | Medium | Third |
| **Inspector DAG view** | Show groups as cluster nodes (nice-to-have) | Optional | Future |
| **Certified bundle schema** | Bump to v1.2, add `signal_groups` field | Small | Second |

### Implementation Order

```
psdl-lang (parser + IR + validation)
  -> Inspector backend (API responses)
    -> Inspector frontend (display)
```

### Backward Compatibility

- Fully backward compatible: `signal_groups` is an optional section
- Existing scenarios without groups remain valid with no changes
- Bundle version bumps from 1.1 to 1.2 (additive, non-breaking)
- Inspector gracefully handles scenarios with or without groups

## Test Cases for Validation

Build the `testorg/` folder with cases that exercise different group patterns:

| Case | What It Tests |
|------|---------------|
| Perioperative surgical cohort | Domain-level groups + custom panels |
| OHDSI T2DM phenotype | Medication groups, complex inclusion windows |
| MIMIC sepsis cohort | Dense lab signals, multi-organ logic alongside groups |
| Registry quality measure | Procedure groups, billing data extraction |

## Open Questions

1. **Should domain-level groups support filtering?** E.g.,
   `all_labs: { domain: laboratory, filter: "last 7 days" }`. Deferred - this
   is a datasetSpec concern, not a scenario-level concern.

2. **Can groups reference other groups?** E.g., `comprehensive_panel: { members_from: [renal_panel, coag_panel] }`.
   Deferred to Phase 2 to avoid complexity.

3. **Should the Inspector suggest groups automatically?** E.g., if 5+ signals
   share a ClinicalDomain, suggest creating a domain-level group. Nice-to-have
   for Inspector UX.
