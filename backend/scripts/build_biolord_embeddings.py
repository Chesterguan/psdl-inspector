#!/usr/bin/env python3
"""Build a BioLORD-2023 FAISS index from the vocab-data-v2 vocabulary JSON.

Usage:
    python scripts/build_biolord_embeddings.py \
        --vocab ~/.cache/psdl_vocab/v2/vocabulary_final.json \
        --out /tmp/biolord_build \
        --batch-size 256

Produces four files in <out_dir>:
    embeddings.npy         float32 (N, 768) L2-normalised
    index.faiss            FAISS IndexFlatIP
    index.faiss.meta       pickle of list[int] concept_ids in row order
    metadata.json          provenance record (model, dim, text_format, etc.)

A resumable checkpoint <out_dir>/progress.npz is written after every batch and
removed once the final artefacts are committed.  Re-running the script after an
interruption picks up from where it left off.

Text format (pinned in metadata.json):
    concept_name | synonym_1 | synonym_2 | ... | search_term_1 | ... | abbrev_1 | ...

Rules: all fields lowercased and stripped; None values dropped; duplicates removed
(first-occurrence-wins, order preserved); joined with ' | '; truncated to 256 chars.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import pickle
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import numpy as np

logging.basicConfig(level=logging.INFO, format="[build] %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Text builder
# ---------------------------------------------------------------------------

TEXT_FORMAT = "concept_name | synonyms | search_terms | abbreviations"
TEXT_RULES = (
    "Lowercase and strip each field value; drop None / falsy entries; "
    "remove duplicates preserving first-occurrence order; join with ' | '; "
    "truncate to 256 characters."
)
TEXT_CAP = 256


def build_concept_text(concept: dict) -> str:
    """Produce the canonical embedding input string for one concept dict.

    Fields used, in order: concept_name, synonyms (list), search_terms (list),
    abbreviations (list).  None values and empty strings are skipped.  Duplicates
    are removed with first-occurrence-wins semantics.  The result is truncated to
    TEXT_CAP (256) characters.
    """
    raw: list[str] = []
    raw.append(concept.get("concept_name") or "")

    for field in ("synonyms", "search_terms", "abbreviations"):
        values = concept.get(field)
        if values is None:
            continue
        if isinstance(values, str):
            raw.append(values)
        else:
            raw.extend(v for v in values if v is not None)

    # lowercase + strip, drop falsy
    parts: list[str] = []
    seen: set[str] = set()
    for p in raw:
        norm = str(p).lower().strip()
        if not norm:
            continue
        if norm in seen:
            continue
        seen.add(norm)
        parts.append(norm)

    text = " | ".join(parts)
    return text[:TEXT_CAP]


# ---------------------------------------------------------------------------
# Model loader
# ---------------------------------------------------------------------------

MODEL_ID = "FremyCompany/BioLORD-2023"


def _load_model():
    """Load BioLORD-2023 with MPS → CUDA → CPU device preference."""
    from sentence_transformers import SentenceTransformer  # type: ignore
    import torch  # type: ignore

    if torch.backends.mps.is_available():
        device = "mps"
    elif torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"

    log.info("Loading %s on %s …", MODEL_ID, device)
    model = SentenceTransformer(MODEL_ID, device=device)
    log.info("BioLORD-2023 loaded on %s", device)
    return model


# ---------------------------------------------------------------------------
# L2 normalisation
# ---------------------------------------------------------------------------


def _normalize(arr: np.ndarray) -> np.ndarray:
    """L2-normalise rows to unit vectors; return float32."""
    arr = arr.astype(np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return arr / norms


# ---------------------------------------------------------------------------
# Index builder (resumable)
# ---------------------------------------------------------------------------

PROGRESS_FILE = "progress.npz"


def build_index(concepts: list, out_dir: Path, batch_size: int = 256) -> None:
    """Embed all concepts into a FAISS IndexFlatIP; write four artefact files.

    Resumable: after each batch the partial results are checkpointed to
    <out_dir>/progress.npz.  Re-running the script loads the checkpoint and skips
    already-embedded concepts.
    """
    import faiss  # type: ignore

    out_dir.mkdir(parents=True, exist_ok=True)
    progress_path = out_dir / PROGRESS_FILE

    # ---- load checkpoint if present ----------------------------------------
    done_ids: set[int] = set()
    saved_embeddings: list[np.ndarray] = []
    saved_concept_ids: list[int] = []

    if progress_path.exists():
        try:
            chk = np.load(progress_path)
            saved_embeddings = [chk["embeddings"]]
            saved_concept_ids = list(chk["concept_ids"].tolist())
            done_ids = set(saved_concept_ids)
            log.info("Resumed from checkpoint: %d concepts already embedded.", len(done_ids))
        except Exception as exc:
            log.warning("Could not load checkpoint (%s); starting fresh.", exc)

    # ---- filter remaining --------------------------------------------------
    remaining = [c for c in concepts if c["concept_id"] not in done_ids]
    log.info("%d concepts to embed (%d remaining after checkpoint).", len(concepts), len(remaining))

    # ---- load model (only if there is work to do) --------------------------
    if remaining:
        model = _load_model()

        total = len(remaining)
        for batch_start in range(0, total, batch_size):
            batch = remaining[batch_start: batch_start + batch_size]
            texts = [build_concept_text(c) for c in batch]
            ids = [c["concept_id"] for c in batch]

            embeddings = model.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=False,
                convert_to_numpy=True,
            ).astype(np.float32)

            saved_embeddings.append(embeddings)
            saved_concept_ids.extend(ids)

            # checkpoint after each batch (overwrite — atomic-ish on most FS)
            all_emb_so_far = np.vstack(saved_embeddings)
            all_ids_so_far = np.array(saved_concept_ids, dtype=np.int64)
            # write to tmp then rename for better atomicity
            tmp_progress = out_dir / (PROGRESS_FILE + ".tmp")
            np.savez(tmp_progress, embeddings=all_emb_so_far, concept_ids=all_ids_so_far)
            tmp_progress.rename(progress_path)

            done_count = len(saved_concept_ids)
            pct = done_count / len(concepts) * 100
            log.info("  %d / %d (%.1f%%)", done_count, len(concepts), pct)

    # ---- finalise artefacts ------------------------------------------------
    final_embeddings: np.ndarray
    if saved_embeddings:
        final_embeddings = np.vstack(saved_embeddings)
    else:
        # nothing to embed (all were in checkpoint and no remaining)
        chk = np.load(progress_path)
        final_embeddings = chk["embeddings"]
        saved_concept_ids = list(chk["concept_ids"].tolist())

    # defensive L2-normalise (sentence-transformers normalise_embeddings=True
    # should have already done this, but guard against edge cases)
    final_embeddings = _normalize(final_embeddings)
    log.info("Final matrix: %s dtype=%s", final_embeddings.shape, final_embeddings.dtype)

    dim = final_embeddings.shape[1]

    # FAISS index
    index = faiss.IndexFlatIP(dim)
    index.add(final_embeddings)

    # ---- write artefacts ---------------------------------------------------
    embeddings_path = out_dir / "embeddings.npy"
    np.save(embeddings_path, final_embeddings)
    log.info("Wrote %s", embeddings_path)

    index_path = out_dir / "index.faiss"
    faiss.write_index(index, str(index_path))
    log.info("Wrote %s", index_path)

    meta_path = out_dir / "index.faiss.meta"
    with open(meta_path, "wb") as f:
        pickle.dump(saved_concept_ids, f)
    log.info("Wrote %s (concept_ids list, %d entries)", meta_path, len(saved_concept_ids))

    metadata = {
        "model": MODEL_ID,
        "dimension": dim,
        "num_concepts": len(saved_concept_ids),
        "index_type": "IndexFlatIP",
        "text_format": TEXT_FORMAT,
        "text_rules": TEXT_RULES,
        "text_cap_chars": TEXT_CAP,
        "built_date": datetime.now(timezone.utc).isoformat(),
        "vocab_source": "vocab-data-v2",
    }
    meta_json_path = out_dir / "metadata.json"
    with open(meta_json_path, "w") as f:
        json.dump(metadata, f, indent=2)
    log.info("Wrote %s", meta_json_path)

    # remove progress checkpoint — build is complete
    if progress_path.exists():
        progress_path.unlink()
        log.info("Removed checkpoint %s", progress_path)


# ---------------------------------------------------------------------------
# Tarball packer
# ---------------------------------------------------------------------------

TARBALL_NAME = "vocab-embeddings-v2-biolord.tar.gz"
ARTEFACT_FILES = ("embeddings.npy", "index.faiss", "index.faiss.meta", "metadata.json")


def pack_tarball(out_dir: Path) -> Path:
    """Pack the four artefact files into a single .tar.gz in out_dir."""
    tarball_path = out_dir / TARBALL_NAME
    with tarfile.open(tarball_path, "w:gz") as tf:
        for fname in ARTEFACT_FILES:
            fpath = out_dir / fname
            if not fpath.exists():
                raise FileNotFoundError(f"Artefact missing: {fpath}")
            tf.add(fpath, arcname=fname)
    size_mb = tarball_path.stat().st_size / (1024 * 1024)
    log.info("Packed %s (%.1f MB)", tarball_path, size_mb)
    return tarball_path


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build BioLORD-2023 FAISS embeddings for vocab-data-v2."
    )
    parser.add_argument(
        "--vocab",
        default=os.path.expanduser("~/.cache/psdl_vocab/v2/vocabulary_final.json"),
        help="Path to vocabulary_final.json (default: ~/.cache/psdl_vocab/v2/vocabulary_final.json)",
    )
    parser.add_argument(
        "--out",
        default="/tmp/biolord_build",
        help="Output directory for artefacts (default: /tmp/biolord_build)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=256,
        help="Encode batch size (default: 256)",
    )
    args = parser.parse_args()

    vocab_path = Path(args.vocab)
    out_dir = Path(args.out)

    log.info("Loading vocabulary from %s …", vocab_path)
    with open(vocab_path) as f:
        concepts = json.load(f)
    log.info("Loaded %d concepts.", len(concepts))

    build_index(concepts, out_dir, batch_size=args.batch_size)
    pack_tarball(out_dir)


if __name__ == "__main__":
    main()
