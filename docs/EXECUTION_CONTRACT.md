# PSDL Export Bundle: The Execution Contract


## Overview

The **Certified Audit Bundle** is the contract between PSDL Inspector (governance/certification) and execution platforms (runtime systems). Inspector validates and certifies; execution platforms consume and run.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PSDL WORKFLOW                                    │
│                                                                          │
│   AUTHORING           CERTIFICATION              EXECUTION               │
│   ─────────           ─────────────              ─────────               │
│                                                                          │
│   ┌─────────┐        ┌─────────────┐          ┌─────────────────┐       │
│   │ Builder │   →    │  Inspector  │    →     │ Execution       │       │
│   │ / YAML  │        │  (Certify)  │          │ Platform        │       │
│   └─────────┘        └─────────────┘          └─────────────────┘       │
│        │                   │                         │                   │
│        ↓                   ↓                         ↓                   │
│   scenario.yaml    certified_bundle.json      Patient Alerts            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## What's in the Bundle

```json
{
  "bundle_version": "1.2",
  "certified_at": "2026-01-26T10:30:00Z",
  "checksum": "sha256:abc123...",

  "scenario": {
    "name": "AKI_Early_Detection",
    "version": "0.3.1",
    "raw_yaml": "...",
    "parsed": { /* Full IR */ }
  },

  "terminology_anchors": {
    "anchors": {
      "creatinine": {
        "concept_id": 3016723,
        "vocabulary_id": "LOINC",
        "concept_code": "2160-0",
        "standard_unit": "mg/dL"
      }
    }
  },

  "validation": {
    "psdl_lang_version": "0.4.0",
    "valid": true
  },

  "audit": {
    "intent": "Detect early AKI for timely intervention",
    "rationale": "Based on KDIGO guidelines",
    "provenance": "doi:10.1038/..."
  },

  "summary": "Human-readable description..."
}
```

## How Execution Platforms Use the Bundle

### 1. Integrity Verification

```python
import hashlib

def verify_bundle(bundle: dict, raw_yaml: str) -> bool:
    """Verify the bundle hasn't been tampered with."""
    expected = bundle["checksum"]  # "sha256:abc123..."
    actual = "sha256:" + hashlib.sha256(raw_yaml.encode()).hexdigest()
    return expected == actual
```

**Why**: Ensures the scenario hasn't been modified since certification.

### 2. Data Source Binding via Terminology Anchors

The `terminology_anchors` section maps semantic refs to OMOP concept IDs:

```python
def bind_to_data_source(bundle: dict, site_config: dict) -> dict:
    """Map scenario refs to site-specific data queries."""
    bindings = {}

    for ref, anchor in bundle["terminology_anchors"]["anchors"].items():
        concept_id = anchor["concept_id"]

        # Site provides mapping: OMOP concept_id → local query
        if concept_id in site_config["concept_queries"]:
            bindings[ref] = site_config["concept_queries"][concept_id]
        else:
            raise ValueError(f"No data source for concept {concept_id}")

    return bindings
```

**Example site config**:
```yaml
# Site-specific datasetSpec
concept_queries:
  3016723:  # Creatinine
    source: "lab_results"
    column: "value_numeric"
    filter: "concept_id = 3016723"
  3013682:  # BUN
    source: "lab_results"
    column: "value_numeric"
    filter: "concept_id = 3013682"
```

**Why**: Same scenario runs on any OMOP-compliant site without modification.

### 3. Logic Execution

The `scenario.parsed` section contains the full IR for execution:

```python
def execute_scenario(bundle: dict, patient_data: dict) -> dict:
    """Execute the certified scenario against patient data."""
    parsed = bundle["scenario"]["parsed"]

    # 1. Evaluate trends from signals
    trend_values = {}
    for name, trend in parsed["trends"].items():
        trend_values[name] = evaluate_trend(trend["expr"], patient_data)

    # 2. Evaluate logic rules
    results = {}
    for name, rule in parsed["logic"].items():
        results[name] = evaluate_logic(rule["when"], trend_values)

    return {
        "scenario": bundle["scenario"]["name"],
        "version": bundle["scenario"]["version"],
        "certified_at": bundle["certified_at"],
        "checksum": bundle["checksum"],
        "results": results,
        "evaluated_at": datetime.utcnow().isoformat()
    }
```

### 4. Audit Trail Logging

```python
def log_execution(bundle: dict, patient_id: str, results: dict):
    """Log execution with full audit trail."""
    audit_record = {
        "timestamp": datetime.utcnow().isoformat(),
        "patient_id": patient_id,
        "scenario": bundle["scenario"]["name"],
        "version": bundle["scenario"]["version"],
        "checksum": bundle["checksum"],
        "certified_at": bundle["certified_at"],

        # Audit info from certification
        "intent": bundle["audit"]["intent"],
        "rationale": bundle["audit"]["rationale"],
        "provenance": bundle["audit"]["provenance"],

        # Execution results
        "results": results,

        # Validation proof
        "psdl_lang_version": bundle["validation"]["psdl_lang_version"]
    }

    # Store in audit log (immutable)
    audit_log.append(audit_record)
```

**Why**: Complete traceability from algorithm design to patient outcome.

## Execution Platform Responsibilities

| Responsibility | Inspector Provides | Platform Implements |
|----------------|-------------------|---------------------|
| **Scenario correctness** | Validated IR, checksum | Checksum verification |
| **Data binding** | Terminology anchors (OMOP) | Site-specific datasetSpec |
| **Patient data access** | N/A (no PHI) | OMOP/FHIR queries |
| **Real-time evaluation** | Logic expressions | Expression evaluator |
| **Alert delivery** | Severity levels | Notification system |
| **Audit logging** | Audit metadata | Immutable audit log |
| **HIPAA compliance** | N/A | PHI handling |

## Example: Complete Execution Flow

```
1. LOAD BUNDLE
   └── Verify checksum
   └── Check psdl_lang_version compatibility

2. BIND DATA SOURCES
   └── For each terminology_anchor:
       └── Map concept_id → site's data query
       └── Fail if unmapped concepts

3. FOR EACH PATIENT:
   a. FETCH SIGNALS
      └── Query site's data using bindings
      └── Get: creatinine=1.5, BUN=25, ...

   b. COMPUTE TRENDS
      └── cr_delta_48h = delta(creatinine, 48h) → 0.4
      └── bun_current = last(BUN) → 25

   c. EVALUATE LOGIC
      └── aki_stage1: cr_delta_48h >= 0.3 → TRUE
      └── aki_stage2: ... → FALSE

   d. GENERATE OUTPUT
      └── decisions: { alert_aki: true }
      └── features: { cr_change: 0.4 }

   e. LOG AUDIT
      └── Store execution record with bundle metadata

   f. DELIVER ALERT (if triggered)
      └── Notify clinician based on severity
```

## Security Considerations

1. **Checksum verification** - Always verify before execution
2. **Version compatibility** - Check psdl_lang_version matches execution engine
3. **No PHI in bundles** - Bundles contain only algorithm, not patient data
4. **Immutable audit logs** - Execution records cannot be modified
5. **Access control** - Only certified bundles should execute

## Integration Examples

### OMOP CDM Integration
```sql
-- Query for creatinine signal (concept_id: 3016723)
SELECT person_id, measurement_date, value_as_number
FROM measurement
WHERE measurement_concept_id = 3016723
  AND measurement_date >= CURRENT_DATE - INTERVAL '48 hours'
ORDER BY measurement_date DESC;
```

### FHIR Integration
```javascript
// Fetch creatinine observations
const observations = await fhirClient.search({
  resourceType: 'Observation',
  code: 'http://loinc.org|2160-0',  // LOINC code from anchor
  patient: patientId,
  date: 'ge' + twoDaysAgo
});
```

## Summary

The Certified Audit Bundle is designed to be:

1. **Self-contained** - Everything needed to execute (except patient data)
2. **Portable** - Works across any OMOP-compliant site
3. **Auditable** - Full provenance and certification metadata
4. **Secure** - Checksummed and versioned
5. **Interoperable** - Terminology anchors enable cross-site deployment

Execution platforms trust Inspector's certification and focus on:
- Data access and binding
- Real-time evaluation
- Alert delivery
- Compliance and audit logging
