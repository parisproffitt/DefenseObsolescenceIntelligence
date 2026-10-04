# Demo script (target 4:40, hard limit 5:00)

Matches what is built as of 2026-10-04. Narration is about 135 words per minute
(~610 spoken words). Every number is produced by code in Foundry and pinned by tests;
say them exactly. AIP scores are from `aip/extraction_scores` (D-26).

**The through-line.** The brief asks how AIP is used with Foundry. The video shows AIP
where language is the work (reading the notice, chosen by measured accuracy), the
Ontology as the shared model, code for every number, and one human approval written
back by an Ontology Action. Each time AIP appears, say what it is not allowed to do.

## Script

| # | Time | Screen | Narration |
|---|---|---|---|
| 1 | 0:00–0:20 | Deck: cover, then *Defense systems outlive the parts inside them* | "Military aircraft fly for twenty-five to thirty years. The commercial chips inside them are supported for four to seven. So every few months, a manufacturer discontinues a part, and an engineer has to work out what that means for every program that uses it, before the last order date." |
| 2 | 0:20–0:40 | Deck: *A real end-of-life notice drives the demo* | "This is a real one. Microchip notice CAAN-02OLLE763 discontinues 110 FPGA part numbers, last-time buy December 1st, 2025. It also says the notice may be cancelled if a new assembly site qualifies. Steve, our DMSMS engineer, has to catch that too." |
| 3 | 0:40–1:05 | Deck: *How Foundry and AIP are used across the workflow* | "Here's the design. AIP reads the documents. Python transforms in Foundry clean the data and do every calculation. The Ontology connects notice, part, program and decision. And the engineer makes the call through an Ontology Action. Code for numbers, AI for language, a person for judgment." |
| 4 | 1:05–1:40 | Pipeline Builder canvas: `extraction_prompts` → two *Use LLM* nodes → two outputs; then the deck slide *Two models, 230 real parts: Sonnet is kept* | "AIP reads the notice in Pipeline Builder. I ran two models on the same prompts, GPT-5.4 nano and Claude Sonnet, and scored both against the manufacturers' 230 real part numbers. Both found every part. But the small model dropped every date on the Intel notice, so I keep Sonnet: 100 percent on every field. And every row carries a verbatim quote; the cancellation caveat comes through word for word." |
| 5 | 1:40–2:05 | Foundry Data Lineage: `raw/` → `clean/` → `analysis/`; then `bom_notice_matches` (5 rows) | "Program data arrives messy, the way a customer hands it over. Transforms clean it, and an exact match, not AI, finds five affected lines across three programs. Petrel uses the same chip in a different package that isn't discontinued, so it's flagged for review, not matched." |
| 6 | 2:05–2:40 | Workshop app, left column, then click **Heron · A3P1000** | "This is Steve's app. Every affected case, worst first; only critical is red. Heron, an airlift fleet: 312 units on hand cover 13.8 months. The buy window closes in 5.7. A redesign takes 24. So even starting today, Heron runs out 10.2 months before the redesign is ready." |
| 7 | 2:40–3:00 | Same screen: the forecast cards 337 / 573 / 880 | "How many will it need? Spares demand is lumpy, so the forecast is a range: 337 to 880 units. I calibrated it on held-out data; it holds 82 percent of outcomes against an 80 percent target." |
| 8 | 3:00–3:30 | Right column: the three options; point at the red 99% | "Three options, priced by code. A life-of-type buy looks safe at 10 percent shortage risk, but if an aging fleet uses 5 percent more a year, that becomes 99. Redesign alone: 93. A bridge buy of 500 plus the redesign costs about the same, 1.55 million, at 14 percent, and 18 under stress." |
| 9 | 3:30–4:00 | Click **Bridge buy + redesign** → **Approve COA** → form shows Heron, APPROVED, Bridge buy → **Submit** → Heron's status changes to APPROVED | "Steve chooses. The form fills itself from the Ontology: quantity, cost, program, justification. He never retypes what the system knows. One Action records the decision and opens the purchase request and the engineering review together." |
| 10 | 4:00–4:25 | Deck: *What runs on its own, and what never does* | "Everything before this click can run on its own: a new notice arrives, AIP reads it, a code gate holds anything it can't verify, and Steve is notified. The approval never automates. A last-time buy can't be cancelled." |
| 11 | 4:25–4:40 | Deck: *Pilot CONTINUUM with one program office* | "Next step: a pilot with one program office, on their own data, measuring hours from notice to decision. That's CONTINUUM: one notice in, one program decision out." |

## Shot list (record each as its own clip)

Open these tabs in this order before recording, signed in, at 110–125% browser zoom,
bookmarks bar hidden, notifications off:

1. **Deck**, presentation mode, on the cover. Slides used: cover, *Defense systems outlive…*, *A real end-of-life notice…*, *How Foundry and AIP are used…*, *What runs on its own…*, *Pilot CONTINUUM…*
2. **Pipeline Builder** `aip/extract_notice_lines`, canvas fitted to screen. Second take: a Use LLM node open with its output showing the caveat. Deck slide 28 (*Two models, 230 real parts*) for the scores.
3. **Data Lineage** for `analysis/coas` (raw → clean → analysis visible), then the `analysis/bom_notice_matches` preview (5 rows).
4. **Workshop app** in View mode, Heron selected, no option selected.

| Clip | Tab | Action | Length |
|---|---|---|---|
| A | Deck | Cover → problem → notice → platform (advance on the narration beats) | ~1:05 |
| B | Pipeline Builder | Hold on the canvas 5 s; click the Use LLM node; scroll to the output | ~0:35 |
| C | Lineage | Pan raw → clean → analysis; open `bom_notice_matches` | ~0:25 |
| D | Workshop | Hover the CRITICAL row; click Heron; hold on the cards; hold on the forecast | ~0:55 |
| E | Workshop | Hover the red 99%; click Bridge buy; Approve COA; pause on the form; Submit; show status APPROVED | ~1:00 |
| F | Deck | Autonomy slide → close slide | ~0:40 |

## Before recording
- Run `pytest` (44 tests) so the numbers above are re-confirmed.
- In Workshop, confirm Heron's status is `OPEN`. Approving is the last clip; if you need a
  second take, set Heron back with the action (status `OPEN`) and expect a second purchase
  request object; delete it afterwards in Object Explorer.
- Record the voice separately (quiet room, mic or phone close), one scene per take, then cut
  the screen clips to the voice. Add captions; zoom in on 10.2, 82%, 99% and the form.
- Export 1080p. Upload to YouTube as **Unlisted**, check it plays at 1080p, then email the
  link to USG-AIP-DEMO@Palantir.com with the GitHub link and the deck.
