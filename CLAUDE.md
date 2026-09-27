# CONTINUUM — agent context

Palantir FDSE (USG / Delta) interview exercise for Paris Proffitt: a Foundry + AIP
project and a < 5 minute demo video, due **2026-10-05**. The project is built with
AI assistance (explicitly permitted); Paris must be able to explain every choice, so
**every change is recorded with its reasoning**.

## What the project is
DMSMS obsolescence decision intelligence. A manufacturer end-of-life notice (real:
Microchip CAAN-02OLLE763, Intel PDN2401) → part matching against notional program
BOMs → coverage / supply-gap math → calibrated demand forecast → courses of action →
the engineer (Dana) approves → Ontology Action updates state.
Programs Heron, Kite, Petrel are fictional. Scenario date 2025-06-10.

Read first: `README.md`, `DECISIONS.md` (D-01…), `docs/FOUNDRY_BUILD.md`.

## Invariants (tests pin them; the video narrates them)
Heron `A3P1000-1PQG208I`: 312 on hand, 13.8 mo coverage, 5.7 mo to LTB, 24 mo redesign,
10.2 mo gap, CRITICAL. Hybrid COA: buy 500, $1.55M, 14% shortage (18% under +5%/yr).
Petrel `A3P1000-1FGG484I` is FAMILY_ONLY (not matched). `bom_notice_matches` = 5 rows.
If a change moves any of these, say so explicitly and update README, deck and script.

## Division of labor (D-04, D-05, D-09)
Code: identity + arithmetic. ML: uncertainty (calibrated bootstrap). AIP: language
(extraction with citations, explanations, memo). Engineer: judgment. AIP never
declares a replacement compatible and never computes numbers in prose.

## Working rules
- Every meaningful change: update `DECISIONS.md` (Decision / Why / Alternative / Why
  rejected), `README.md` and `docs/FOUNDRY_BUILD.md` if affected, run `pytest`, commit
  with a clear message, push to `main`.
- Foundry names must match the README tables exactly (datasets, object types, keys).
- Never commit manufacturer PDFs, tokens, or `.env`. No employer data anywhere.
- Foundry access is via the `palantir` MCP server (see below). Prefer building in
  Foundry through it; mirror any Foundry-side code into `foundry/` in this repo.
- The design deck is a Claude Slides artifact: https://claude.ai/artifact/EL6ZbRX4M1vGhug25MaYwh
  Keep it in sync: read it with the Artifact tool, edit only the affected slides
  (`project/slides/<id>.html`), republish to that URL. Style: near-black #08090A, off-white
  #EDEDEA, grays #B8BBBF/#8B8F94, ONE signal color #FF5B1F for critical items only;
  Barlow Semi Condensed (headings, big numbers) + Barlow (body) + JetBrains Mono (labels);
  faint crosshair-grid background, corner marks and a right-edge ruler on every slide;
  illustrations are white/gray engineering wireframes (isometric parts, planforms);
  doc-ID header and page number on every slide (20 slides). Titles say plainly what the
  slide shows; no taglines.

## Definition of done (work through in order, without stopping to ask)
1. **Phase 1, data** (`docs/FOUNDRY_BUILD.md`): Python transforms in the Continuum
   project generate the raw datasets (port `generate.py` + `raw.py`) and clean them
   into `clean/`; verify every row count and the 5-row `bom_notice_matches`.
2. **Phase 2, Ontology:** all 10 object types and 11 link types from the build guide.
3. **Phase 3, logic in Foundry:** port `impact.py`, `forecast.py`, `coa.py` as
   transforms producing `impact_cases`, `review_flags`, `coas`, `tradeoff_curve`;
   numbers must equal the invariants above.
4. **AIP Logic:** `extractNoticeLines` per `docs/AIP_LOGIC.md`; score it with
   `eval_extraction.score`; compare a small and a frontier model; record real numbers.
5. **Action + app:** action type *Approve course of action* (sets Impact Case
   `status`, creates Procurement Request and Engineering Review); Workshop app for
   Dana: impact cases → Heron detail → forecast range → COAs → approve.
6. **Docs:** DECISIONS.md entry for every choice, README + build guide current,
   deck slides updated (plan, AIP evaluation numbers, screenshots described), and a
   `docs/DEMO_SCRIPT.md` under 5 minutes that matches what was actually built.
If a step is impossible with the tools available (e.g. the MCP cannot create action
types or Workshop apps), do everything around it, write exact manual steps for Paris
into `docs/MANUAL_STEPS.md`, and continue with the next step.
Stop only for irreversible actions outside this project, or credentials.

## Palantir MCP
Configured in Claude Code as server `palantir`:
`claude mcp add palantir -e FOUNDRY_TOKEN=$FOUNDRY_TOKEN -- npx -y palantir-mcp --foundry-api-url https://continuum-demo.usw-17.palantirfoundry.com`
It can modify the Ontology (object and link types, functions) and create / preview /
debug Python transforms. It cannot write Ontology data or (per docs) upload datasets;
generate notional data with a Python transform instead, and upload PDFs by hand.
