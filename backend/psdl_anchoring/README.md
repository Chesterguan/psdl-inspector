# psdl_anchoring

Terminology anchoring for the PSDL ecosystem: bind PSDL semantic signal references to OMOP vocabulary concepts.

## What it does

Given a PSDL signal reference (e.g. `creatinine`, `heart_rate`, `diabetes_diagnosis`) and optionally the signal's PSDL domain (e.g. `measurement`, `condition`), this package:

1. Searches the vocabulary for matching OMOP concepts.
2. Applies domain filtering to avoid lab/drug collisions (e.g. `creatinine` with `psdl_domain="measurement"` anchors to a LOINC lab concept, not an RxNorm drug).
3. Returns a `TerminologyAnchor` with concept ID, vocabulary, confidence level, and standard unit.

## Key design decision

Uses the **Workbench domain-threaded** `anchor_ref(ref, psdl_domain, unit)` as the canonical version (supersedes the earlier undirected Inspector version). Domain filtering is strictly better — Inspector gains it on upgrade.

## Usage

```python
from psdl_anchoring import get_terminology_anchoring_service

svc = get_terminology_anchoring_service()

# Anchor a single ref with domain context
anchor = svc.anchor_ref("creatinine", psdl_domain="measurement")
print(anchor.vocabulary_id, anchor.concept_id, anchor.match_confidence)
# e.g. LOINC 2160-0 high

# Anchor all refs in a parsed scenario
anchors = svc.anchor_scenario(scenario)
print(anchors.anchored_count, "/", anchors.total_refs)
```

## Flat layout

This package uses setuptools flat layout: `pyproject.toml` and `__init__.py` are siblings inside `backend/psdl_anchoring/`. Install with:

```bash
pip install -e ./psdl_anchoring
```
