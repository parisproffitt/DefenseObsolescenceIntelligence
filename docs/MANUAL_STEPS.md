# Manual steps

These are the steps the Palantir MCP cannot do (D-15). Everything around them was built
through the MCP and is mirrored in `foundry/`. Do them in order; each says how to check
it worked. Foundry host: `https://continuum-demo.usw-17.palantirfoundry.com`.
Project: `/CONTINUUM-edbe5f/Continuum`.

<!-- Sections are appended as the build reaches each step. -->

## 1. Approve the Ontology proposal (Phase 2 + the action) — DONE 2026-09-27
Merged; the objects serve the invariant values (checked with the MCP: Heron 312 / 13.8 / 5.7 / 10.2 CRITICAL; hybrid 500 / $1,550,011 / 0.1425 / 0.1815).
Everything Ontology-side was created on global branch **continuum-ontology**.
1. Open the proposal:
   https://continuum-demo.usw-17.palantirfoundry.com/workspace/developer-branching/proposal/ri.branch..proposal.6aedeb42-43ab-456b-85fe-648ede7393b1
2. Review: 12 object types, 15 link types, 1 action type (*Approve course of action*).
3. **Approve** and **Merge**. Wait for the object indexes to finish (Ontology Manager →
   each object type → Datasources shows "Up to date").
- **Check:** Object Explorer → search "Heron" → Program *Heron* → Assemblies (3) →
  *Mission Computer Processor Card* → BOM Lines → `A3P1000-1PQG208I` → Part. Then Heron →
  Impact Cases: 2 (one CRITICAL, one WATCH).

## 2. Run the AIP extraction evaluation, then build `extractNoticeLines` (step 4)
The MCP cannot add the language-model libraries: editing `meta.yaml` fails dependency
resolution for both `palantir_models` and `language-model-service-api` (D-19). The
evaluation code is written and waiting in
`foundry/continuum-transforms/pending/aip_extraction.py`; it needs the libraries and
two model RIDs.

**2a. Add the libraries — DONE 2026-09-27** (`palantir_models 0.2563.0`,
`language-model-service-api 0.4123.0` on master).

**2b. Import the two models into the project (3 min). NEEDED NOW.** The evaluation is on
master (`transforms-python/src/myproject/datasets/aip_extraction.py`, GPT-4.1 nano vs
GPT-4.1). Checks fail with `Jemma:AccessWithoutImportDenied`:
`'ri.language-model-service..language-model.gpt-4-1-nano' is not referenced in the project`
(same for `...gpt-4-1`). Fix: open that file in the repository, put the cursor in each
model RID string (lines 23–24) and accept the **Import** prompt the editor offers (or
retype `ri.` and pick the model from the dropdown, which imports it). Import both into
project `Continuum`. Then **Rerun checks** on master's latest commit and confirm green.
If GPT-4.1 / GPT-4.1 nano are not in the picker, pick the closest small / frontier pair
it offers and tell the terminal agent which, so it updates `MODELS`.
Then tell the terminal agent: it builds, reports the scores, picks the kept model, and
installs the intake (6c).

**2c. Drop in the evaluation.** Copy `pending/aip_extraction.py` to
`transforms-python/src/myproject/datasets/aip_extraction.py`, set the two RIDs in
`MODELS`, commit. Build `aip_extraction.py` (all three transforms).
- **Check / record:** `aip/extraction_scores` has one `POOLED` row per model × mode.
  Copy recall, precision, LTB/LTS accuracy, replacement accuracy and citation coverage
  into `docs/AIP_LOGIC.md` → *Results*, and onto the deck's AIP evaluation slide
  (the `[__]` placeholders). `aip/extraction_*_calls` shows any call that failed to parse;
  report those, do not drop them.

**2d. Build the interactive function.**
1. Project `Continuum` → **New → AIP Logic** → `extractNoticeLines`, saved in
   `/CONTINUUM-edbe5f/Continuum/aip`.
2. **Inputs:** `noticeId` (String), `noticeText` (String).
3. **Output:** a list of structs `notice_id`, `part_number`, `last_time_buy` (Date),
   `last_time_ship` (Date), `replacement_part_number`, `source_quote` (strings unless stated).
4. **Use LLM** block, the model 2c kept, temperature 0. System prompt: `docs/AIP_LOGIC.md`
   verbatim (identical to `SYSTEM_PROMPT` in `src/continuum/extraction.py`). Task prompt:
   the schema block from `extraction.SCHEMA`, then `notice_id: {noticeId}`, a blank
   line, `Notice text:`, and `{noticeText}`.
5. **Test** with `CAAN-02OLLE763` and `raw/raw_notice_text` pages p01–p06 joined.
- **Check:** 110 rows; every `last_time_buy` = 2025-12-01; `A3P1000-1PQG208I` present
  with a quote; the caveat about qualifying a new assembly site copied verbatim.

## 3. Finish the *Approve course of action* action (step 5)
The MCP created the action (`approve-course-of-action`,
`ri.actions.main.action-type.1d070cf4-1ac9-4bf0-b391-192fb695de6e`) with its core rule:
*modify Impact Case → `status`* (dropdown: `APPROVED: …` / `OPEN`). Add the rest in
**Ontology Manager → Action types → Approve course of action** (on branch
`continuum-ontology` before merging, or on main after):
1. **Parameters → Add → Object reference** `course_of_action`, type *Course of Action*,
   required. Filter: *Course of Action.case_id = Impact Case parameter.case_id*.
2. Make `status` default to `"APPROVED: " + course_of_action.name` (Parameter →
   Default value → Object parameter property → `name`, with a static prefix), and hide it.
3. **Rules → Add rule → Create object → Procurement Request**:
   `request_id` = UUID (auto-generated) · `case_id` = Impact Case.case_id ·
   `coa_key` = course_of_action.coa_key · `program_id` = Impact Case.program_id ·
   `part_number` = Impact Case.part_number · `quantity` = course_of_action.buy_qty ·
   `estimated_cost_usd` = course_of_action.procurement_usd · `status` = `"DRAFT"` ·
   `requested_by` = current user · `requested_at` = current time ·
   `justification` = course_of_action.summary.
4. **Rules → Add rule → Create object → Engineering Review**:
   `review_id` = UUID · `case_id`, `coa_key`, `program_id`, `part_number` as above ·
   `review_type` = `"Replacement qualification / redesign"` · `status` = `"OPEN"` ·
   `opened_by` = current user · `opened_at` = current time ·
   `notes` = Impact Case.rationale.
5. **Submission criteria:** Impact Case.status equals `OPEN` (a decided case can't be
   approved twice). Save.
- **Check:** run the action on Heron / *Bridge buy + redesign (hybrid)*. The case's
  status becomes `APPROVED: Bridge buy + redesign (hybrid)`; one Procurement Request
  with quantity **500** and cost **$92,500** and one Engineering Review exist, both
  linked to the case.

## 4. Build Steve's Workshop app (step 5)
No MCP tool builds Workshop modules. The Ontology gives the app everything it needs,
so this is layout only: no logic lives in the app (D-09). About 30 minutes.
**New → Workshop module** `CONTINUUM – Obsolescence decisions`, saved in
`/CONTINUUM-edbe5f/Continuum/apps`. Dark theme. One page, three columns.

**Variables**
- `cases` = object set: all **Impact Case**, sorted by `gap_months` desc then `coverage_months` asc.
- `selectedCase` = active object of the Impact Cases table (default: first row, i.e. Heron).
- `caseCoas` = `selectedCase` → Search Around → **Courses of Action**.
- `selectedCoa` = active object of the COA table.
- `caseFlags` = `selectedCase` → Program → **Review Flags**.

**Left: "Impact cases"**: *Object table* on `cases`. Columns: `title`, `severity`,
`coverage_months`, `months_to_ltb`, `gap_months`, `status`. Conditional formatting:
`severity = CRITICAL` → text color `#FF5B1F`; everything else default.

**Middle: "Heron detail" (selected case)**
1. *Metric cards* on `selectedCase`: **On hand** `on_hand` · **Coverage** `coverage_months` (mo) ·
   **Last-time buy in** `months_to_ltb` (mo) · **Redesign** `redesign_lead_time_months` (mo) ·
   **Supply gap** `gap_months` (mo, orange when > 0).
2. *Property list*: `rationale`, `stockout_date`, `redesign_ready_date`, `notice_id`, `part_number`.
3. **Forecast range**: *Metric cards*: `window_demand_p10` · `window_demand_p50` · `window_demand_p90`,
   caption "Units needed over the redesign window (calibrated P10–P90, D-07)".
4. *Object list* on `caseFlags` (`flag_type`, `flag`), titled "Engineering review flags".

**Right: "Courses of action"**
1. *Object table* on `caseCoas`: `name`, `buy_qty`, `total_usd` (currency, 0 dp),
   `p_shortage` (percent, 0 dp), `p_shortage_under_stress` (percent, 0 dp). Active object → `selectedCoa`.
2. *Property list* on `selectedCoa`: `summary`.
3. *Button group*: **Approve course of action** → action `Approve course of action`,
   defaults: Impact Case = `selectedCase`, course_of_action = `selectedCoa`.
   Disabled when `selectedCase.status` ≠ `OPEN`.

- **Check:** Heron is the first row and orange; its middle column reads 312 · 13.8 · 5.7 ·
  24 · 10.2 and 337 / 573 / 880; the COA table shows 5,640 / $1.53M / 10% / 99%,
  0 / $1.45M / 93% / 94%, 500 / $1.55M / 14% / 18%. Approving the hybrid flips the
  status and disables the button.
- **Screenshots for the deck/video:** the module with Heron selected; the action dialog;
  the Procurement Request object after approval.

## 4a. Build `draftDecisionMemo` and show it in the app (D-21)
The second AIP Logic function: AIP writes the memo on the decision screen; code checks its numbers.
1. Project `Continuum` → **New → AIP Logic** → `draftDecisionMemo`, saved in `.../Continuum/aip`.
2. **Input:** `impactCase` (Object: *Impact Case*). **Output:** String.
3. Blocks: *Get object properties* on `impactCase`; *Search Around* → Courses of Action
   (name, buy_qty, total_usd, p_shortage, p_shortage_under_stress); then **Use LLM** with
   the kept model, temperature 0. System prompt: `docs/AIP_LOGIC.md` → *draftDecisionMemo*
   verbatim. Task prompt: the INPUT block in the same `key: value` layout as
   `continuum.memo.build_input` (money as `$1.55M`, risks as `14%`).
4. **Test** with the Heron impact case. **Check:** every number in the memo is one of those
   listed under *Expected memo for Heron*; no option is recommended; paste the memo into
   `unsupported_numbers` (or eyeball it against the list) and record the result.
5. **Workshop:** in the right column under the COA table, add a *Markdown* (or Text)
   widget titled "Decision memo (drafted by AIP)" whose content is a function-backed
   variable calling `draftDecisionMemo(selectedCase)`. Add a caption: "Numbers come from
   the options above; the engineer decides."
- **Screenshot:** the memo beside the Approve button (`docs/screenshots/workshop-memo.png`).

## 6. Turn on autonomous intake (D-23, `docs/AUTOMATION.md`)
**6a. Schedule (5 min).** Open `aip/notice_lines_auto` in Data Lineage → **Schedules** →
**Create schedule**. Trigger: *When `raw/notice_inbox` is updated*. Target: *Build
`analysis/coas` and all upstream datasets* (or select `aip/notice_intake_status`,
`clean/notice_lines`, `analysis/impact_cases`, `analysis/coas`). Save and enable.
- **Check:** release PDN2401 into the inbox (`raw/notice_inbox`, see the terminal agent's
  note); the schedule starts a build within a minute without you clicking Build.

**6b. Automate (10 min).** **New → Automate** `CONTINUUM – new impact case`.
- Condition: *Objects added to object set* → Impact Case where `severity` is CRITICAL or
  WATCH; add a second condition *Object modified* → `severity` changed to CRITICAL;
  **and a third: *Objects added to object set* → Review Flag (any type).** The demo's own
  release (PDN2401) produces a **LOW** Kite case (its buy date passed in 2024; 164 months
  of stock) plus a FINISH_CHANGE flag, so without the third condition Steve gets no
  notification on camera (D-25).
- Effect: *Notification* to yourself (Steve), title `{severity}: {title}`, body
  `{rationale}`, link to the Workshop module. Turn on email as well if offered.
- **Check:** after 6a's test build, a notification for the Kite case arrives.
- **Screenshot:** the notification (`docs/screenshots/automate-notification.png`).

**6c. Intake extraction + gate (terminal agent, after 2a).** Already written and tested
locally with a stand-in model: `foundry/continuum-transforms/pending/intake_aip.py`
(`aip/notice_lines_auto` → gate → `aip/notice_lines_accepted`, `_rejected`,
`aip/notice_intake_status` → `clean/notice_lines_live`). The agent sets `KEPT`, drops it in,
builds, and switches `analysis/impact` to `clean/notice_lines_live` only if CAAN-02OLLE763
is RELEASED with 110 accepted rows and the invariants hold by SQL afterwards (D-25).

## 5. Optional polish
- Upload the two notice PDFs to a media set `notices/notice_pdfs` so Steve can open the
  source next to the extracted rows (PDFs stay out of git).
- Add `analysis/tradeoff_curve` as a Contour chart (x `buy_qty`, y `p_shortage` and
  `expected_excess_usd`) and embed it under the COA table.
- Download the manufacturers' separate parts files (both sites block scripted downloads)
  and commit them to `data/reference/official/`: Microchip PCN portal → search
  `CAAN-02OLLE763` → `CAAN-02OLLE763_Affected_CPN_06062025.csv`; Intel
  `cdrdv2.intel.com/v1/dl/getContent/813534`. The key is already verified against the
  notices themselves (D-20); this adds a second source.
