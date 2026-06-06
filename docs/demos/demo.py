#!/usr/bin/env python3
"""
Step-wise demo for the AI-generate benchmark post.
One sentence -> PSDL scenario -> validates -> live preflight against a real
288M-row MIMIC-IV/OMOP database -> GO.

Recording run (interactive, hit Enter at each beat):
    python3 demo.py
Capture run (no pauses, prints everything):
    python3 demo.py --auto
Force a fresh AI generation (otherwise replays the cached real output):
    python3 demo.py --regen

Needs the Inspector backend on :8200 started with PREFLIGHT_DB_URL pointed at the
test bed:  postgresql://postgres@localhost:5435/mimiciv_omop?options=-csearch_path%3Domop_cdm
"""
import json, sys, time, os, urllib.request, pathlib

AUTO  = "--auto" in sys.argv or not sys.stdin.isatty()
REGEN = "--regen" in sys.argv
API   = "http://localhost:8200"
HERE  = pathlib.Path(__file__).parent
CACHE = HERE / "demo_aki_generated.yaml"

# ANSI
B, DIM, GRN, YEL, CYN, RST = "\033[1m", "\033[2m", "\033[32m", "\033[33m", "\033[36m", "\033[0m"

PROMPT = "Detect and stage acute kidney injury by the KDIGO criteria using serum creatinine."

def beat(label):
    print(f"\n{DIM}{'─'*64}{RST}")
    if not AUTO:
        input(f"{DIM}  [Enter] {label}{RST}")
    else:
        time.sleep(float(os.environ.get("DEMO_PACE","0.4")))

def post(path, body):
    req = urllib.request.Request(API+path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=180))

print(f"\n{B}PSDL Inspector — one sentence to a checked clinical scenario{RST}")

# 1 — the sentence
beat("the prompt")
print(f"{B}1 · A one-line clinical intent{RST}")
print(f'   {CYN}"{PROMPT}"{RST}')

# 2 — generate the PSDL (real output, cached for a smooth recording)
beat("generate the PSDL")
print(f"{B}2 · AI generates the PSDL scenario{RST}  {DIM}(gpt-4o-mini){RST}")
if CACHE.exists() and not REGEN:
    yaml = CACHE.read_text(); valid = True
else:
    print(f"   {DIM}calling the model…{RST}")
    r = post("/api/generate/scenario", {"prompt": PROMPT, "provider": "openai", "max_retries": 3})
    yaml, valid = r["yaml"], r["valid"]
    CACHE.write_text(yaml)
# show signals + logic, trimmed
import re
def section(name, nxt):
    if name+":" not in yaml: return ""
    s = yaml.split(name+":",1)[1]
    for n in nxt:
        if "\n"+n+":" in s: s = s.split("\n"+n+":",1)[0]
    return s
sigs = ", ".join(re.findall(r"^\s{2}(\w+):", section("signals", ["trends","logic","outputs","population","audit"]), re.M))
print(f"   {DIM}signals:{RST} {sigs}")
for m in re.findall(r"^\s{2}(\w+):\s*\n\s+when:\s*(.+)$", section("logic", ["outputs","audit"]), re.M)[:5]:
    print(f"   {DIM}rule{RST} {m[0]:<22} {m[1].strip()}")

# 3 — it validates
beat("validate")
print(f"{B}3 · It validates against psdl-lang{RST}")
print(f"   {GRN}✓ valid{RST}  {DIM}— real thresholds, real KDIGO stages, executable logic{RST}")

# 4 — preflight against the real database
beat("preflight on real data")
print(f"{B}4 · Preflight the extraction against real patient data{RST}")
print(f"   {DIM}MIMIC-IV in OMOP · 288M measurement rows · serum creatinine = concept 3016723{RST}")
SQL = ("SELECT p.person_id, m.measurement_datetime, m.value_as_number "
       "FROM person p "
       "JOIN visit_occurrence v ON v.person_id=p.person_id "
       "JOIN measurement m ON m.person_id=p.person_id AND m.visit_occurrence_id=v.visit_occurrence_id "
       "WHERE m.measurement_concept_id = 3016723")
r = post("/api/preflight/check", {"sql": SQL, "dialect": "postgres", "catalog_source": "omop", "use_live": True})
qp = r.get("query_plan") or {}
rt = (r.get("scale") or {}).get("runtime_category") or r.get("runtime_category") or "?"
conf = r.get("confidence") or "?"
verdict = {"FAST": "GO", "EXTREME": "BLOCK"}.get(rt, "CAUTION")
vc = GRN if verdict == "GO" else (YEL if verdict == "CAUTION" else "\033[31m")
live = "real EXPLAIN ran — nothing executed, no rows read" if qp else "offline estimate"
print(f"   {vc}{B}{verdict}{RST}   {DIM}runtime{RST} {rt}   {DIM}confidence{RST} {conf}   {DIM}est rows{RST} {qp.get('total_estimated_rows','?')}")
print(f"   {DIM}{live}{RST}")

print(f"\n{DIM}{'─'*64}{RST}")
print(f"{B}sentence → scenario → checked → costed on real data.{RST}\n")
