# Quickstart — one sentence to a certified algorithm in 5 minutes

This gets you from zero to a **validated, audit-ready clinical algorithm** without writing any PSDL by hand. For the full feature tour see the [README](README.md).

## 1. Run it (2 min)

```bash
git clone https://github.com/Chesterguan/psdl-inspector.git
cd psdl-inspector && docker compose up        # → http://localhost:9806
```

The image bundles the OMOP vocabulary (~1GB), so the **first** build takes a few minutes. When the logs settle, open **http://localhost:9806**.

> No Docker? Jump to [Local setup](#local-setup-for-contributors) below.

## 2. Turn on AI generation (1 min, optional but recommended)

The "Generate" mode needs a model. Pick one:

```bash
# Option A — OpenAI (easiest)
cp .env.example .env          # then set OPENAI_API_KEY=sk-...
docker compose up             # restart to pick up the key

# Option B — local, private, no key
brew install ollama && ollama serve && ollama pull mistral-small
```

No model configured? You can still **Build** (visual builder) or **Edit** (paste YAML) — skip to step 3 and use the Editor mode with the built-in template.

## 3. Generate a scenario (1 min)

1. Open the app → **Generate** tab.
2. Paste a clinical sentence, e.g.:

   > *Detect and stage acute kidney injury by the KDIGO criteria using serum creatinine.*

3. Click **Generate**. Inspector calls the model, validates the result against `psdl-lang`, and retries automatically until it passes. You get a checked PSDL scenario — signals, trends, and severity-staged logic.

## 4. See it, certify it (1 min)

- **Preview** → the **DAG** shows the logic as a graph (signal → trend → rule); the **Outline** lists it as a tree. This is where you catch a wrong threshold *before* IRB review, not after.
- **Export** → **Certified Bundle** produces a checksummed JSON with OMOP terminology anchors (creatinine → LOINC `2160-0`), plus an **IRB-ready Word doc**.

That's the loop: **sentence → scenario → checked → certified.** 🎉

## 5. (Optional) Preflight the extraction

The **Prepare** step estimates what your extraction would cost *before* it touches a warehouse — **GO / CAUTION / BLOCK**. It's offline by default. To run a real `EXPLAIN` against your **own local** database (metadata only — it never executes the query or reads a patient row):

```bash
# set on the backend, then restart
export PREFLIGHT_DB_URL="postgresql://user:pass@localhost:5432/yourdb"
```

A "Live plan (local DB)" toggle appears in the Preflight panel.

---

## What's next

- **Reproduce the demos** — [`docs/demos/`](docs/demos/) ships two full scenarios (sepsis, T2D nephropathy) with narrator cue sheets.
- **Self-host** — see the [Deployment Guide](docs/DEPLOYMENT.md) (Vercel / Render / Docker).
- **Working as a team?** Inspector is single-user. A scenario **registry**, role-based review/approval, IRB templates, and SSO live in **PSDL Workbench** *(commercial)* — [request access or info](mailto:chesterfield199512@gmail.com?subject=PSDL%20Workbench%20inquiry).

## Local setup (for contributors)

Prefer running the services directly instead of Docker:

```bash
# Backend  → http://localhost:8200
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install psdl-lang --upgrade          # Inspector always tracks the latest psdl-lang
uvicorn app.main:app --reload --port 8200

# Frontend → http://localhost:9806  (new terminal)
cd frontend
npm install
npm run dev
```

Confirm the backend is healthy: `curl -s http://localhost:8200/api/version` → `{"inspector": "0.2.0", "psdl_lang": "0.4.x"}`.

Contribution guidelines: [CONTRIBUTING.md](CONTRIBUTING.md).
