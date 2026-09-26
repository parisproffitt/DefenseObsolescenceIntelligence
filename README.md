# CONTINUUM — Obsolescence Intelligence for Defense Sustainment

[![tests](https://github.com/parisproffitt/DefenseObsolescenceIntelligence/actions/workflows/tests.yml/badge.svg)](https://github.com/parisproffitt/DefenseObsolescenceIntelligence/actions/workflows/tests.yml)

Built on Palantir Foundry and AIP, CONTINUUM turns manufacturer end-of-life notices into program-level impact analysis, uncertainty-aware demand forecasts, and human-approved mitigation decisions.

> Defense systems serve for 25–30+ years. The commercial electronics inside them are supported for 4–7. When a part is discontinued, the manufacturer publishes a notice, usually a PDF. An engineer then has to work out what that one document means for every program that depends on it, before the last-time-buy window closes. The DoD calls this **DMSMS** (Diminishing Manufacturing Sources and Material Shortages).

## The workflow

```
EOL notice (PDF) ──► AIP extraction ──► part-number normalization ──► BOM traversal
      ──► coverage & gap math ──► demand forecast (calibrated range)
      ──► replacement review flags ──► courses of action ──► engineer decides
      ──► Ontology Action: procurement request + engineering review + risk status
```

| Step | Who does it | Why |
|---|---|---|
| Read the notice, extract OPNs, dates, replacements | **AIP** (with source citations) | Unstructured documents in many formats |
| Match OPNs to BOM lines | **Deterministic code** | Identity question with one right answer ([D-04](DECISIONS.md)) |
| Coverage, gap, severity | **Deterministic code** | Every number must be traceable |
| How many units will we consume? | **ML: bootstrap forecast, calibrated** | Lumpy demand; the decision needs a range ([D-06, D-07](DECISIONS.md)) |
| Replacement differences | **Code + AIP**, flagged for review | Compatibility is an engineering judgment ([D-05](DECISIONS.md)) |
| Draft courses of action and memo | **AIP**, from computed numbers | Language and synthesis ([D-09](DECISIONS.md)) |
| Choose a course of action | **The engineer** | Consequential decision |

## Demo scenario (reproducible)

Scenario date **2025-06-10**, replaying Microchip's real notice **CAAN-02OLLE763** (ProASIC3 FPGAs, last-time buy 2025-12-01).

| Program | Part | On hand | Coverage | Severity |
|---|---|---|---|---|
| **Heron** (airlift fleet) | A3P1000-1PQG208I | 312 | 13.8 mo | **CRITICAL**: out of stock 10.2 months before a 24-month redesign could be ready; LTB closes in 5.7 months |
| Heron | A3P250-PQG208I | 170 | 28.7 mo | WATCH |
| Petrel (radar) | M1A3P400-1PQG208I | 133 | 43.1 mo | MODERATE |
| Kite (trainer) | A3P250-PQG208I | 280 | > support life | LOW |

**Review flags:**
- Petrel's `A3P1000-1FGG484I` shares a device name with the notice but is a different package and **not** discontinued. It is flagged, not matched.
- Kite's Intel `EP4CE10E22I7` replacement (PDN2401) changes the finish from tin-lead to lead-free, which triggers a tin-whisker review.

**Heron courses of action** (notional costs):

| COA | Buy | Total cost | Shortage risk | …if demand grows 5%/yr (stress) |
|---|---|---|---|---|
| Life-of-type buy | 5,640 | $1.53M | 10% | 99% |
| Redesign only | 0 | $1.45M | 93% | 94% |
| **Bridge buy + redesign** | **500** | **$1.55M** | **14%** | **18%** |

The life-of-type buy looks cheapest until you add holding cost and ask what happens if an aging fleet consumes parts faster. It bets 17 years of support on one forecast. The hybrid costs about the same and only has to be right for 24 months.

## Forecast evaluation (held-out, 12-month cumulative demand)

| Evaluation | Method | MAE vs naive average | P10–P90 coverage (target 80%) |
|---|---|---|---|
| 200-series corpus, raw bootstrap | bootstrap median | 1.05 | 69% |
| 200-series corpus, calibrated (×1.35) | bootstrap median | 1.05 | **82%** |
| Program series, calibrated | bootstrap median | 0.95 | 85% |

The bootstrap's value is a **calibrated planning range**, not a sharper point estimate. Because the evaluation data is synthetic, these results validate the method's machinery and must be re-run on real demand history ([D-07](DECISIONS.md)).

## Data

| Data | Real or notional | Source |
|---|---|---|
| EOL notices, affected OPNs, dates, replacements | **Real** | Microchip CAAN-02OLLE763, Intel PDN2401 (see [`data/notices/`](data/notices)) |
| Programs, assemblies, BOMs, inventory, costs | Notional | [`src/continuum/generate.py`](src/continuum/generate.py) |
| Monthly demand history | Notional (lumpy, trended, seeded) | same |

Raw, spreadsheet-style exports (`output/raw/`) are cleaned inside Foundry by a Pipeline Builder pipeline; the Python code is the reference implementation it must reproduce ([D-12](DECISIONS.md)). Step-by-step build: [`docs/FOUNDRY_BUILD.md`](docs/FOUNDRY_BUILD.md).

Only links and metadata for notices are committed, not the manufacturers' PDFs. The affected-part CSVs double as **ground truth** for evaluating AIP's extraction.

## Repository

```
src/continuum/
  partnumbers.py   normalization, ProASIC3/Intel OPN parsing, notice matching
  generate.py      notional programs/BOMs/inventory/demand + evaluation corpus
  forecast.py      baselines, bootstrap, calibration, rolling-origin backtest
  impact.py        notice -> impact cases, coverage/gap/severity, review flags
  coa.py           courses of action, holding cost, growth stress test
  raw.py           messy raw exports for Foundry ingestion
  eval_extraction.py  scores AIP notice extraction against ground truth
scripts/build_all.py   generates everything into output/ (Foundry upload set)
data/notices/          notice registry + sources
data/reference/        real affected-part lists (ground truth)
tests/                 27 pytest cases, incl. the demo story's numbers
DECISIONS.md           design decision log
docs/FOUNDRY_BUILD.md  exact Foundry / AIP build steps
docs/AIP_LOGIC.md      extraction prompt, output schema, evaluation
```

```bash
pip install -e ".[dev]"
python scripts/build_all.py     # writes output/*.csv and prints the scenario
pytest
```

## Foundry and AIP mapping

Upload `output/*.csv` as datasets, then create these object types ([D-11](DECISIONS.md)):

| Object type | Backing dataset | Primary key | Title | Links |
|---|---|---|---|---|
| Program | `programs` | `program_id` | `name` | has many Assembly, Impact Case |
| Assembly | `assemblies` | `assembly_id` | `name` | belongs to Program (`program_id`) |
| Part | `parts` | `part_number` | `part_number` | — |
| BOM Line | `bom_lines` | `bom_line_id` | `part_number` | Assembly (`assembly_id`), Part (`part_number`) |
| Inventory Position | `inventory` | `inventory_id` | `inventory_id` | Program, Part |
| Notice | `notices` | `notice_id` | `notice_id` | has many Notice Line |
| Notice Line | `notice_lines` | `notice_line_id` | `part_number` | Notice (`notice_id`) |
| Impact Case | `impact_cases` | `case_id` | `case_id` | Program, Part, Notice |
| Review Flag | `review_flags` | `flag_id` | `flag_type` | Program, Part, Notice |
| Course of Action | `coas` | `coa_key` | `name` | Impact Case (`case_id`) |

`demand_monthly`, `tradeoff_curve` and the backtest outputs stay datasets (charts in Workshop / Contour).

| Here | In Foundry |
|---|---|
| `partnumbers.py`, `impact.py`, `coa.py` | Python transforms / Functions (Code Repositories) |
| Notice PDF to structured lines | AIP Logic ([spec](docs/AIP_LOGIC.md)), scored by `eval_extraction.py` against `notice_lines` |
| COA narrative and decision memo | AIP Logic over computed COA values |
| Engineer's choice | Ontology Action: create Procurement Request and Engineering Review, set Impact Case `status` |

*Programs Heron, Kite, and Petrel are fictional. No employer data is used.*

Licensed under the [MIT License](LICENSE).
