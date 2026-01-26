# OMOP Vocabulary Knowledge Base

*Last updated: 2026-01-26*

## Source

- **File**: `/Volumes/extraSupply/Projects/vocabulary_download_v5.zip`
- **Version**: Athena v5 (downloaded 2025-10-16)
- **Total size**: ~4.8GB uncompressed

## File Structure

| File | Size | Description |
|------|------|-------------|
| `CONCEPT.csv` | 868MB | Main concept table |
| `CONCEPT_SYNONYM.csv` | 207MB | Synonyms for concepts |
| `CONCEPT_RELATIONSHIP.csv` | 1.96GB | Relationships between concepts |
| `CONCEPT_ANCESTOR.csv` | 1.63GB | Hierarchical ancestry |
| `DOMAIN.csv` | 1.7KB | Domain definitions |
| `VOCABULARY.csv` | 6KB | Vocabulary definitions |
| `CONCEPT_CLASS.csv` | 19KB | Concept class definitions |

## CONCEPT.csv Schema

```
concept_id          INT       Unique identifier
concept_name        STRING    Human-readable name
domain_id           STRING    Domain (Measurement, Condition, Drug, etc.)
vocabulary_id       STRING    Source vocabulary (LOINC, SNOMED, RxNorm, etc.)
concept_class_id    STRING    Class within vocabulary
standard_concept    CHAR      'S'=Standard, 'C'=Classification, NULL=Non-standard
concept_code        STRING    Original code in source vocabulary
valid_start_date    DATE      YYYYMMDD format
valid_end_date      DATE      YYYYMMDD format
invalid_reason      CHAR      'U'=Updated, 'D'=Deprecated, NULL=Valid
```

## Relevant Domains for PSDL Signals

| Domain | Description | Use Case |
|--------|-------------|----------|
| `Measurement` | Lab tests, vitals, clinical observations | Primary for signals |
| `Condition` | Diagnoses, problems | Logic conditions |
| `Drug` | Medications | Drug-related signals |
| `Procedure` | Clinical procedures | Event triggers |
| `Observation` | Clinical observations | Additional context |

## Standard Measurements by Vocabulary

| Vocabulary | Count | Description |
|------------|-------|-------------|
| LOINC | 68,106 | Lab tests, vitals (primary source) |
| SNOMED | 25,806 | Clinical observations |
| OMOP Extension | 807 | OMOP-specific extensions |
| HCPCS | 79 | Healthcare procedures |

## LOINC Concept Classes (for Measurements)

| Concept Class | Examples |
|---------------|----------|
| `Lab Test` | Creatinine, Glucose, Potassium |
| `Clinical Observation` | Heart rate, Blood pressure |
| `LOINC Hierarchy` | Classification nodes |
| `LOINC Group` | Grouping concepts |
| `LOINC Class` | Class-level concepts |

## Key Concepts for Common Signals

### Labs

| Signal | concept_id | concept_name | LOINC Code |
|--------|------------|--------------|------------|
| Creatinine | 3016723 | Creatinine [Mass/volume] in Serum or Plasma | 2160-0 |
| (more to be added) | | | |

### Vitals

| Signal | concept_id | concept_name | LOINC Code |
|--------|------------|--------------|------------|
| Heart Rate | 3027018 | Heart rate | 8867-4 |
| (more to be added) | | | |

## Concept Naming Patterns

### LOINC Lab Tests
Pattern: `{Analyte} [{Property}] in {Specimen} {--Timing/Condition}`

Examples:
- `Creatinine [Mass/volume] in Serum or Plasma`
- `Glucose [Mass/volume] in Blood`
- `Potassium [Moles/volume] in Serum or Plasma`

### LOINC Clinical Observations
Pattern: `{Observable} {Method/Location}`

Examples:
- `Heart rate`
- `Blood pressure panel with all children optional`
- `Body temperature`

## Standard Concept Indicator

- `standard_concept = 'S'` : Standard concept (preferred for mapping)
- `standard_concept = 'C'` : Classification concept (hierarchical grouping)
- `standard_concept = NULL` : Non-standard (map to standard equivalent)

**For PSDL signals, use only `standard_concept = 'S'`**

## Synonyms

`CONCEPT_SYNONYM.csv` contains alternate names:
- Multi-language support (Spanish, etc.)
- Abbreviations and aliases

Schema:
```
concept_id              INT     Reference to CONCEPT
concept_synonym_name    STRING  Alternate name
language_concept_id     INT     Language (4180186=English, 4182511=Spanish)
```

## Relationships

`CONCEPT_RELATIONSHIP.csv` contains:
- `Maps to` - Non-standard to standard mappings
- `Is a` - Hierarchical relationships
- `Has component` - Panel to component relationships

Useful for:
- Finding related concepts
- Building synonym lists
- Understanding concept hierarchies

## Query Examples

### Find standard measurements for a term
```bash
grep -i "creatinine" CONCEPT.csv | awk -F'\t' '$3=="Measurement" && $6=="S"'
```

### Find synonyms for a concept
```bash
grep "^3016723" CONCEPT_SYNONYM.csv
```

### Count concepts by domain
```bash
awk -F'\t' '$6=="S" {print $3}' CONCEPT.csv | sort | uniq -c | sort -rn
```

## Common Units (UCUM)

| Unit | concept_id | concept_code | Used For |
|------|------------|--------------|----------|
| milligram per deciliter | 8840 | mg/dL | Creatinine, Glucose, BUN |
| millimole per liter | 8753 | mmol/L | Electrolytes (SI) |
| gram per deciliter | 8713 | g/dL | Hemoglobin, Albumin |
| per minute | 8541 | /min | Heart rate, Respiratory rate |
| milliliter per minute | 8795 | mL/min | GFR, Clearance |
| mL/min/1.73m² | 720870 | mL/min/(173.10*-2.m2) | eGFR |
| percent | 8554 | % | SpO2, Ejection fraction |
| thousand | 8566 | 10*3 | WBC count |
| trillion per liter | 8734 | 10*12/L | RBC count |
| heartbeat | 8581 | {hb} | Cardiac output per beat |

### Unit Extraction from LOINC Names

LOINC concept names encode property type in brackets:
- `[Mass/volume]` → mg/dL, g/dL, etc.
- `[Moles/volume]` → mmol/L, mEq/L
- `[#/volume]` → count per volume (cells/uL)
- `[Presence]` → qualitative (positive/negative)

## Notes for Embedding Enrichment

When enriching concepts for embedding, include:
1. `concept_name` - Primary name
2. Synonyms from `CONCEPT_SYNONYM.csv` (English only)
3. Domain context
4. Common abbreviations (need manual curation)
5. Clinical usage context (from LLM)

## Filtering Strategy for PSDL

For initial vocabulary, filter to:
1. `domain_id IN ('Measurement', 'Observation')`
2. `vocabulary_id = 'LOINC'`
3. `standard_concept = 'S'`
4. `concept_class_id IN ('Lab Test', 'Clinical Observation')`

This gives ~68K concepts. May need further filtering by clinical relevance.

---

## Research Findings: ATLAS/OHDSI Approach (2026-01-15)

### How OHDSI ATLAS Handles Vocabulary Search

ATLAS uses [HELIOS](https://github.com/OHDSI/Helios) - an Apache Solr-based search that indexes CONCEPT table fields:
- CONCEPT_ID, CONCEPT_NAME, CONCEPT_CODE
- CONCEPT_CLASS_ID, DOMAIN_ID, VOCABULARY_ID

**Key findings from HELIOS source code:**
1. **Does NOT index CONCEPT_SYNONYM** - synonyms are not searchable
2. **synonyms.txt is empty** - no clinical abbreviations (HR, BP, T2DM)
3. **100x faster than SQL LIKE** - Solr provides significant performance boost
4. **No enrichment** - uses raw OMOP data only

### CONCEPT_SYNONYM Table Analysis

```
Total synonyms:     2,703,047
English synonyms:   1,682,141 (language_concept_id = 4180186)
Spanish synonyms:     911,554 (language_concept_id = 4182511)
```

**Limitations of CONCEPT_SYNONYM:**
- Mostly full descriptions, not abbreviations
- No clinical shorthand (HR, BP, BG, T2DM, HTN)
- Many non-English translations
- Not indexed by ATLAS/HELIOS

**Conclusion:** Our LLM enrichment adds significant value that OMOP/ATLAS doesn't have.

---

## Hierarchy Analysis: Drugs vs Conditions

### Drugs (RxNorm) - Hierarchy Works Well ✅

```
Example: metformin (Ingredient, concept_id: 1503297)
├── 8,198 descendant concepts via CONCEPT_ANCESTOR
├── Includes all formulations, brands, combinations
└── One enrichment → covers all related drugs
```

**Drug Concept Classes (RxNorm):**
| Class | Count | Description |
|-------|-------|-------------|
| Clinical Drug | 53,694 | Specific formulations |
| Branded Drug | 39,618 | Brand name versions |
| Ingredient | 15,869 | Active ingredients ← **Enrich this level only** |

**Strategy for Drugs:** Enrich ~16K Ingredients, use hierarchy for related drugs.

### Conditions (SNOMED) - Hierarchy is Incomplete ⚠️

```
Example: Type 2 diabetes mellitus (SNOMED concept_id: 201826)
├── CONCEPT_ANCESTOR descendants: 15 concepts
├── Text search "type 2 diabetes": 255 concepts
└── Only 6% of related conditions are in hierarchy!
```

**Why?** SNOMED defines many specific conditions as separate concepts, not hierarchical descendants:
- "T2DM with renal complications" is NOT a child of "T2DM"
- These are related via "Due to of" relationship (126 links for T2DM)

**Condition Concept Classes (SNOMED):**
| Class | Count | Description |
|-------|-------|-------------|
| Disorder | 142,701 | Specific conditions |
| Clinical Finding | 21,808 | Broader findings ← **Potential enrichment target** |

### CONCEPT_RELATIONSHIP for Conditions

```sql
-- T2DM relationship types
Due to of:        126  ← Complications related to T2DM
Mapped from:       90  ← ICD codes mapping to this
Subsumes:          16  ← Hierarchical children
Asso finding of:    4  ← Associated findings
```

The "Due to of" relationship captures condition relationships better than hierarchy.

---

## Enrichment Strategy Recommendations

### For Signals (Measurements) - Current Approach ✅
- **Source:** LOINC (75,773 concepts)
- **Enrichment:** LLM-generated abbreviations, search terms, categories
- **Status:** 46,000/75,773 enriched (61%)
- **Why needed:** Clinicians use abbreviations (HR, BP, K+, BUN)

### For Drugs (Population Criteria)
- **Source:** RxNorm Ingredients only (~16K)
- **Enrichment:** LLM abbreviations for common drugs
- **Hierarchy:** Use CONCEPT_ANCESTOR for formulations
- **Estimated cost:** ~$2 OpenAI batch

### For Conditions (Population Criteria)
**Option A: Text-based search (no enrichment)**
- Use native OMOP name search
- Add CONCEPT_SYNONYM for English synonyms
- Lower precision but zero cost

**Option B: Enrich high-level conditions**
- Focus on "Clinical Finding" class (~22K)
- Add abbreviations for common conditions (T2DM, HTN, CHF)
- Use "Due to of" relationship to find related conditions
- Estimated cost: ~$3 OpenAI batch

**Option C: Hybrid with embeddings**
- Embed condition names and search terms
- Semantic search for related conditions
- Highest precision, higher complexity

### Cost-Benefit Summary

| Domain | Concepts | Enrichment | Cost | Benefit |
|--------|----------|------------|------|---------|
| Signals (LOINC) | 75K | LLM abbreviations | $8 | High - clinicians use abbr |
| Drugs (Ingredients) | 16K | LLM abbreviations | $2 | Medium - common names exist |
| Conditions (SNOMED) | 22K | LLM abbreviations | $3 | Medium - hierarchy incomplete |

---

## Implementation Notes

### CONCEPT_ANCESTOR Usage
```python
# Find all formulations of metformin
SELECT descendant_concept_id
FROM concept_ancestor
WHERE ancestor_concept_id = 1503297  -- metformin ingredient
  AND min_levels_of_separation > 0

# Find parent conditions of a specific condition
SELECT ancestor_concept_id
FROM concept_ancestor
WHERE descendant_concept_id = 201826  -- T2DM
  AND min_levels_of_separation > 0
```

### CONCEPT_RELATIONSHIP Usage for Conditions
```python
# Find conditions related to T2DM via "Due to" relationship
SELECT cr.concept_id_2, c.concept_name
FROM concept_relationship cr
JOIN concept c ON cr.concept_id_2 = c.concept_id
WHERE cr.concept_id_1 = 201826  -- T2DM
  AND cr.relationship_id = 'Due to of'
```

### References
- [OHDSI HELIOS](https://github.com/OHDSI/Helios) - Solr-based search
- [The Book of OHDSI - Vocabularies](https://ohdsi.github.io/TheBookOfOhdsi/StandardizedVocabularies.html)
- [OHDSI WebAPI Solr Integration](https://github.com/OHDSI/WebAPI/issues/580)

---

## Tracking

- **Population Enrichment Issue**: [GitHub #2](https://github.com/Chesterguan/psdl-inspector/issues/2)
- **Modular Search Architecture**: [GitHub #3](https://github.com/Chesterguan/psdl-inspector/issues/3)
- **Tier 1 Target**: ~40K concepts (16K drugs + 22K conditions + 1K procedures)
- **Estimated Cost**: ~$3-5 OpenAI Batch API

---

## Modular Vocabulary Search System (2026-01-26)

### Architecture

Implemented a pluggable architecture for vocabulary concept matching:

```
app/services/vocabulary_search/
├── __init__.py       # Package exports
├── base.py           # Abstract base classes
├── embedders.py      # Embedding implementations
├── retrievers.py     # Vector retrieval implementations
├── rerankers.py      # Score adjustment implementations
└── factory.py        # Configuration & factory functions
```

### Available Components

| Type | Options | Default |
|------|---------|---------|
| **Embedders** | `minilm`, `minilm-l12`, `mpnet`, `sapbert`, `biolord`, `openai`, `openai-large` | `minilm` |
| **Retrievers** | `faiss`, `numpy`, `hnsw` | `faiss` |
| **Rerankers** | `none`, `rules`, `string`, `hybrid` | `rules` |

### Configuration Methods

```python
# Presets
SearchEngineConfig.default()           # minilm + faiss + rules (fast, good)
SearchEngineConfig.medical_optimized() # sapbert + faiss + hybrid (best for medical)
SearchEngineConfig.high_quality()      # biolord + faiss + hybrid (ontology-grounded)

# Environment variables
VOCAB_SEARCH_EMBEDDER=sapbert
VOCAB_SEARCH_RETRIEVER=faiss
VOCAB_SEARCH_RERANKER=hybrid
```

### Embedder Research

1. **SapBERT** (`cambridgeltl/SapBERT-from-PubMedBERT-fulltext`)
   - Trained on 4M+ UMLS synonyms via self-alignment pretraining
   - SOTA on 6 medical entity linking benchmarks
   - Best for medical concept matching

2. **BioLORD-2023** (`FremyCompany/BioLORD-2023`)
   - Ontology-grounded embeddings using SNOMED-CT and UMLS definitions
   - Good for hierarchical concept understanding
   - Understands concept relationships

3. **Hybrid Re-ranking**
   - Research shows combining embeddings with Jaccard/Levenshtein improves accuracy
   - Implemented in `rerankers.py` as `hybrid` option

### Test Results (Default: minilm + faiss + rules)

| Query | Rank 1 Result | Status |
|-------|---------------|--------|
| `creatinine` | Creatinine [Mass/volume] in Serum or Plasma | ✅ Correct |
| `glucose` | Glucose [Mass/volume] in Serum or Plasma | ✅ Correct |
| `heart rate` | Heart rate Intra arterial line by Invasive | ⚠️ Should prefer simple concept |
| `hemoglobin` | Hemoglobin [Mass/volume] in Venous blood | ⚠️ Should prefer general |
| `blood pressure` | Blood pressure panel | ⚠️ Acceptable |

### References

- SapBERT paper: https://arxiv.org/abs/2010.11784
- BioLORD paper: https://arxiv.org/abs/2311.16075
- OHDSI Usagi: https://github.com/OHDSI/Usagi
