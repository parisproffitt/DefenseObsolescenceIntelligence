# AIP Logic — notice extraction

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
Intel PDN2401 lists 120 parts across six attachment tables. Extract per page (or per
table) and union the results; long single calls are where rows get dropped. The
evaluation below measures whether chunking is actually needed.

## Evaluation (D-14)
Export the function's output as a dataset and score it with
`continuum.eval_extraction.score(extracted, truth)` against `notice_lines`:
part recall and precision, LTB/LTS accuracy, replacement accuracy, citation coverage.

Model comparison: run the same notices through a small and a frontier model
available in AIP. Keep the cheaper model for any step where its scores match.
Report numbers on the AIP evaluation slide; do not round up.
