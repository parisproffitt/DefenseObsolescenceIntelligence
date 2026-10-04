# Autonomous intake: from a new notice to Steve's queue with no one touching it (D-23)

**Goal.** A new end-of-life notice should flow all the way to a costed, explained impact
case, with Steve notified, without anyone running anything by hand. The one step that
stays human is the decision itself: approving a purchase and a redesign commits money
and cannot be undone (D-05).

## The loop

```
notice text lands            raw/notice_inbox          (production: a Data Connection sync
      │                                                  from manufacturer PCN feeds / GIDEP)
      ▼  schedule: "when raw/notice_inbox updates, build downstream"
AIP extraction (kept model)  aip/notice_lines_auto     one call per page, incremental by notice_id
      ▼
code gate (gate.py)          aip/notice_lines_accepted  rows that pass every check
                             aip/notice_lines_rejected  rows that failed, with reasons
                             aip/notice_intake_status   RELEASED or HELD_FOR_REVIEW per notice
      ▼  only RELEASED notices continue
matching → impact → forecast → options  (the existing transforms, unchanged)
      ▼
Ontology sync                Impact Case objects appear / update
      ▼  Automate: "Impact Case added (CRITICAL/WATCH), severity became CRITICAL,
      ▼            or a Review Flag was added"
Steve is notified             in-platform notification + email, linking to the Workshop app,
                             where the AIP memo is already drafted next to Approve
      ▼
Steve approves (human)        Ontology Action writes status, purchase request, review
```

## The gate (why autonomy is safe here)
A new notice has no answer key, so the extraction can't be scored. `continuum/gate.py`
checks what can be checked from the notice alone (tested in `tests/test_gate.py`):

| Check | Catches |
|---|---|
| Part number appears verbatim in the notice text | Invented or normalized part numbers |
| Part number parses as a known manufacturer's part | Garbage tokens |
| Source quote appears in the notice | Made-up evidence |
| Dates are valid ISO dates | Unparsed or hallucinated dates |
| Replacement appears verbatim | Invented replacements |
| **Every part number in the text was extracted** | **Silently dropped rows, the costly error** |

A notice with any rejected row or any missed part number is `HELD_FOR_REVIEW`: its rows
become review flags and Steve is notified to check it, instead of the pipeline acting on
a partial list. This is the same reverse check that verified the answer key (D-20),
reused as a production control.

## What each piece is in Foundry
| Piece | Foundry feature | Built by |
|---|---|---|
| `raw/notice_inbox` | Dataset (demo: a transform that "releases" notices one at a time) | Terminal agent (MCP) |
| Extraction + gate transforms | Python transforms with a language model input | Terminal agent, after the Libraries step |
| Trigger on new data | Build schedule on `raw/notice_inbox` → downstream | Manual, `MANUAL_STEPS.md` step 6a |
| Notification to Steve | Automate (object-set condition → notification effect) | Manual, step 6b |
| Memo already drafted | `draftDecisionMemo` in the Workshop app | Manual, step 4a |

## Demo moment (about 20 seconds)
Start with only CAAN-02OLLE763 released. On camera, release Intel PDN2401 into the inbox
(one row flips in `raw/notice_inbox`, or re-run the release transform). The schedule
fires, and within minutes a new Kite impact case appears, flagged for a tin-whisker
review because the replacement changes the lead finish, and Steve gets a notification.
If the build is too slow to film live, film the notification and the new case after
the build, and say how long it took.

## Build status (2026-09-27)
| Piece | State |
|---|---|
| `raw/notice_releases` (the release switch; CAAN-02OLLE763 only) | Uploaded |
| `raw/notice_inbox` (`intake.py`) | Built in Foundry |
| Extraction, gate, `clean/notice_lines_live` (`pending/intake_aip.py`) | Written; tested locally with a stand-in model. Measured results (D-26) set it to Claude Sonnet in **document mode**, and add a gate check that holds a notice whose rows all lack a buy date. Deploying it is the next step |
| `analysis/impact` input | Still `clean/notice_lines` (switch only after the checks in D-25) |
| Schedule, Automate | UI (`MANUAL_STEPS.md` 6a, 6b) |

Local run of the whole loop with a stand-in model: CAAN-02OLLE763 RELEASED (110 accepted,
0 rejected, 0 missed); impact on the live lines reproduces every invariant. Releasing
PDN2401: RELEASED (120/0/0), 230 live lines, one new case **Kite · EP4CE10E22I7 · LOW**
(buy date passed 10.8 months before the scenario date) and one new flag,
**FINISH_CHANGE** (EP4CE10E22I7 → EP4CE10E22I7N). The on-camera moment is therefore the
new flag and case, not a CRITICAL alert; the Automate rule includes Review Flags so it fires.

