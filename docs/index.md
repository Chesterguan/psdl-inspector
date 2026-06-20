# PSDL Inspector

**Describe a clinical cohort or detection rule in one sentence — get back a validated, audit-ready algorithm.**

PSDL Inspector turns plain English into a **checked clinical scenario**: a visual DAG, OMOP terminology anchoring, a checksummed *certified bundle*, and a real-database **SQL cost preflight** — without writing a line of PSDL by hand.

![One sentence → AI-generated, validated PSDL scenario → DAG → certified bundle → live preflight GO](img/aki-preflight-walkthrough.gif)

[Get started in 5 minutes](quickstart.md){ .md-button .md-button--primary }
[View on GitHub](https://github.com/Chesterguan/psdl-inspector){ .md-button }

## What you can do

- **Describe it, don't code it** — one sentence → a validated PSDL scenario, AI-generated and auto-checked against `psdl-lang`. No new syntax to learn.
- **See the logic** — an interactive DAG + semantic outline surface errors at authoring time, not at IRB review.
- **Hand it off** — a checksummed certified bundle with OMOP anchors + an IRB-ready Word doc, and a SQL preflight that reads **GO / CAUTION / BLOCK** before a query ever touches the warehouse.

## Documentation

- [**Quickstart**](quickstart.md) — zero to a certified algorithm in 5 minutes
- [**Using Inspector**](usage.md) — the wizard workflow + the anchoring-engine choice (BioLORD vs legacy)
- [**API & bundle reference**](reference.md) — REST endpoints, the certified bundle schema, MEDS preview, compatibility
- [**Architecture & scope**](architecture.md) — system design + what Inspector does and doesn't do
- [**Execution contract**](EXECUTION_CONTRACT.md) — how an execution platform consumes the certified bundle
- [**Deployment**](DEPLOYMENT.md) — Docker / Vercel / Render

!!! note "Working as a team?"
    Inspector is the free, single-user tool. A scenario **registry**, role-based review/approval, IRB templates, and SSO live in **PSDL Workbench** *(commercial)* — [request access or info](mailto:chesterfield199512@gmail.com?subject=PSDL%20Workbench%20inquiry).
