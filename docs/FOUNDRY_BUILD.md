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

### 1.5 Verify the ground truth against the official source (D-13)
- Microchip: download `CAAN-02OLLE763_Affected_CPN_06062025.csv` from the PCN portal
  (microchip.com/en-us/support/product-change-notification, search the notice ID).
- Intel: the OPN list linked from PDN2401 (cdrdv2.intel.com/v1/dl/getContent/813534).
Commit both to `data/reference/official/`; a test compares them to our lists.

## Phase 2 — Ontology (Ontology Manager)

Create object types from the `clean/` datasets (and the computed uploads):

| Object type | Dataset | Primary key | Title |
|---|---|---|---|
| Program | `programs` | `program_id` | `name` |
| Assembly | `assemblies` | `assembly_id` | `name` |
| Part | `parts` | `part_number` | `part_number` |
| BOM Line | `bom_lines` | `bom_line_id` | `part_number` |
| Inventory Position | `inventory` | `inventory_id` | `inventory_id` |
| Notice | `notices` | `notice_id` | `notice_id` |
| Notice Line | `notice_lines` | `notice_line_id` | `part_number` |
| Impact Case | `impact_cases` | `case_id` | `case_id` |
| Review Flag | `review_flags` | `flag_id` | `flag_type` |
| Course of Action | `coas` | `coa_key` | `name` |

Link types (all many-to-one, foreign key on the first object):

| From | To | Key |
|---|---|---|
| Assembly | Program | `program_id` |
| BOM Line | Assembly | `assembly_id` |
| BOM Line | Part | `part_number` |
| Inventory Position | Program | `program_id` |
| Inventory Position | Part | `part_number` |
| Notice Line | Notice | `notice_id` |
| Impact Case | Program | `program_id` |
| Impact Case | Notice | `notice_id` |
| Impact Case | Part | `part_number` |
| Review Flag | Notice | `notice_id` |
| Course of Action | Impact Case | `case_id` |

**Check:** open Heron in the object explorer and follow Program → Assembly → BOM Line → Part.

## Phase 3 — Logic in Foundry (next)
- AIP Logic: notice PDF → notice lines, scored against `notice_lines`.
- Code Repositories: port `impact.py`, `forecast.py`, `coa.py` as Python transforms.
- Action type: *Approve course of action* → set Impact Case `status`, create Procurement Request and Engineering Review.
- Workshop: Dana's app.
