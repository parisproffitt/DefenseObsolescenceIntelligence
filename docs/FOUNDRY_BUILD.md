# Foundry Build Guide

Exact build steps for CONTINUUM in Foundry + AIP. Names here match the README and
DECISIONS.md, so the platform, the code and the docs stay aligned.
Foundry UI labels change over time: if a transform isn't where described, search
the transform picker for the key word (e.g. "trim", "regex", "join").

## Phase 1 — Raw data in, clean data out (Python transforms) — BUILT

Built through the Palantir MCP (D-15, D-16). Code: Foundry repository
`continuum-transforms` (`ri.stemma.main.repository.0a93c76c-9a57-4738-8165-833990fa1b0c`),
mirrored in [`foundry/continuum-transforms/`](../foundry/continuum-transforms). The
`myproject/continuum/` package in that repository is a verbatim copy of `src/continuum/`.

### 1.1 Folders in the `Continuum` project (created by the transforms' output paths)
`raw/` · `clean/` · `analysis/` · `aip/` · `ontology/`

### 1.2 `raw/`: what the program office hands over
| Dataset | Made by | What's in it |
|---|---|---|
| `raw_programs`, `raw_bom_export`, `raw_parts_master`, `raw_inventory`, `raw_demand_history` | `raw_exports.py` (ports `generate.py` + `raw.py`, seed 7) | One CSV file each, as a file drop: spreadsheet headers, padded / lower-case part numbers, a Digi-Key `-ND` suffix, `MM/dd/yyyy` and `dd-MMM-yyyy` text dates, `$1,234.00` text costs |
| `raw_notices` | uploaded (`data/notices/notices.csv`) | Notice registry, all columns as text |
| `raw_notice_parts` | uploaded (`data/reference/*_affected_parts.csv`) | The 230 real affected OPNs: ground truth (D-13) |
| `raw_notice_text` | uploaded (text layer of the two notice PDFs, one row per page) | Input to the AIP extraction (step 4). The PDFs themselves are not in the repo |

### 1.3 `clean/`: keyed, typed tables (`clean.py`)
Every part number goes through `partnumbers.normalize()` (trim, upper-case, drop
`-ND`/`-CT`/`-TR`/`-DKR`), the same function the matching uses. Every output declares
its primary key as a FAIL check.

| Output | From | Key |
|---|---|---|
| `programs` | `raw_programs` | `program_id` |
| `assemblies` | `raw_bom_export` (distinct assemblies) | `assembly_id` |
| `parts` | `raw_parts_master` | `part_number` |
| `bom_lines` | `raw_bom_export` (`bom_line_id = Assy No. + "-" + 2-digit Line`) | `bom_line_id` |
| `inventory` | `raw_inventory` (`inventory_id = INV-<program>-<part>`) | `inventory_id` |
| `demand_monthly` | `raw_demand_history` | (dataset only) |
| `notices` | `raw_notices` | `notice_id` |
| `notice_lines` | `raw_notice_parts` (`notice_line_id = notice_id|part_number`) | `notice_line_id` |
| `bom_notice_matches` | `bom_lines` ⋈ `notice_lines` on `part_number` (**inner join**: D-04 as a visible join) | `match_id` |

**Verified in Foundry by SQL (2026-09-26):** programs 3 · assemblies 7 · parts 12 ·
bom_lines 13 · inventory 13 · demand_monthly 936 (4,690 units) · notices 7 ·
notice_lines 230 · **bom_notice_matches 5**. Petrel's `M1A3P400-1PQG208I-ND` is in the
matches (suffix stripped); Heron's `"  a3p250-pqg208i "` too (padding and case);
Petrel's `A3P1000-1FGG484I` is not.

### 1.4 Screenshot for the video/deck
The lineage graph (raw → clean → analysis) and the `bom_notice_matches` preview.

### 1.5 Verify the ground truth (D-13, D-20) — DONE against the notices
`python scripts/verify_ground_truth.py <raw_notice_text.csv>` checks the key against the
notices' text in both directions: CAAN-02OLLE763 110/110; PDN2401 120/120 parts and 100/100
replacements; no OPN in the text is missing from the key. Optional extra: the
manufacturers' separate parts files (manual, `docs/MANUAL_STEPS.md` step 5; both sites
block scripted downloads).

## Phase 2 — Ontology — BUILT (on a branch; merge is manual)

Built through the MCP on global branch `continuum-ontology`; the exact ids, API names
and datasets are in [`foundry/ONTOLOGY.md`](../foundry/ONTOLOGY.md) (D-17).

| Object type | Dataset | Primary key | Title |
|---|---|---|---|
| Program | `clean/programs` | `program_id` | `name` |
| Assembly | `clean/assemblies` | `assembly_id` | `name` |
| Part | `clean/parts` | `part_number` | `part_number` |
| BOM Line | `clean/bom_lines` | `bom_line_id` | `part_number` |
| Inventory Position | `clean/inventory` | `inventory_id` | `inventory_id` |
| Notice | `clean/notices` | `notice_id` | `notice_id` |
| Notice Line | `clean/notice_lines` | `notice_line_id` | `part_number` |
| Impact Case | `analysis/impact_cases` | `case_id` | `title` |
| Review Flag | `analysis/review_flags` | `flag_id` | `flag_type` |
| Course of Action | `analysis/coas` | `coa_key` | `name` |

Link types (all one-to-many, foreign key on the first object): Assembly → Program,
BOM Line → Assembly, BOM Line → Part, Inventory Position → Program, Inventory
Position → Part, Notice Line → Notice, Impact Case → Program, Impact Case → Notice,
Impact Case → Part, Review Flag → Notice, **Review Flag → Program, Review Flag → Part**
(the last two added so the README's link list holds), Course of Action → Impact Case;
and for the approve action (D-18): Procurement Request → Impact Case, Engineering Review →
Impact Case, backed by the empty typed datasets `ontology/procurement_requests` and
`ontology/engineering_reviews` (`writeback.py`). Action type *Approve course of action*
created with its core rule; the rest is `docs/MANUAL_STEPS.md` step 3.

**Manual:** approve the branch's proposal (`docs/MANUAL_STEPS.md`). **Check:** open
Heron in Object Explorer and follow Program → Assembly → BOM Line → Part.

## Phase 3 — Decision logic in Foundry — BUILT

`analysis.py` runs the reference modules unchanged (`impact.py`, `forecast.py`,
`coa.py`), reading only the clean tables:

| Transform | Outputs (`analysis/`) |
|---|---|
| `impact` | `impact_cases` (5; plus `status = OPEN`, a readable `title`, and P10/P50/P90 demand over each case's redesign window), `review_flags` (2) |
| `courses_of_action` | `coas` (3 per CRITICAL case) and `tradeoff_curve` (81 rows per case) |
| `forecast_evaluation` | `backtest_summary`, `calibration_table` (D-07, held-out origins) |

**Verified in Foundry by SQL (2026-09-26):** Heron `A3P1000-1PQG208I`: 312 on hand,
13.8 mo coverage, 5.7 mo to LTB, 24 mo redesign, 10.2 mo gap, CRITICAL. COAs:
life-of-type 5,640 / $1,525,140 / 9.8% / 99.15%; redesign only 0 / $1,450,000 / 92.9% /
94.3%; **hybrid 500 / $1,550,011 / 14.25% / 18.15%**, identical to the reference run.
Heron's forecast range over the 24-month window is P10 337, P50 573, P90 880 units.

## Phase 3b — Autonomous intake (D-23, D-25) — PARTLY BUILT
| Dataset | Made by | State |
|---|---|---|
| `raw/notice_releases` | uploaded (notice_id, released_at); CAAN-02OLLE763 only | Built |
| `raw/notice_inbox` | `intake.py`: `raw_notice_text` filtered to released notices | Built |
| `aip/notice_lines_auto`, `aip/notice_lines_accepted`, `aip/notice_lines_rejected`, `aip/notice_intake_status`, `clean/notice_lines_live` | `pending/intake_aip.py` (Claude Sonnet, **document mode** per the D-26 results, `gate.py`) | Written and tested locally; deploy is the next step |

`analysis/impact` keeps reading `clean/notice_lines` until the live lines pass the D-25 checks.

## Phase 4 — AIP, Action, app
See `docs/AIP_LOGIC.md` (extraction and its evaluation) and `docs/MANUAL_STEPS.md`.

AIP appears at three points (D-21):
1. **`extractNoticeLines`** (AIP Logic): notice text → Notice Line rows with verbatim quotes. MANUAL_STEPS 2d.
2. **Model comparison** (language models in the `aip_extraction.py` transform): small vs frontier, scored against the 230-part key. MANUAL_STEPS 2a–2c.
3. **`draftDecisionMemo`** (AIP Logic): Impact Case + Courses of Action → memo in Workshop beside *Approve*; numbers checked by `continuum.memo.unsupported_numbers`. MANUAL_STEPS 4a.

The Action's create rules and the Workshop module are MANUAL_STEPS 3 and 4.

## Phase 5 — Autonomous intake (D-23)
See `docs/AUTOMATION.md`. Datasets: `raw/notice_inbox`, `aip/notice_lines_auto`,
`aip/notice_lines_accepted`, `aip/notice_lines_rejected`, `aip/notice_intake_status`.
Gate logic: `continuum/gate.py` (tested). Schedule and Automate rule: MANUAL_STEPS 6.

