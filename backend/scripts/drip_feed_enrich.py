#!/usr/bin/env python3
"""Resumable, cost-safe drip-feed orchestrator for scope-C vocabulary enrichment.

Enriches the 563,138 scope-C OMOP concepts through the OpenAI Batch API one
token-budgeted WAVE at a time, staying under the org's 2,000,000 enqueued-token
concurrent limit. Submits ONE wave at a time and waits for it to finish before
the next, so in-flight tokens never exceed a single wave's budget.

COST SAFETY (this is an unattended loop spending real money):
  - Submit EXACTLY ONCE per wave. The batch_id + submitted_at are written to the
    manifest IMMEDIATELY after batches.create() returns, before any polling, so a
    crash can never lose a batch_id or cause a double-submit.
  - Resume from the manifest: a wave with a batch_id is polled, never re-submitted;
    a "done" wave is skipped entirely (never re-downloaded).
  - FAIL-STOP: if any wave ends failed / expired / cancelled, record it and STOP
    THE ENTIRE LOOP (exit non-zero). A systematic failure must never burn money
    across hundreds of waves.

Build reuses the validated request-building logic + FIXED enrichment prompt from
enrich_vocabulary.prepare_batch_requests (medication category + drug-abbreviation
constraint), so every request matches the validated prompt.

Usage:
    # Prove the chunking + safety math without spending a cent:
    python scripts/drip_feed_enrich.py --dry-run

    # Launch the real run (submits batches, spends money):
    python scripts/drip_feed_enrich.py            # 'run' is the default mode

Re-running `run` is idempotent: it picks up exactly where the manifest left off.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# --- SSL / CA bundle: the system Python 3.9 has a broken CA store. The openai
# SDK (httpx) usually handles its own SSL, but be defensive: point the standard
# CA env vars at certifi's bundle if they are not already set. This mirrors the
# certifi pattern used elsewhere in the codebase for the download path. -------
try:
    import certifi

    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
except Exception:  # certifi optional; SDK may still work without it
    pass

# Reuse the validated request-building logic + FIXED prompt from the existing
# enrichment pipeline so each request matches the validated prompt exactly.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from enrich_vocabulary import ENRICHMENT_PROMPT  # noqa: E402

# --------------------------------------------------------------------------- #
# Paths (all relative to the backend/ working directory, matching submit_scope_c)
# --------------------------------------------------------------------------- #
BATCH_DIR = "data/vocabulary/batch"
WAVES_DIR = os.path.join(BATCH_DIR, "waves")
RESULTS_DIR = os.path.join(BATCH_DIR, "results")
MANIFEST = os.path.join(BATCH_DIR, "drip_manifest.json")
LOG_FILE = os.path.join(BATCH_DIR, "drip.log")
LOCK_FILE = os.path.join(BATCH_DIR, "drip.lock")

# Single-instance guard. Held open for the process lifetime; the OS releases
# the flock automatically when the process exits (even on crash/kill), so there
# is never a stale lock. Prevents two orchestrators racing → double-submit/spend.
_lock_fh = None


def _acquire_singleton_lock() -> bool:
    """Return True if we got the exclusive lock; False if another instance holds it."""
    global _lock_fh
    os.makedirs(BATCH_DIR, exist_ok=True)
    _lock_fh = open(LOCK_FILE, "w")
    try:
        fcntl.flock(_lock_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    _lock_fh.write(f"{os.getpid()}\n")
    _lock_fh.flush()
    return True
CONCEPTS_PATH = "data/vocabulary/extracted/scope_c_concepts.json"

# --------------------------------------------------------------------------- #
# Token + cost math
# --------------------------------------------------------------------------- #
# Each request enqueues ~= input_tokens + reserved max_output (max_tokens=500).
RESERVED_OUTPUT_TOKENS = 500
# Conservative fallback per-request input estimate when tiktoken is unavailable.
# Task spec: ~515 input + 500 reserved = ~1,015 enqueued tokens/request.
FALLBACK_INPUT_TOKENS = 515
# Org concurrent enqueued-token limit is 2,000,000. We submit ONE wave at a time
# and wait for it to finish, so peak in-flight tokens == one wave's est_tokens.
# Use a safety budget well under the hard limit.
TOKEN_BUDGET_PER_WAVE = 1_700_000

# gpt-4o-mini Batch API pricing (50% batch discount already applied):
PRICE_INPUT_PER_1M = 0.075   # USD per 1M input tokens
PRICE_OUTPUT_PER_1M = 0.30   # USD per 1M output tokens
# Observed average actual output tokens/concept from the earlier sample.
EST_OUTPUT_TOKENS_PER_CONCEPT = 75

POLL_INTERVAL_SECONDS = 60
TERMINAL_OK = {"completed"}
TERMINAL_BAD = {"failed", "expired", "cancelled", "cancelling"}


# --------------------------------------------------------------------------- #
# Small utilities
# --------------------------------------------------------------------------- #
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(msg: str) -> None:
    """Append a timestamped line to drip.log and echo to stdout (tail-friendly)."""
    line = f"{now_iso()} {msg}"
    print(line, flush=True)
    os.makedirs(BATCH_DIR, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def get_api_key() -> str | None:
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    try:
        from dotenv import dotenv_values

        return dotenv_values(".env").get("OPENAI_API_KEY")
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Token estimation
# --------------------------------------------------------------------------- #
def build_request(concept: dict) -> dict:
    """Build a single batch request matching enrich_vocabulary.prepare_batch_requests.

    Globally-unique custom_id = concept_<concept_id>.
    """
    synonyms_str = ", ".join(concept["synonyms"][:10]) if concept.get("synonyms") else "None"
    prompt = ENRICHMENT_PROMPT.format(
        concept_name=concept["concept_name"],
        domain_id=concept["domain_id"],
        vocabulary_id=concept["vocabulary_id"],
        concept_code=concept["concept_code"],
        concept_class_id=concept["concept_class_id"],
        synonyms=synonyms_str,
    )
    return {
        "custom_id": f"concept_{concept['concept_id']}",
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a clinical terminology expert. Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": 500,
            "temperature": 0.1,
        },
    }


def _load_encoder():
    """Return a tiktoken encoder for gpt-4o-mini, or None if tiktoken is absent."""
    try:
        import tiktoken
    except Exception:
        return None
    try:
        return tiktoken.encoding_for_model("gpt-4o-mini")
    except Exception:
        try:
            return tiktoken.get_encoding("o200k_base")
        except Exception:
            return None


def estimate_input_tokens(request: dict, encoder) -> int:
    """Estimate enqueued INPUT tokens for one request.

    With tiktoken: count the message text + small per-message overhead.
    Without tiktoken: fall back to the conservative constant.
    """
    if encoder is None:
        return FALLBACK_INPUT_TOKENS
    total = 0
    for msg in request["body"]["messages"]:
        # +4 tokens/message is the standard chat-format overhead approximation.
        total += len(encoder.encode(msg["content"])) + 4
    total += 3  # priming for the assistant reply
    return total


def measure_per_request_input_tokens(concepts: list[dict], encoder, sample: int = 200) -> float:
    """Measure the average INPUT tokens/request across a sample of real requests.

    Returns the conservative fallback when tiktoken is unavailable. We use the
    MAX-side (a small +5% margin on the measured mean) to size waves safely.
    """
    if encoder is None:
        log(f"tiktoken unavailable -> using conservative fallback {FALLBACK_INPUT_TOKENS} input tokens/request")
        return float(FALLBACK_INPUT_TOKENS)
    n = min(sample, len(concepts))
    # Sample evenly across the dataset (names vary a lot in length).
    step = max(1, len(concepts) // n)
    counts = [estimate_input_tokens(build_request(concepts[i]), encoder) for i in range(0, len(concepts), step)][:n]
    mean = sum(counts) / len(counts)
    p_max = max(counts)
    log(f"measured input tokens over {len(counts)} sampled requests: mean={mean:.1f} max={p_max} (tiktoken)")
    # Size with a 5% margin over the mean so a wave's real enqueue stays under budget.
    return mean * 1.05


def per_request_enqueued_tokens(input_tokens_per_req: float) -> float:
    return input_tokens_per_req + RESERVED_OUTPUT_TOKENS


def wave_size(input_tokens_per_req: float) -> int:
    """Largest N s.t. N * per_request_enqueued_tokens <= TOKEN_BUDGET_PER_WAVE."""
    per = per_request_enqueued_tokens(input_tokens_per_req)
    n = int(TOKEN_BUDGET_PER_WAVE // per)
    if n < 1:
        raise RuntimeError(f"per-request tokens ({per}) exceed wave budget {TOKEN_BUDGET_PER_WAVE}")
    return n


def est_cost_usd(request_count: int, input_tokens_per_req: float) -> float:
    """Estimated USD cost for `request_count` requests at batch pricing."""
    input_cost = request_count * input_tokens_per_req / 1_000_000 * PRICE_INPUT_PER_1M
    output_cost = request_count * EST_OUTPUT_TOKENS_PER_CONCEPT / 1_000_000 * PRICE_OUTPUT_PER_1M
    return input_cost + output_cost


# --------------------------------------------------------------------------- #
# Wave files + manifest
# --------------------------------------------------------------------------- #
def write_wave_files(concepts: list[dict], n_per_wave: int, input_tokens_per_req: float) -> list[dict]:
    """Re-chunk concepts into wave_XXXX.jsonl files. Returns wave records.

    Idempotent: only (re)writes a wave file if it is missing or has the wrong
    line count, so an interrupted re-chunk can be resumed and existing waves are
    not disturbed.
    """
    os.makedirs(WAVES_DIR, exist_ok=True)
    waves: list[dict] = []
    total = len(concepts)
    n_waves = (total + n_per_wave - 1) // n_per_wave
    per_enq = per_request_enqueued_tokens(input_tokens_per_req)

    for w in range(n_waves):
        start = w * n_per_wave
        chunk = concepts[start:start + n_per_wave]
        wave_id = w + 1
        wave_name = f"wave_{wave_id:04d}.jsonl"
        wave_path = os.path.join(WAVES_DIR, wave_name)
        est_tokens = int(round(len(chunk) * per_enq))

        need_write = True
        if os.path.exists(wave_path):
            with open(wave_path) as f:
                existing_lines = sum(1 for _ in f)
            if existing_lines == len(chunk):
                need_write = False
        if need_write:
            tmp = wave_path + ".tmp"
            with open(tmp, "w") as f:
                for concept in chunk:
                    f.write(json.dumps(build_request(concept)) + "\n")
            os.replace(tmp, wave_path)

        waves.append(
            {
                "wave_id": wave_id,
                "wave_file": os.path.join("waves", wave_name),
                "request_count": len(chunk),
                "est_tokens": est_tokens,
                "batch_id": None,
                "status": "pending",
                "submitted_at": None,
                "completed_at": None,
                "output_file": None,
                "result_count": None,
                "error": None,
            }
        )
    return waves


def load_manifest() -> dict | None:
    if os.path.exists(MANIFEST):
        with open(MANIFEST) as f:
            return json.load(f)
    return None


def save_manifest(m: dict) -> None:
    """Atomic manifest write (tmp + os.replace) — the single source of truth."""
    m["updated_at"] = now_iso()
    os.makedirs(BATCH_DIR, exist_ok=True)
    tmp = MANIFEST + ".tmp"
    with open(tmp, "w") as f:
        json.dump(m, f, indent=2)
    os.replace(tmp, MANIFEST)


def build_or_load_manifest(concepts: list[dict], input_tokens_per_req: float, dry_run: bool) -> dict:
    """Load an existing manifest, else build a fresh one (and write wave files).

    On dry-run with no manifest we still compute the plan but DO NOT write the
    manifest file (so a dry-run never mutates the resume source of truth). We do
    write wave files in dry-run is avoided too — dry-run is purely a math proof.
    """
    existing = load_manifest()
    if existing is not None:
        # Re-attach the live per-request estimate for cost printing if missing.
        existing.setdefault("input_tokens_per_request", input_tokens_per_req)
        return existing

    n_per_wave = wave_size(input_tokens_per_req)
    if dry_run:
        # Compute the plan in-memory without touching disk.
        total = len(concepts)
        n_waves = (total + n_per_wave - 1) // n_per_wave
        per_enq = per_request_enqueued_tokens(input_tokens_per_req)
        waves = []
        for w in range(n_waves):
            start = w * n_per_wave
            cnt = min(n_per_wave, total - start)
            waves.append(
                {
                    "wave_id": w + 1,
                    "wave_file": os.path.join("waves", f"wave_{w + 1:04d}.jsonl"),
                    "request_count": cnt,
                    "est_tokens": int(round(cnt * per_enq)),
                    "batch_id": None,
                    "status": "pending",
                    "submitted_at": None,
                    "completed_at": None,
                    "output_file": None,
                    "result_count": None,
                    "error": None,
                }
            )
    else:
        waves = write_wave_files(concepts, n_per_wave, input_tokens_per_req)

    manifest = {
        "description": "PSDL Inspector scope-C drip-feed enrichment (token-budgeted waves)",
        "model": "gpt-4o-mini",
        "endpoint": "/v1/chat/completions",
        "completion_window": "24h",
        "source_extract": CONCEPTS_PATH,
        "total_requests": sum(w["request_count"] for w in waves),
        "wave_size": n_per_wave,
        "token_budget_per_wave": TOKEN_BUDGET_PER_WAVE,
        "input_tokens_per_request": input_tokens_per_req,
        "reserved_output_tokens": RESERVED_OUTPUT_TOKENS,
        "created_at": now_iso(),
        "waves": waves,
    }
    if not dry_run:
        save_manifest(manifest)
    return manifest


# --------------------------------------------------------------------------- #
# Dry-run
# --------------------------------------------------------------------------- #
def do_dry_run(manifest: dict, input_tokens_per_req: float) -> int:
    waves = manifest["waves"]
    total_requests = sum(w["request_count"] for w in waves)
    n_waves = len(waves)
    max_wave_tokens = max(w["est_tokens"] for w in waves)
    per_enq = per_request_enqueued_tokens(input_tokens_per_req)

    log("=== DRY-RUN: chunking + safety math (NO spend, NO API calls) ===")
    for w in waves:
        cost = est_cost_usd(w["request_count"], input_tokens_per_req)
        log(
            f"WOULD submit wave {w['wave_id']}/{n_waves}: "
            f"{w['request_count']} requests, ~{w['est_tokens']:,} tokens, ~${cost:.4f}"
        )

    total_cost = est_cost_usd(total_requests, input_tokens_per_req)
    log("--- DRY-RUN SUMMARY ---")
    log(f"total waves:            {n_waves}")
    log(f"total requests:         {total_requests:,}")
    log(f"input tokens/request:   {input_tokens_per_req:.1f} (enqueued/request ~= {per_enq:.1f})")
    log(f"max per-wave tokens:    {max_wave_tokens:,}  (budget {TOKEN_BUDGET_PER_WAVE:,})")
    log(f"total estimated cost:   ${total_cost:.2f}")

    ok = True
    if total_requests != len(_loaded_concepts):
        log(f"!! CHECK FAILED: total requests {total_requests:,} != concepts {len(_loaded_concepts):,}")
        ok = False
    else:
        log(f"CHECK OK: total requests == {total_requests:,} concepts")
    if max_wave_tokens > TOKEN_BUDGET_PER_WAVE:
        log(f"!! CHECK FAILED: max per-wave tokens {max_wave_tokens:,} > budget {TOKEN_BUDGET_PER_WAVE:,}")
        ok = False
    else:
        log(f"CHECK OK: max per-wave tokens {max_wave_tokens:,} <= budget {TOKEN_BUDGET_PER_WAVE:,}")
    if max_wave_tokens > 2_000_000:
        log("!! CHECK FAILED: max per-wave tokens exceed the 2,000,000 hard limit")
        ok = False

    log("=== DRY-RUN COMPLETE — no batches submitted, zero spend ===")
    return 0 if ok else 1


# --------------------------------------------------------------------------- #
# Real run
# --------------------------------------------------------------------------- #
def make_client():
    from openai import OpenAI

    api_key = get_api_key()
    if not api_key:
        sys.exit("FATAL: OPENAI_API_KEY not found in env or backend/.env")
    return OpenAI(api_key=api_key)


def poll_to_terminal(client, batch_id: str, n_waves: int, wave_id: int):
    """Poll a batch every POLL_INTERVAL_SECONDS until it reaches a terminal state."""
    while True:
        batch = client.batches.retrieve(batch_id)
        rc = batch.request_counts
        log(
            f"WAVE {wave_id}/{n_waves} polling {batch_id}: status={batch.status} "
            f"({rc.completed}/{rc.total} done, {rc.failed} failed)"
        )
        if batch.status in TERMINAL_OK or batch.status in TERMINAL_BAD:
            return batch
        time.sleep(POLL_INTERVAL_SECONDS)


def do_run(manifest: dict, input_tokens_per_req: float) -> int:
    client = make_client()
    waves = manifest["waves"]
    n_waves = len(waves)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    log(f"=== RUN: {n_waves} waves, {manifest['total_requests']:,} total requests ===")

    for w in waves:
        wid = w["wave_id"]

        # 1) Already finished — skip, never re-download.
        if w["status"] == "done":
            log(f"WAVE {wid}/{n_waves} skip (already done, {w.get('result_count')} results)")
            continue

        # 2) Already submitted (has batch_id) but not terminal — poll, never re-submit.
        if w.get("batch_id"):
            log(f"WAVE {wid}/{n_waves} resume polling existing batch {w['batch_id']}")
            batch = poll_to_terminal(client, w["batch_id"], n_waves, wid)
        else:
            # 3) Not yet submitted — SUBMIT EXACTLY ONCE.
            wave_path = os.path.join(BATCH_DIR, w["wave_file"])
            est = est_cost_usd(w["request_count"], input_tokens_per_req)
            log(f"WAVE {wid}/{n_waves} uploading {w['wave_file']} ({w['request_count']} reqs)...")
            with open(wave_path, "rb") as f:
                up = client.files.create(file=f, purpose="batch")
            batch = client.batches.create(
                input_file_id=up.id,
                endpoint="/v1/chat/completions",
                completion_window="24h",
                metadata={"description": "PSDL scope-C drip enrichment", "wave": str(wid)},
            )
            # CRITICAL: persist batch_id + submitted_at IMMEDIATELY, before polling,
            # so a crash can never lose the id or cause a double-submit on resume.
            w["batch_id"] = batch.id
            w["submitted_at"] = now_iso()
            w["status"] = "submitted"
            save_manifest(manifest)
            log(
                f"WAVE {wid}/{n_waves} submitted {batch.id} "
                f"({w['request_count']} reqs, ~{w['est_tokens']:,} tokens, ~${est:.4f})"
            )
            batch = poll_to_terminal(client, batch.id, n_waves, wid)

        # 4) Terminal handling.
        if batch.status in TERMINAL_OK:
            if not batch.output_file_id:
                w["status"] = "failed"
                w["error"] = "completed but no output_file_id"
                save_manifest(manifest)
                log(f"WAVE {wid}/{n_waves} ERROR: completed without output_file_id — STOPPING")
                return 2
            out_name = f"wave_{wid:04d}_out.jsonl"
            out_path = os.path.join(RESULTS_DIR, out_name)
            content = client.files.content(batch.output_file_id)
            with open(out_path, "wb") as f:
                f.write(content.read())
            with open(out_path) as f:
                result_count = sum(1 for _ in f)
            w["status"] = "done"
            w["completed_at"] = now_iso()
            w["output_file"] = os.path.join("results", out_name)
            w["result_count"] = result_count
            save_manifest(manifest)
            log(f"WAVE {wid}/{n_waves} done ({result_count} results -> {w['output_file']})")
        else:
            # FAIL-STOP: failed / expired / cancelled — record and HALT the loop.
            w["status"] = batch.status
            w["error"] = f"terminal status={batch.status}"
            if getattr(batch, "errors", None):
                try:
                    w["error"] += f"; {batch.errors}"
                except Exception:
                    pass
            save_manifest(manifest)
            log(
                f"WAVE {wid}/{n_waves} FAILED (status={batch.status}). "
                f"STOPPING ENTIRE LOOP to prevent runaway spend across remaining waves."
            )
            return 3

    done = sum(1 for w in waves if w["status"] == "done")
    total_results = sum(w.get("result_count") or 0 for w in waves)
    log(f"=== RUN COMPLETE: {done}/{n_waves} waves done, {total_results:,} total results ===")
    return 0


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
_loaded_concepts: list[dict] = []


def main() -> int:
    global _loaded_concepts

    parser = argparse.ArgumentParser(description="Drip-feed scope-C enrichment orchestrator")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute + print chunking and safety math without any API call or spend",
    )
    args = parser.parse_args()

    if not os.path.exists(CONCEPTS_PATH):
        sys.exit(f"FATAL: concepts extract not found at {CONCEPTS_PATH} (run from backend/)")

    log(f"loading concepts from {CONCEPTS_PATH} ...")
    with open(CONCEPTS_PATH) as f:
        _loaded_concepts = json.load(f)
    log(f"loaded {len(_loaded_concepts):,} concepts")

    encoder = _load_encoder()
    input_tokens_per_req = measure_per_request_input_tokens(_loaded_concepts, encoder)

    manifest = build_or_load_manifest(_loaded_concepts, input_tokens_per_req, dry_run=args.dry_run)
    # Use the manifest's stored per-request estimate so resume + cost math are
    # consistent with how the waves were originally sized.
    input_tokens_per_req = manifest.get("input_tokens_per_request", input_tokens_per_req)

    if args.dry_run:
        return do_dry_run(manifest, input_tokens_per_req)

    # Single-instance guard before any spend: if another orchestrator is live,
    # stop cleanly (exit 0) so a duplicate supervisor doesn't restart-loop.
    if not _acquire_singleton_lock():
        log("another drip_feed instance holds the lock — exiting without doing work")
        return 0
    return do_run(manifest, input_tokens_per_req)


if __name__ == "__main__":
    sys.exit(main())
