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
- The design deck is a Claude artifact (Slides); the main Claude conversation keeps it
  updated. Note deck-relevant changes in the commit message so they can be reflected.

## Palantir MCP
Configured in Claude Code as server `palantir`:
`claude mcp add palantir -e FOUNDRY_TOKEN=$FOUNDRY_TOKEN -- npx -y palantir-mcp --foundry-api-url https://<your-host>.palantirfoundry.com`
It can modify the Ontology (object and link types, functions) and create / preview /
debug Python transforms. It cannot write Ontology data or (per docs) upload datasets;
generate notional data with a Python transform instead, and upload PDFs by hand.
