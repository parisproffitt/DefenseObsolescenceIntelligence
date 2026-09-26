# Demo script (target 4:30, hard limit 5:00)

Narration is ~135 words per minute. Every number below is produced by code in Foundry
and pinned by tests; say them exactly. Screens marked **[MANUAL]** depend on
`docs/MANUAL_STEPS.md` being done; the fallback in brackets shows the same thing
without it.

| # | Time | Screen | Narration |
|---|---|---|---|
| 1 | 0:00–0:25 | Deck cover, then the Microchip notice CAAN-02OLLE763 (PDF) | "Defense aircraft fly for thirty years; the chips inside them are supported for five. When a manufacturer discontinues one, it publishes a notice like this. On June 6th 2025 Microchip announced the end of 110 ProASIC3 FPGA part numbers, with a last-time buy on December 1st. An engineer, call her Dana, has to work out which programs that hits, before the window closes." |
| 2 | 0:25–0:55 | Foundry lineage graph: `raw/` → `clean/` → `analysis/` | "Program data arrives like this: spreadsheet exports with padded, lower-case part numbers and a distributor suffix. Python transforms clean it with the same normalizer that does the matching, and every table has a primary-key check. Then an exact join finds the affected lines." |
| 3 | 0:55–1:20 | `clean/bom_notice_matches` preview (5 rows), then the `review_flags` row for Petrel | "Five BOM lines across three programs, including one typed with a Digi-Key suffix. Just as important is what it doesn't match: Petrel uses an A3P1000 too, but in a different package that isn't discontinued. A fuzzy or AI match would flag it. Here it becomes a review flag, not a false alarm." |
| 4 | 1:20–2:00 | `aip/extraction_scores` in Foundry (or the AIP evaluation slide) | "Reading the notice is the one step that's language, so that's AIP. Every row it returns has to quote its source, and it's scored against the manufacturers' real lists: 230 part numbers. [AIP RESULT SENTENCE, from `aip/extraction_scores` after MANUAL_STEPS step 2: recall, precision and date accuracy for the kept model, and which model was kept and why. Never say a number that is not in that table. If it has not run by recording day, say instead: "The evaluation harness is built and tested; the model comparison runs next."]" |
| 5 | 2:00–2:50 | **[MANUAL]** Workshop app, Heron selected [fallback: Object Explorer on the Heron impact case] | "Here's what it means for Heron, an airlift fleet. 312 units on hand cover 13.8 months. The last-time buy closes in 5.7 months. A redesign takes 24 months. So even with a redesign started today, Heron runs out 10.2 months before it's ready. That's critical, and it's arithmetic you can trace back to its inputs." |
| 6 | 2:50–3:20 | Same page: forecast range cards (337 / 573 / 880) | "How many will Heron need over those 24 months? Demand is lumpy, so the forecast is a range: between 337 and 880 units, middle 573. I checked that the range is honest. On held-out data the raw version held 69% of outcomes against an 80% target; calibrated, 82%." |
| 7 | 3:20–4:05 | COA table | "Three options, all priced from that distribution. A life-of-type buy of 5,640 units looks safe at 10% risk, but if an aging fleet uses 5% more a year, that jumps to 99%: it's a 17-year bet on one forecast. Redesign alone is 93% likely to run short. A bridge buy of 500 units plus the redesign costs about the same, $1.55 million, and its risk is 14%, 18% under stress." |
| 8 | 4:05–4:30 | **[MANUAL]** Click *Approve course of action* → status flips; Procurement Request (500 units, $92,500) and Engineering Review appear [fallback: the action type in Ontology Manager] | "Dana makes the call. One action records the decision, opens a purchase request for 500 units and an engineering review for the redesign. Code did identity and arithmetic, ML the uncertainty, AIP the language, and the engineer the judgment." |
| 9 | 4:30–4:45 | Deck close slide | "That's CONTINUUM: one notice in, one program decision out." |

**Word count check:** ~590 words ≈ 4:25 at 135 wpm (scene 4 is ~25 words shorter with the fallback line).

## Before recording
- Run `pytest` and `python scripts/build_all.py`; the printout must match the numbers above.
- In Foundry, re-query `analysis/coas` and `analysis/impact_cases` (SQL in
  `docs/FOUNDRY_BUILD.md`, Phase 3) to confirm nothing moved.
- Reset Heron's status to `OPEN` (run the action with status `OPEN`, or revert the edit) so the approval can be shown live.
