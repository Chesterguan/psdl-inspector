#!/usr/bin/env python3
"""Build vocab-data-v2: merge scope-C drip-feed enrichments into the base extract.

Reads:
  data/vocabulary/extracted/scope_c_concepts.json   (~563K base OMOP records)
  data/vocabulary/batch/results/wave_*_out.jsonl    (337 OpenAI batch result files)

Writes:
  data/vocabulary/built/vocabulary_final.json       (a JSON LIST of enriched records,
                                                     same shape as vocab-data-v1)
  data/vocabulary/built/vocabulary_final.json.gz    (gzipped release asset)

Schema of one record (matches v1):
  concept_id, concept_name, domain_id, vocabulary_id, concept_class_id,
  standard_concept, concept_code, synonyms,
  abbreviations, search_terms, category, typical_units

Drip-feed result line shape:
  {"custom_id": "concept_<id>", "response": {"status_code": 200, "body": {"choices":
    [{"message": {"content": "<json string with enrichment fields>"}}]}}}

If a concept has no enrichment (drip-feed missed it), the enrichment fields fall
back to empty/None, mirroring the v1 behavior for un-enriched records.
"""

from __future__ import annotations

import glob
import gzip
import json
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
BASE_EXTRACT = BACKEND / "data/vocabulary/extracted/scope_c_concepts.json"
RESULTS_GLOB = str(BACKEND / "data/vocabulary/batch/results/wave_*_out.jsonl")
OUT_DIR = BACKEND / "data/vocabulary/built"
OUT_JSON = OUT_DIR / "vocabulary_final.json"
OUT_GZ = OUT_DIR / "vocabulary_final.json.gz"


def _log(msg: str) -> None:
    print(f"[build_vocab_v2] {msg}", flush=True)


def parse_enrichments() -> tuple[dict[int, dict], dict]:
    """Read all wave_*_out.jsonl files, return (concept_id -> enrichment dict, stats)."""
    enrichments: dict[int, dict] = {}
    stats = {"files": 0, "lines": 0, "ok": 0, "non_200": 0, "parse_errors": 0,
             "missing_custom_id": 0, "duplicates": 0}
    files = sorted(glob.glob(RESULTS_GLOB))
    stats["files"] = len(files)
    if not files:
        sys.exit(f"FATAL: no result files match {RESULTS_GLOB}")
    for f in files:
        with open(f) as fh:
            for line in fh:
                stats["lines"] += 1
                d = json.loads(line)
                if d.get("response", {}).get("status_code") != 200 or d.get("error"):
                    stats["non_200"] += 1
                    continue
                cid_raw = d.get("custom_id", "")
                if not cid_raw.startswith("concept_"):
                    stats["missing_custom_id"] += 1
                    continue
                try:
                    cid = int(cid_raw[len("concept_"):])
                except ValueError:
                    stats["missing_custom_id"] += 1
                    continue
                content = (d["response"]["body"]["choices"][0]["message"]
                           .get("content") or "")
                try:
                    enr = json.loads(content)
                except json.JSONDecodeError:
                    stats["parse_errors"] += 1
                    continue
                if cid in enrichments:
                    stats["duplicates"] += 1  # last-wins, but report
                enrichments[cid] = enr
                stats["ok"] += 1
    return enrichments, stats


def load_base_concepts() -> list[dict]:
    if not BASE_EXTRACT.is_file():
        sys.exit(f"FATAL: base extract not found at {BASE_EXTRACT}")
    _log(f"loading base extract: {BASE_EXTRACT.name} "
         f"({BASE_EXTRACT.stat().st_size / (1024 * 1024):.1f} MB)")
    with open(BASE_EXTRACT) as f:
        return json.load(f)


def merge(base: list[dict], enrichments: dict[int, dict]) -> tuple[list[dict], dict]:
    """Produce the merged list. Enrichment fields default to empty when missing."""
    out: list[dict] = []
    merged = 0
    unenriched = 0
    for c in base:
        cid = int(c["concept_id"])
        e = enrichments.get(cid)
        if e is not None:
            merged += 1
        else:
            unenriched += 1
            e = {}
        out.append({
            "concept_id": cid,
            "concept_name": c.get("concept_name", ""),
            "domain_id": c.get("domain_id", ""),
            "vocabulary_id": c.get("vocabulary_id", ""),
            "concept_class_id": c.get("concept_class_id", ""),
            "standard_concept": c.get("standard_concept", ""),
            "concept_code": c.get("concept_code", ""),
            "synonyms": c.get("synonyms", []),
            "abbreviations": e.get("abbreviations"),
            "search_terms": e.get("search_terms"),
            "category": e.get("category"),
            "typical_units": e.get("typical_units"),
        })
    stats = {"merged": merged, "unenriched": unenriched, "total": len(out)}
    return out, stats


def write_artifacts(rows: list[dict]) -> tuple[int, int]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _log(f"writing {OUT_JSON} ({len(rows):,} rows) ...")
    with open(OUT_JSON, "w") as f:
        json.dump(rows, f, separators=(",", ":"), ensure_ascii=False)
    raw = OUT_JSON.stat().st_size
    _log(f"gzipping → {OUT_GZ} ...")
    with open(OUT_JSON, "rb") as src, gzip.open(OUT_GZ, "wb", compresslevel=9) as dst:
        # stream copy so memory stays flat
        while True:
            chunk = src.read(1 << 20)
            if not chunk:
                break
            dst.write(chunk)
    return raw, OUT_GZ.stat().st_size


def main() -> int:
    t0 = time.perf_counter()
    _log("parsing 337 wave result files ...")
    enrichments, stats = parse_enrichments()
    _log(f"  files={stats['files']}, lines={stats['lines']:,}, ok={stats['ok']:,}, "
         f"non_200={stats['non_200']}, parse_errors={stats['parse_errors']}, "
         f"duplicates={stats['duplicates']}, unique_concepts={len(enrichments):,}")

    base = load_base_concepts()
    _log(f"  base concepts: {len(base):,}")

    rows, mstats = merge(base, enrichments)
    _log(f"merged: total={mstats['total']:,}, enriched={mstats['merged']:,}, "
         f"unenriched={mstats['unenriched']:,}")

    raw, gz = write_artifacts(rows)
    _log(f"raw: {raw / (1024 * 1024):.1f} MB, gz: {gz / (1024 * 1024):.1f} MB "
         f"(compression: {raw / gz:.1f}x)")

    _log(f"DONE in {time.perf_counter() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
