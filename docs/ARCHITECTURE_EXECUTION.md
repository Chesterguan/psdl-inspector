# PSDL Execution Architecture

*Last updated: 2026-01-26*

## Overview

PSDL separates **clinical logic** (scenarios) from **data binding** (datasetSpec). This document describes how these layers connect to enable portable, executable clinical algorithms.

## Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EXECUTION CHAIN                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐                                                        │
│  │  PSDL Scenario   │  WHAT to detect (pure clinical logic)                  │
│  │                  │  Signals use semantic refs only                        │
│  │  signals:        │  e.g., ref: creatinine                                 │
│  │    cr:           │                                                        │
│  │      ref: creat  │  NO physical bindings here                             │
│  └────────┬─────────┘                                                        │
│           │                                                                  │
│           │  Inspector validates + enriches                                  │
│           ↓                                                                  │
│  ┌──────────────────┐                                                        │
│  │  Certified       │  Contains:                                             │
│  │  Bundle          │  - Validated scenario                                  │
│  │                  │  - terminologyAnchors (OMOP vocabulary binding)        │
│  │ terminologyAnchors│  - Checksum, audit info                               │
│  │    creatinine:   │                                                        │
│  │      concept_id  │  Anchors semantic refs to standard vocabulary          │
│  │      concept_code│                                                        │
│  │      vocabulary  │                                                        │
│  └────────┬─────────┘                                                        │
│           │                                                                  │
│           │  Runtime pairs with site's datasetSpec                           │
│           ↓                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     datasetSpec (same schema)                         │   │
│  │                                                                       │   │
│  │  Maps semantic refs → physical data locations                         │   │
│  │  Defines: table, column, concept_id filter, units, timestamps         │   │
│  │                                                                       │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐  │   │
│  │  │ omop_cdm_v54   │  │ mimic_iv       │  │ hospital_xyz           │  │   │
│  │  │ (standard)     │  │ (PhysioNet)    │  │ (custom institution)   │  │   │
│  │  └────────────────┘  └────────────────┘  └────────────────────────┘  │   │
│  │                                                                       │   │
│  │  All follow spec/dataset_schema.json                                  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│           │                                                                  │
│           ↓                                                                  │
│  ┌──────────────────┐                                                        │
│  │  Local Database  │  Actual patient data                                   │
│  └──────────────────┘                                                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Layer Responsibilities

| Layer | Purpose | Who Creates | Schema |
|-------|---------|-------------|--------|
| **Scenario** | Clinical logic (WHAT to detect) | Clinician/Author | `spec/schema.json` |
| **terminologyAnchors** | Standard vocabulary binding (OMOP) | Inspector (auto) | TBD |
| **datasetSpec** | Physical data binding (WHERE data lives) | Site data analyst | `spec/dataset_schema.json` |

## Scenario Layer

Defined by `spec/schema.json`. Contains:

- **signals**: Semantic references (e.g., `ref: creatinine`)
- **trends**: Computed values from signals
- **logic**: Boolean predicates (clinical rules)
- **audit**: Intent, rationale, provenance

**Key principle**: NO physical bindings. Signals use semantic refs only.

```yaml
# Example scenario (pure logic)
signals:
  cr:
    ref: creatinine
    # NO concept_id, table, or column here

trends:
  cr_delta_48h:
    expr: delta(cr, 48h)

logic:
  aki_stage1:
    when: cr_delta_48h >= 0.3
    severity: high
```

## terminologyAnchors Layer (Inspector's Contribution)

Added by Inspector at export time. Anchors semantic refs to standard vocabulary:

```yaml
terminologyAnchors:
  creatinine:
    concept_id: 3016723
    concept_code: "2160-0"
    vocabulary_id: LOINC
    concept_name: "Creatinine [Mass/volume] in Serum or Plasma"
    standard_unit: mg/dL
    match_confidence: high  # or medium, low, unanchored

  heart_rate:
    concept_id: 3027018
    concept_code: "8867-4"
    vocabulary_id: LOINC
    concept_name: "Heart rate"
    standard_unit: /min
    match_confidence: high
```

**Purpose**:
1. Validates scenario uses standard terminology
2. Provides vocabulary metadata for governance
3. Helps sites create their datasetSpec (they know what concept_ids to map)
4. Enables cross-site scenario portability

**Unanchored signals**: Logged with warnings in bundle. Sites can still execute if they provide custom mapping in their datasetSpec.

## datasetSpec Layer

Defined by `spec/dataset_schema.json`. Maps semantic refs to physical data:

```yaml
# Example: omop_cdm_v54.yaml
psdl_version: "0.3"
dataset:
  name: omop_cdm_v54
  version: "1.0.0"
data_model: omop

conventions:
  patient_id_field: person_id
  default_timestamp_field: measurement_datetime
  timezone: UTC
  unit_strategy: strict

elements:
  creatinine:
    table: measurement
    value_field: value_as_number
    time_field: measurement_datetime
    patient_field: person_id
    filter:
      concept_id: 3016723
    unit: mg/dL
```

**Key point**: All datasetSpecs (standard OMOP, MIMIC-IV, custom institution) follow the SAME schema. They're just different instances with different values.

## Execution Flow

```
1. Author writes PSDL scenario (pure logic, semantic refs)
        ↓
2. Inspector validates + generates terminologyAnchors (OMOP binding)
        ↓
3. Export certified bundle (scenario + terminologyAnchors + audit)
        ↓
4. Site has datasetSpec (maps refs → their physical data)
        ↓
5. Runtime: Bundle + datasetSpec → Execute against local data
```

## terminologyAnchors Implementation

### Schema Definition

```python
class TerminologyAnchor(BaseModel):
    """Single terminology anchor for a semantic reference."""
    concept_id: Optional[int] = None
    concept_code: Optional[str] = None
    vocabulary_id: Optional[str] = None
    concept_name: Optional[str] = None
    standard_unit: Optional[str] = None
    match_confidence: Literal["high", "medium", "low", "unanchored"]

class TerminologyAnchors(BaseModel):
    """All terminology anchors for a scenario."""
    anchors: Dict[str, TerminologyAnchor]
    unanchored_refs: List[str]  # Refs that couldn't be matched
    anchor_timestamp: str  # When anchoring was performed
    vocabulary_version: Optional[str] = None  # OMOP vocabulary version
```

### Confidence Levels

| Level | Criteria | Action |
|-------|----------|--------|
| **high** | Exact match or known alias | Auto-accept |
| **medium** | Fuzzy match >80% similarity | Include with note |
| **low** | Fuzzy match 60-80% similarity | Include with warning |
| **unanchored** | No match found | Log warning, allow custom mapping |

### Implementation Location

- **Service**: `backend/app/services/terminology_anchoring.py`
- **Called from**: `backend/app/services/exporter.py` at bundle export
- **Uses**: `backend/app/services/vocabulary.py` for OMOP lookup

### Bundle Structure with terminologyAnchors

```json
{
  "bundle_version": "1.1",
  "certified_at": "2026-01-23T12:00:00Z",
  "checksum": "sha256:...",
  "scenario": { ... },
  "terminologyAnchors": {
    "anchors": {
      "creatinine": {
        "concept_id": 3016723,
        "concept_code": "2160-0",
        "vocabulary_id": "LOINC",
        "concept_name": "Creatinine [Mass/volume] in Serum or Plasma",
        "standard_unit": "mg/dL",
        "match_confidence": "high"
      }
    },
    "unanchored_refs": [],
    "anchor_timestamp": "2026-01-23T12:00:00Z"
  },
  "validation": { ... },
  "audit": { ... }
}
```

## References

- PSDL Scenario Schema: `spec/schema.json`
- Dataset Spec Schema: `spec/dataset_schema.json`
- Example datasetSpecs: `dataset_specs/omop_cdm_v54.yaml`
- Example institution mappings: `mappings/hospital_template.yaml`
- Execution Contract: See [EXECUTION_CONTRACT.md](EXECUTION_CONTRACT.md) for how execution platforms consume bundles
