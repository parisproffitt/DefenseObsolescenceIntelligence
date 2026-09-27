# Demo script (target 4:40, hard limit 5:00)

Narration is ~135 words per minute. Every number below is produced by code in Foundry
and pinned by tests; say them exactly. Screens marked **[MANUAL]** depend on
`docs/MANUAL_STEPS.md` being done; the fallback in brackets shows the same thing
without it.

**The through-line.** The brief assesses how AIP is integrated with Foundry, so the video
shows AIP at the three points where it does work (reading the notice, choosing the model,
writing the memo on the decision screen) and says, each time, what AIP is not allowed to
do. Scene 2 states this up front; scene 8 pays it off (D-21).

| # | Time | Screen | Narration |
|---|---|---|---|
| 1 | 0:00–0:20 | Deck cover, then the Microchip notice CAAN-02OLLE763 (PDF) | "Defense aircraft fly for thirty years; the chips inside them are supported for five. On June 6th 2025 Microchip discontinued 110 ProASIC3 FPGA part numbers, last-time buy December 1st. An engineer, Steve, has to work out which programs that hits, before the window closes." |
| 2 | 0:20–0:45 | Deck slide *How Foundry and AIP are used across the workflow* | "Here's the whole workflow on Foundry and AIP. Foundry transforms clean the data and do the math, the Ontology connects notice to part to program, and AIP does the three jobs that are language: reading the notice, choosing which model to trust, and writing the decision memo. The engineer makes the call through an Ontology Action." |
| 3 | 0:45–1:25 | **[MANUAL]** AIP Logic `extractNoticeLines` run on the notice; rows with quotes [fallback: deck slide *What AIP does*] | "First, AIP reads the notice. Every row it returns has a part number exactly as printed, the dates, and a verbatim quote as evidence. It also copied this sentence word for word: Microchip may cancel the notice if a new assembly site qualifies. That changes the decision, so Steve has to see it. [AIP RESULT SENTENCE from `aip/extraction_scores`: recall, precision and date accuracy for the small and the frontier model, and which one was kept. If not run by recording day: "Each run is scored against the manufacturers' 230 real part numbers."]" |
| 4 | 1:25–1:50 | Foundry lineage `raw/` → `clean/` → `analysis/`, then `bom_notice_matches` (5 rows) and Petrel's review flag | "Program data arrives messy. Python transforms clean it, and an exact join, not AI, finds five affected BOM lines. Petrel uses the same chip in a different package that isn't discontinued: a fuzzy match would raise a false alarm. Here it's a review flag." |
| 5 | 1:50–2:30 | **[MANUAL]** Workshop app, Heron selected [fallback: Object Explorer on the Heron impact case] | "Heron, an airlift fleet, is critical. 312 units on hand cover 13.8 months. The last-time buy closes in 5.7 months, and a redesign takes 24. So even starting a redesign today, Heron runs out 10.2 months before it's ready." |
| 6 | 2:30–2:55 | Same page: forecast range cards (337 / 573 / 880) | "How many will it need? Demand is lumpy, so the forecast is a range: 337 to 880 units, middle 573. I checked the range is honest: on held-out data, calibrated, it held 82% of outcomes against an 80% target." |
| 7 | 2:55–3:35 | COA table | "Three options, priced by code. A life-of-type buy of 5,640 units has a 10% shortage risk, but if an aging fleet uses 5% more a year, that's 99%. Redesign alone is 93%. A bridge buy of 500 plus the redesign costs about the same, $1.55 million, with 14% risk, 18% under stress." |
| 8 | 3:35–4:10 | **[MANUAL]** Workshop memo panel beside *Approve* [fallback: `draftDecisionMemo` test run in AIP Logic] | "Then AIP writes the memo Steve would have written by hand, straight from these Ontology objects. It lays out the options and the deadline, but it can't recommend one, and code checks that every number in it matches the Ontology before it's shown." |
| 9 | 4:10–4:35 | **[MANUAL]** Click *Approve course of action* → status flips; Procurement Request (500 units, $92,500) and Engineering Review appear [fallback: the action type in Ontology Manager] | "Steve makes the call. One Action records the decision, opens a purchase request for 500 units and an engineering review. Code did the arithmetic, ML the uncertainty, AIP the language, and the engineer the judgment." |
| 10 | 4:35–4:45 | Deck close slide | "That's CONTINUUM: one notice in, one program decision out." |

**Word count check:** ~600 words ≈ 4:30 at 135 wpm, leaving ~15 s for clicks and pauses.

## Before recording
- Run `pytest` and `python scripts/build_all.py`; the printout must match the numbers above.
- In Foundry, re-query `analysis/coas` and `analysis/impact_cases` (SQL in
  `docs/FOUNDRY_BUILD.md`, Phase 3) to confirm nothing moved.
- Run `draftDecisionMemo` on Heron once and check its numbers against `docs/AIP_LOGIC.md` → *Expected memo for Heron*.
- Reset Heron's status to `OPEN` (run the action with status `OPEN`, or revert the edit) so the approval can be shown live.
