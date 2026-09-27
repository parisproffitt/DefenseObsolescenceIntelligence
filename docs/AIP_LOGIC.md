# AIP Logic — notice extraction and decision memo

The one step where an LLM does the work (D-09): read a manufacturer notice and
return structured, cited rows. Everything downstream (matching, math, courses of
action) is deterministic and consumes these rows.

## Function
**Name:** `extractNoticeLines`
**Input:** notice text (from the PDF in the `notices` media set; one call per page
chunk for long notices, see below) and the `notice_id`.
**Output:** a list of objects, one per affected ordering part number:

| Field | Type | Rule |
|---|---|---|
| `notice_id` | string | as given |
| `part_number` | string | exactly as printed; no normalizing, no inventing |
| `last_time_buy` | date `YYYY-MM-DD` | the last order / booking date that applies to this part |
| `last_time_ship` | date `YYYY-MM-DD` | the last shipment date that applies to this part |
| `replacement_part_number` | string or null | only if the notice names one for this part |
| `source_quote` | string | the shortest verbatim text supporting the row (e.g. the table row) |

Plus one notice-level object:

| Field | Rule |
|---|---|
| `notice_type` | EOL / PDN / PCN, as stated |
| `caveats` | verbatim sentences that change the decision, e.g. "qualifying a new assembly site… intend to cancel the EOL notice" or "LTB orders will be processed as NCNR" |

## Prompt (system)
```
You extract facts from semiconductor end-of-life / discontinuance notices for a
defense sustainment engineer. Accuracy matters more than completeness of prose.

Rules:
1. List EVERY affected ordering part number in the text, exactly as printed.
   Do not group, abbreviate, expand ranges, or normalize.
2. Never invent a part number, date, or replacement. If a field is not stated
   for a part, return null for it.
3. Dates: convert to YYYY-MM-DD. If the notice gives one LTB/LTS for all parts,
   apply it to every part.
4. A replacement counts only if the notice explicitly pairs it with that part.
   Do not suggest one, and never state that a part is compatible.
5. For every row, quote the shortest verbatim text that supports it.
6. Copy any sentence that could change a buy decision (possible cancellation,
   non-cancellable orders, allocation limits) into `caveats`, verbatim.
Return only the JSON object described in the schema.
```

## Long notices
Intel PDN2401 lists 120 parts across six attachment tables. Two modes are evaluated
(D-19): `document` (one call per notice) and `page` (one call per page, each prefixed
with page 1 so the dates are in view; results unioned). Long single calls are where
rows get dropped; the evaluation measures whether chunking is actually needed.

## Implementation
- `src/continuum/extraction.py`: `SYSTEM_PROMPT` (the text above), `SCHEMA`, chunking,
  tolerant JSON parsing, and a per-call log. Tested in `tests/test_extraction.py`.
- Input: `raw/raw_notice_text`, the text layer of the two PDFs, one row per page
  (CAAN-02OLLE763: 6 pages; PDN2401: 10 pages). All 230 ground-truth OPNs appear in it
  verbatim.
- Foundry transform: `foundry/continuum-transforms/pending/aip_extraction.py` writes
  `aip/extraction_{small,frontier}_lines`, `..._calls`, and `aip/extraction_scores`.
  It is held until the language-model libraries are added (`docs/MANUAL_STEPS.md`, step 2).

## Evaluation (D-14)
Export the function's output as a dataset and score it with
`continuum.eval_extraction.score(extracted, truth)` against `notice_lines`:
part recall and precision, LTB/LTS accuracy, replacement accuracy, citation coverage.

Model comparison: run the same notices through a small and a frontier model
available in AIP. Keep the cheaper model for any step where its scores match.
Report numbers on the AIP evaluation slide; do not round up.

## Results
**Not yet measured** (2026-09-26). Fill this table from `aip/extraction_scores`
(`notice_id = POOLED`) after `docs/MANUAL_STEPS.md` step 2:

| Model | Mode | Recall | Precision | LTB exact | LTS exact | Replacements | Citations | Failed calls |
|---|---|---|---|---|---|---|---|---|
| small | document | | | | | | | |
| small | page | | | | | | | |
| frontier | document | | | | | | | |
| frontier | page | | | | | | | |

---

# AIP Logic — `draftDecisionMemo` (D-21)

The second AIP Logic function. It turns the computed options for one Impact Case into
the memo Steve would otherwise write by hand. It never computes, recommends or judges fit.

**Input:** one Impact Case object. The function reads its properties and its linked
Course of Action objects (Search Around → Courses of Action), and the notice's
`caveats` if extracted.
**Output:** String (plain-text memo, three sections: Situation · Options · Decision needed).
**Model:** the model kept in the extraction comparison; temperature 0.

**Prompt (system):** `continuum.memo.SYSTEM_PROMPT`, verbatim:
```
You draft a short decision memo for a defense program office about one obsolete part.
Rules:
1. Use only the facts in the INPUT block. Copy every number exactly as written there.
   Never compute, round, convert or estimate a new number.
2. Do not recommend or choose a course of action. Present each option's quantity, cost
   and chance of running short (flat demand and under the stated stress), then state
   the decision the engineer must make and the date it must be made by.
3. If a caveat is given, quote it verbatim.
4. Never state that a replacement part is compatible.
5. Three headed sections: Situation, Options, Decision needed. Under 220 words.
Return the memo as plain text.
```
**Task prompt:** the INPUT block exactly as `continuum.memo.build_input(case, coas, caveats)`
renders it (one `key: value` line per property; one `option:` line per Course of Action).

**Guardrail:** `continuum.memo.unsupported_numbers(memo, input_block)` must return an
empty list before the memo is shown. In Foundry this is a TypeScript/Python function
check in the Logic board (a final block that compares the numbers) or, simplest, a
Workshop rule that shows the memo only when the check function returns `[]`.

**Expected memo for Heron** (numbers must match exactly): 312 units, 13.8 months of
stock, 5.7 months to the 2025-12-01 last-time buy, 24-month redesign, 10.2-month gap;
life-of-type buy 5,640 units, $1.53M, 10% / 99%; redesign only 0 units, $1.45M,
93% / 94%; bridge buy + redesign 500 units, $1.55M, 14% / 18%.

