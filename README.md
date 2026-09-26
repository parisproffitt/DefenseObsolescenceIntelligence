# CONTINUUM

**A decision-support system for defense parts obsolescence, built on Palantir Foundry and AIP.**

[![tests](https://img.shields.io/github/actions/workflow/status/parisproffitt/DefenseObsolescenceIntelligence/tests.yml?branch=main&label=tests&style=flat-square&color=FF5B1F&labelColor=08090A)](https://github.com/parisproffitt/DefenseObsolescenceIntelligence/actions/workflows/tests.yml) &nbsp;Palantir Foundry · AIP · Python · MIT

CONTINUUM reads a manufacturer's end-of-life notice, finds every program that depends on the discontinued parts, forecasts how many will be needed with an honest uncertainty range, and lays out costed options for an engineer to approve.

**In the demo,** one real Microchip notice reveals a program with a **10.2-month supply gap** that can't be fixed later. The recommended bridge buy cuts its shortage risk from **93% to 14%**.

<!-- SCREENSHOT: Workshop app — impact case list with Heron flagged CRITICAL (docs/screenshots/workshop-cases.png) -->

---

## Why I built this

I've been fascinated by military aircraft for as long as I can remember, and I've always wanted to ride in one. Working in the defense industry changed how I see them. I realized that keeping one aircraft flying takes far more pieces and parts than I'd ever imagined: thousands of components, each with its own supplier, stock and lifespan. Behind every one of those parts are people tracking notices, checking bills of materials and planning purchases years ahead, mostly by hand.

That's the problem I chose: not the aircraft itself, but the unglamorous system that keeps it in the air. **A few-dollar part can ground a multimillion-dollar aircraft**, and it usually starts with a PDF nobody connected to the right program in time.

## The problem

Defense systems serve for 25–30 years. The commercial electronics inside them are supported for only 4–7. When a manufacturer discontinues a part, it publishes a notice with a last-time-buy date. An engineer then has to work out which programs use the part, how long the remaining stock will last, and whether to buy more or fund a redesign, all before the window closes.

The DoD calls this **DMSMS** (Diminishing Manufacturing Sources and Material Shortages). The process is well defined. The bottleneck is information: notices, bills of materials, inventory and demand history all live in different places.

## How it works

| Step | What happens | Done by |
|---|---|---|
| 1. Read the notice | Extract affected parts, deadlines, replacements and caveats, each with a quote from the source | **AIP** |
| 2. Match to programs | Find every bill of materials that uses an affected part; flag near-misses for review | Code |
| 3. Measure impact | Stock coverage, supply gap and severity for each program | Code |
| 4. Forecast demand | A calibrated range of how many parts each program will need | **ML** |
| 5. Lay out options | Costed courses of action, explained in plain language | **AIP** |
| 6. Decide | The engineer approves an option; an Ontology Action records it | **Engineer** |

The rule behind every step: **code for identity and arithmetic, ML for uncertainty, AIP for language, and the engineer for judgment.** Every number the engineer sees is computed in code and traceable to its source.

## AI and ML design

### AIP reads the notices
Notices come in every format: prose, tables, multi-page attachments, revisions. AIP Logic turns each one into structured rows, and every row quotes the text it came from. It also copies word for word any sentence that could change a buy decision. In the demo notice, Microchip says it *may cancel* the end-of-life if a new factory qualifies, and the engineer needs to see that.

The prompt's core rules ([full spec](docs/AIP_LOGIC.md)):

```text
1. List EVERY affected ordering part number in the text, exactly as printed.
2. Never invent a part number, date, or replacement. If a field is not stated, return null.
4. A replacement counts only if the notice explicitly pairs it with that part.
   Do not suggest one, and never state that a part is compatible.
5. For every row, quote the shortest verbatim text that supports it.
6. Copy any sentence that could change a buy decision into `caveats`, verbatim.
```

**Measured, not trusted.** The output is scored against the manufacturers' real parts lists (230 part numbers). **Recall** catches the costly error, a missed part; **precision** catches the dangerous one, an invented part. A small and a frontier model are compared on the same notices, and the cheaper one is kept wherever it scores the same ([D-14](DECISIONS.md)).

<!-- SCREENSHOT: AIP Logic function and its evaluation results (docs/screenshots/aip-logic-eval.png) -->

### ML forecasts demand as a range
Spare-parts demand is lumpy: months of nothing, then a spike. A single-number forecast hides exactly the risk a buy decision is about, so CONTINUUM forecasts total demand over the decision window as a **distribution** and sizes purchases at a stated confidence level.

The first version was overconfident: its "80% range" held only 69% of real outcomes on held-out data. The fix widens the distribution by the smallest factor that reaches 80% on *earlier* data, then checks it on *later* data it never saw:

```python
# src/continuum/forecast.py
def calibrate_spread(demand, horizon=12, origins=range(36, 49, 3), target=0.80, grid=...):
    """Smallest spread whose P10-P90 coverage reaches `target` on the calibration origins."""
    for k in grid:
        for _, y in _series(demand):
            for o in origins:
                s = bootstrap_samples(y[:o], horizon, seed=o, spread=k)
                lo, hi = np.percentile(s, [10, 90])
                hits.append(lo <= y[o:o + horizon].sum() <= hi)
        ...
```

| Held-out test | Outcomes inside the P10–P90 range (target 80%) |
|---|---|
| Raw forecast, 200 series | 69% |
| **Calibrated forecast, 200 series** | **82%** |
| Calibrated forecast, demo programs | 85% |

The honest finding: the forecast's middle value is no sharper than a simple average. **Its value is a range you can trust** ([D-07](DECISIONS.md)). The demand data is synthetic, so this validates the method, not real-world accuracy.

### Options are costed under uncertainty
Each option is priced from the forecast distribution: purchase, storage, engineering, chance of running out, and expected excess stock. A stress test asks what happens if an aging fleet uses parts faster. The growth rate is a stated assumption the engineer can change; a trend fitted to six years of lumpy data proved too noisy to trust (off by ±11 points in simulation, [D-10](DECISIONS.md)).

### Where AI is deliberately not used
Deciding whether a program's part is on a notice is an identity question with one right answer. The demo notice mentions "A3P1000 device families" but discontinues only the 208-pin package. A program using the same chip in a 484-ball package is **not** affected. Fuzzy or AI matching gets this wrong, so matching is exact, with near-misses flagged for a person ([D-04](DECISIONS.md)):

```python
# src/continuum/partnumbers.py
for bp in bom_parts:
    n = normalize(bp)                         # trim, upper-case, drop distributor suffixes
    if n in exact:
        results.append(MatchResult(bp, MatchType.EXACT, exact[n]))
        continue
    device = parse(bp).device                 # same chip, different package or grade?
    if device and device in by_device:
        results.append(MatchResult(bp, MatchType.FAMILY_ONLY, by_device[device]))
    else:
        results.append(MatchResult(bp, MatchType.NONE, None))
```

## Demo: the Heron program

Replaying Microchip's real notice **CAAN-02OLLE763** (ProASIC3 FPGAs) as of June 2025, against three fictional programs:

| | Heron · A3P1000-1PQG208I |
|---|---|
| Units on hand | 312 |
| Stock coverage | 13.8 months |
| Last-time buy closes in | 5.7 months |
| Redesign takes | 24 months |
| **Result** | **CRITICAL: 10.2 months with no parts** |

| Option | Buy | Total cost | Shortage risk | If demand grows 5%/yr |
|---|---|---|---|---|
| Life-of-type buy | 5,640 | $1.53M | 10% | 99% |
| Redesign only | 0 | $1.45M | 93% | 94% |
| **Bridge buy + redesign** | **500** | **$1.55M** | **14%** | **18%** |

The life-of-type buy bets 17 years on one forecast. The bridge buy costs about the same and only has to be right for 24 months. The engineer makes the call, and the Action records it. *(Heron and its costs are fictional.)*

<!-- SCREENSHOT: Heron impact case in Workshop — forecast range and the three options (docs/screenshots/workshop-heron.png) -->
<!-- SCREENSHOT: Approve course of action — before/after status (docs/screenshots/action-approve.png) -->

## Built on Foundry

| Layer | In Foundry |
|---|---|
| Data integration | Python transforms turn messy spreadsheet-style exports into clean, keyed tables |
| Ontology | 10 object types, 13 link types: Program → Assembly → BOM Line → Part ← Notice Line |
| Decision logic | Transforms compute impact cases, forecasts and courses of action |
| AIP | AIP Logic extracts notice lines; explains options and drafts the decision memo |
| Application | Workshop app for the engineer, with an Action that writes the decision back |

Cleaning runs in Foundry with the **same normalizer the matching step uses**, and every table declares its primary key as a build check, so bad data fails the build instead of reaching the Ontology ([D-16](DECISIONS.md)):

```python
# foundry/continuum-transforms/src/myproject/datasets/clean.py
@transform.using(
    out=Output(f"{CLEAN}/bom_lines", checks=_pk("bom_line_id")),   # duplicate key → build fails
    raw=Input(f"{RAW}/raw_bom_export"),
)
def bom_lines(out, raw):
    df = _read_csv(raw, "raw_bom_export")
    ...  # part numbers pass through partnumbers.normalize(), shared with matching
```

Ontology changes are made on a branch and merged only after review, the same "machine proposes, person approves" rule the product follows ([D-17](DECISIONS.md)).

<!-- SCREENSHOT: Foundry data lineage — raw exports → clean tables → analysis (docs/screenshots/lineage.png) -->
<!-- SCREENSHOT: Ontology graph around Heron (docs/screenshots/ontology.png) -->

## Data

- **Real:** the manufacturer notices and their 230 affected part numbers, deadlines and replacements (Microchip CAAN-02OLLE763, Intel PDN2401).
- **Notional:** the programs (Heron, Kite, Petrel), their bills of materials, stock, costs and six years of demand. Real program data isn't public, so it's labeled as notional everywhere.
- **Not included:** any employer data, and the notice PDFs themselves (linked, not redistributed).

## Engineering quality

- **32 automated tests** run on every push, including tests that pin every number in the demo.
- **Decision log:** [`DECISIONS.md`](DECISIONS.md) records each choice, the alternative considered and why it lost, including first attempts that failed a check and what replaced them.

## From demo to deployment

A pilot with one program office would:
1. **Connect** live notice feeds (manufacturer portals and GIDEP, the government-industry exchange).
2. **Replace** the notional data with the program's own records and re-run every evaluation.
3. **Measure** hours from notice to decision, and shortages caught before the buy window closed.

<details>
<summary><b>Repository layout and quickstart</b></summary>

```
src/continuum/        reference implementation (Python)
  partnumbers.py      part-number normalization and notice matching
  generate.py         notional programs, bills of materials, stock, demand
  raw.py              messy raw exports for Foundry ingestion
  impact.py           coverage, supply gap, severity, review flags
  forecast.py         calibrated demand forecast and backtest
  coa.py              costed courses of action and stress test
  eval_extraction.py  scores AIP's notice extraction
  extraction.py       AIP extraction prompt, chunking, parsing (shared with AIP Logic)
foundry/              code deployed to Foundry (transforms, Ontology ids)
data/                 notice registry and real parts lists (ground truth)
docs/                 Foundry build guide, AIP Logic spec
tests/                32 automated tests
```

```bash
pip install -e ".[dev]"
python scripts/build_all.py   # regenerates all data and prints the scenario
pytest
```
</details>

<sub>Licensed under the [MIT License](LICENSE).</sub>
