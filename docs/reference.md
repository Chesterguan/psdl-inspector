# API & bundle reference

## API reference

### GET /api/version
```json
{ "inspector": "0.2.0", "psdl_lang": "0.4.0" }
```

### GET /api/generate/status
Check LLM provider availability.

### POST /api/generate/scenario
```json
{ "prompt": "Detect AKI using creatinine changes", "provider": "openai", "max_retries": 3, "clinical_context": "KDIGO criteria..." }
```

### POST /api/validate
Validate a PSDL scenario.

### POST /api/outline
Generate semantic outline with dependency tracking.

### POST /api/export/bundle
Export certified audit bundle with checksum.

### POST /api/export/irb-document
Export AI-enriched Word document for IRB preparation.

### POST /api/meds/preview
Synthesize a 10-row MEDS preview shard from anchored signals. Subjects are synthetic negative integers and timestamps step from 2024-01-01, so the output can never collide with real PHI; the shard is validated against `meds.schema.data_schema()` before return.

## Certified audit bundle (the authoring → execution contract)

```json
{
  "bundle_version": "1.2",
  "certified_at": "2026-01-26T10:30:00Z",
  "checksum": "sha256:abc123...",
  "scenario": { "name": "AKI_Detection", "version": "0.3.1", "raw_yaml": "...", "parsed": { } },
  "terminology_anchors": {
    "anchors": {
      "creatinine": {
        "concept_id": 3016723, "vocabulary_id": "LOINC", "concept_code": "2160-0",
        "concept_name": "Creatinine [Mass/volume] in Serum or Plasma",
        "standard_unit": "mg/dL", "match_confidence": "high"
      }
    },
    "unanchored_refs": [], "anchored_count": 1, "total_refs": 1
  },
  "validation": { "psdl_lang_version": "0.4.0", "inspector_version": "0.2.0", "valid": true, "errors": [], "warnings": [] },
  "audit": { "intent": "Detect early AKI for timely intervention", "rationale": "Based on KDIGO guidelines", "provenance": "doi:10.1038/..." },
  "summary": "Human-readable summary for IRB..."
}
```

The `terminology_anchors` section maps semantic refs (e.g., "creatinine") to OMOP concept IDs, enabling portable execution across any OMOP-compliant site, standard vocabulary binding (LOINC, SNOMED, RxNorm), and a clear audit trail. See [EXECUTION_CONTRACT.md](EXECUTION_CONTRACT.md) for how execution platforms consume it.

### MEDS Preview (`psdl_meds`)

Inspector embeds the [`psdl_meds`](https://github.com/Chesterguan/psdl-inspector/tree/main/backend/psdl_meds) library so authors can see what their scenario produces in [MEDS](https://github.com/Medical-Event-Data-Standard/meds) format **before** running it against real data — the "Preview MEDS shape" card on Export, or the CLI:

```bash
psdl-meds convert --input cohort.csv --out cohort.parquet
psdl-meds preview --anchors anchors.json --out preview.parquet -n 10
```

The same library backs **PSDL Workbench** for live OMOP-backed cohort exports.

## Compatibility

Inspector **always tracks the latest `psdl-lang`** — the requirements pin is `psdl-lang>=0.4.0`. The table records the spec/bundle versions consumed at each Inspector release; older Inspector versions are not retroactively bumped.

| Inspector Version | psdl-lang at release | PSDL Spec | Bundle Version | Status |
|-------------------|----------------------|-----------|----------------|--------|
| 0.2.x | 0.4.x (latest) | 0.4 | 1.2 | **Current** |
| 0.1.x | 0.3.1 | 0.3 | 1.0 | Maintained (legacy spec) |
| - | < 0.2 | - | - | Not supported |
