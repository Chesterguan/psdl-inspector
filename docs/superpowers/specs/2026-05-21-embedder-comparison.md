# Embedder Comparison for LOINC Vocabulary Search

*Drafted: 2026-05-21 — research finding for issue #3.*

## Background

The production vocabulary search endpoint (`/api/vocabulary/semantic/search`) ranks LOINC concepts by cosine similarity against **OpenAI `text-embedding-3-small`** embeddings. On three generic clinical queries — `heart rate`, `hemoglobin`, `blood pressure` — the rank-1 result is consistently a metadata or specimen-specific variant rather than the simple standard measurement (see issue #3).

PR #5 added domain rules to the unused modular `backend/app/services/vocabulary_search/` package; smoke testing afterward revealed those rules never run in production because the router uses `vocabulary_sqlite.SemanticVocabularyService` instead.

## Research Question

Would a clinically-trained embedding model fix the rank-1 quality on its own, or is a reranker still necessary?

## Method

Built `backend/scripts/sapbert_smoke_test.py` (gitignored, research tooling). For each of 13 clinical queries:

1. Pull LOINC candidates whose name contains the full query phrase as a substring (LIMIT 200, embedding NOT NULL).
2. Re-embed both the query and the candidate names with each embedder.
3. Sort candidates by cosine similarity and report top-3.

Embedders compared:

| Model | Variant | Pooling | Dim |
|---|---|---|---|
| OpenAI `text-embedding-3-small` | Live `/api/vocabulary/semantic/search` (results captured manually) | — | 1536 |
| SapBERT | `cambridgeltl/SapBERT-from-PubMedBERT-fulltext` via the existing `SapBERTEmbedder` | CLS token | 768 |
| BioLORD-2023 | `FremyCompany/BioLORD-2023` via sentence-transformers | mean | 768 |
| MedEmbed-large-v0.1 | `abhinand/MedEmbed-large-v0.1` via sentence-transformers | mean | 1024 |
| EmbeddingGemma-300m | `google/embeddinggemma-300m` | — | — |

EmbeddingGemma is a gated model and was not exercised in this run (HF auth setup pending). It can be added by re-running the script once auth is configured.

## Results

Rank-1 result per query, per embedder. ✅ = clinically appropriate, ⚠️ = related but suboptimal, ❌ = wrong concept category.

| Query | OpenAI (prod) | SapBERT | BioLORD | MedEmbed |
|---|---|---|---|---|
| heart rate | ❌ Heart rate method | ✅ Heart rate | ✅ Heart rate | ✅ Heart rate |
| blood pressure | ❌ Blood pressure method | ❌ Blood pressure method | ✅ Systolic blood pressure | ❌ Blood pressure method |
| temperature | — | ✅ Body temperature | ✅ Body temperature | ❌ Toe temperature |
| oxygen saturation | — | ✅ Oxygen saturation in Blood | ✅ Oxygen saturation in Blood | ❌ Infant activity… |
| respiratory rate | — | ✅ Respiratory rate | ✅ Respiratory rate | ✅ Respiratory rate |
| **creatinine** | — | ❌ Creatinine dialysis fluid clearance | ❌ Creatinine [Interpretation] in Urine | ❌ Ornithine/Creatinine ratio |
| glucose | — | ❌ Glucose management indicator | ⚠️ Glucose [Mass/volume] in Blood | ✅ Glucose [Moles/volume] in Serum or Plasma |
| hemoglobin | ❌ [Presence] in Specimen | ❌ Hemoglobinopathy panel | ✅ Hemoglobin [Presence] in Blood | ❌ Hemoglobin pattern |
| **sodium** | — | ❌ Sodium intake Measured | ❌ Sodium [Mass/mass] in Specimen | ❌ Sodium [Moles/volume] in Urine |
| **potassium** | — | ❌ Potassium intake Measured | ❌ Potassium [Mass/mass] in Specimen | ❌ Potassium [Moles/time] in unspecified |
| hemoglobin A1c | — | ⚠️ A1c/Hemoglobin.total in Blood | ✅ A1c [Mass/volume] in Blood | ❌ A1c/Hemoglobin.total goal Blood |
| troponin | — | ❌ Time interval between troponin assays | ✅ Troponin T.cardiac [Presence] in Blood | ✅ Troponin T.cardiac [Mass/volume] in Blood |
| lactate | — | ❌ Lactate/Creatinine ratio in Urine | ✅ Lactate [Mass/volume] in Serum or Plasma | ❌ Lactate [Moles/volume] post challenge |

### Win count (✅ rank-1)

| Embedder | Wins | Coverage |
|---|---|---|
| BioLORD-2023 | **9 / 13** | strong across vitals, hematology, cardiac, specialty labs |
| SapBERT | 4 / 13 | wins on vitals only; loses on chemistry, hematology variants |
| MedEmbed-large | 4 / 13 | scattered wins; loses on most lab cases |
| OpenAI text-embedding-3-small | 0 / 3 | (only 3 queries verified live, all failed) |

### Where ALL embedders fail

- **Creatinine, sodium, potassium** — basic chemistry tests where the clinically-correct concept is `[Mass/volume] in Serum or Plasma` or `[Moles/volume] in Serum or Plasma`. Every embedder picks a urine variant, an "intake" variant, or a specimen-specific variant.

This is the case for which the existing `RuleBasedReranker.SERUM_PLASMA_TESTS` rule was written (`rerankers.py:156`). No embedding model alone solves it because the "what specimen is clinically standard" knowledge is structural, not derivable from concept names.

### Query terminology mismatches

Two queries returned **zero candidates** because LOINC stores them differently:

| Query as written | LOINC stores as |
|---|---|
| `platelet count` | `Platelets [#/volume] in Blood` |
| `white blood cell count` | `Leukocytes [#/volume] in Blood` |

In production the embedding-based retrieval doesn't filter on substring — it scores all concepts by similarity, so this gap doesn't appear at the user-facing layer. But it's a reminder that query → concept name mapping is non-trivial even before reranking.

## Architectural Conclusion

**BioLORD as default embedder, modular `vocabulary_search/` engine on top, `RuleBasedReranker` to enforce clinical hierarchy where embeddings fail.**

The split is principled:
- **Embedder** handles broad semantic recall (synonyms, abbreviations, related concepts). BioLORD is SOTA among open models on this dimension.
- **Reranker** enforces non-textual clinical conventions ("prefer Serum/Plasma over urine for basic chemistry", "prefer Mass/volume over Presence", "demote panel/method/device concepts when the query is generic").

PR #5's rules slot in here as the reranker layer.

Embedder choice should remain configurable per project policy (open-source, adaptive to SOTA). The `vocabulary_search/factory.py` registry already supports this; the missing piece is wiring the engine into the router.

## Open Items

- **EmbeddingGemma not tested** — gated model requires HF auth. Script supports it; re-run after auth setup. Survey paper "Towards Domain Specification of Embedding Models in Medicine" (arXiv 2507.19407) lists it alongside BioLORD and MedEmbed as a top-tier medical embedder, so worth confirming whether it edges BioLORD.
- **Reranker layer not yet applied to BioLORD output** — this comparison is embedders-only. The combined BioLORD + RuleBasedReranker behavior on the basic-chemistry failures has not been measured.

## Next Steps

1. Re-embed all 75,773 LOINC + 30,587 population concepts with BioLORD (~10 min on CPU based on observed throughput of ~200 concepts/sec).
2. Wire the modular `VocabularySearchEngine` into `/api/vocabulary/semantic/search` and `/api/vocabulary/population/search` (currently use `vocabulary_sqlite.SemanticVocabularyService`).
3. Apply `RuleBasedReranker` (PR #5 version) on top of BioLORD retrieval.
4. Re-run this smoke test to verify the combined BioLORD + reranker output beats embedder-only on all 13 cases.
5. Add EmbeddingGemma to the registry once HF auth is set up; allow runtime swap via env var.

## Local Reproduction

```bash
cd backend
source .venv/bin/activate
python scripts/sapbert_smoke_test.py
```

Script is in `backend/scripts/sapbert_smoke_test.py` (gitignored, internal tooling). Results JSON written to `backend/scripts/sapbert_smoke_results.json`.
