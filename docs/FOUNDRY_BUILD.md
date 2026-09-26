# Foundry Build Guide

Exact build steps for CONTINUUM in Foundry + AIP. Names here match the README and
DECISIONS.md, so the platform, the code and the docs stay aligned.
Foundry UI labels change over time: if a transform isn't where described, search
the transform picker for the key word (e.g. "trim", "regex", "join").

## Phase 1 — Raw data in, clean data out (Pipeline Builder)

### 1.1 Folders in the `Continuum` project
`raw/` · `notices/` · `clean/` · `ontology/` · `apps/`

### 1.2 Upload to `raw/` (New → Upload files → import as datasets)
From `output/raw/`:

| File | What's messy about it |
|---|---|
| `raw_programs.csv` | Spreadsheet headers; `Planned EOS` as `MM/dd/yyyy` text |
| `raw_bom_export.csv` | Part numbers padded, lower-case, one with a Digi-Key `-ND` suffix |
| `raw_parts_master.csv` | `Unit Cost` as `$1,234.00` text |
| `raw_inventory.csv` | Lower-case part numbers; `As Of` as `10-Jun-2025` |
| `raw_demand_history.csv` | `Period` as `2025-05` text |

From `output/` (computed by the reference implementation; moved into Foundry
transforms in Phase 3): `notices.csv`, `notice_lines.csv`, `impact_cases.csv`,
`review_flags.csv`, `coas.csv`, `tradeoff_curve.csv`, `backtest_summary.csv`.

To `notices/`: the two notice PDFs (links in `data/notices/notices.csv`) and the
manufacturers' official parts lists (see §1.5).

### 1.3 Pipeline `continuum_clean` (New → Pipeline Builder → batch pipeline)
Add the five `raw_*` datasets. Build these paths, each ending in an output in `clean/`:

**Part-number cleaning — the same three steps on every `Part No.` column** (this is `partnumbers.normalize`):
1. Trim whitespace
2. Upper case
3. Regex replace `(-ND|-CT|-TR|-DKR)$` → *(empty)*

| Output | From | Steps |
|---|---|---|
| `programs` | `raw_programs` | Rename columns → `program_id, name, description, platform_type, fleet_size, end_of_support, redesign_lead_time_months, redesign_nre_usd`; parse `end_of_support` with format `MM/dd/yyyy`; cast lead time to integer, NRE to double |
| `bom_lines` | `raw_bom_export` | Part-number cleaning into `part_number`; keep the original as `part_number_as_entered`; `bom_line_id = concat(Assy No., "-", lpad(Line, 2, "0"))`; rename `Assy No.→assembly_id`, `Program→program_id`, `Qty/Assy→qty_per_assembly` |
| `assemblies` | `raw_bom_export` | Select `Assy No., Program, Assy Name` → drop duplicates → rename to `assembly_id, program_id, name` |
| `parts` | `raw_parts_master` | Rename `Part No.→part_number`; regex replace `[$,]` → *(empty)* on `Unit Cost`, cast to double → `unit_cost_usd` |
| `inventory` | `raw_inventory` | Part-number cleaning; parse `As Of` with `dd-MMM-yyyy`; `inventory_id = concat("INV-", Program, "-", part_number)`; `Qty OH→on_hand` (integer) |
| `demand_monthly` | `raw_demand_history` | Part-number cleaning; `month = to_date(concat(Period, "-01"))`; `Units Issued→units` (integer) |
| `bom_notice_matches` | `bom_lines` ⋈ `notice_lines` | **Inner join on `part_number`**. Expect **5 rows**, the same 5 impact cases the reference code finds. This is the exact-match rule (D-04) running in Foundry |

**Check:** row counts must equal the reference files: programs 3 · assemblies 7 ·
parts 12 · bom_lines 13 · inventory 13 · demand_monthly 936 · bom_notice_matches 5.
Petrel's `M1A3P400-1PQG208I-ND` must appear in the matches (the suffix was stripped).

Deploy the pipeline and build all outputs.

### 1.4 Screenshot for the video/deck
The pipeline graph (raw → clean) and the `bom_notice_matches` preview.

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
