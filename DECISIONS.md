# Design Decision Log

Format: **Decision** · **Why** (how it serves the operator) · **Alternative** · **Why rejected**.
Newest decisions are appended at the bottom.

## Reading guide

| Question | Decisions |
|---|---|
| Why this problem, and who has it? | D-01 |
| How is the data sourced and structured? | D-02, D-03, D-11, D-12, D-13, D-16 |
| Where is ML used, and how is it validated? | D-06, D-07, D-08, D-10 |
| Where is AIP used, and how is it evaluated? | D-14, D-19 |
| What is AI deliberately not allowed to do? | D-04, D-05, D-09 |
| How does the operator act on a decision? | D-17, D-18 |
| What was changed after a first approach failed a check? | D-07 (calibration), D-08 (holding cost), D-10 (fitted trend), D-16 (revises D-12) |
| What could only be done by hand, and why? | D-15, D-19 |

---

### D-01 · Problem: DMSMS obsolescence, not a flashier mission
- **Decision:** Build around a DMSMS engineer turning a manufacturer end-of-life notice into a program decision.
- **Why:** A real, recurring, consequential decision with an established DoD process (SD-22, Health Status Reports, defined resolution options) that still runs on PDFs and manual cross-referencing.
- **Alternative:** Drone/ISR fusion, disaster logistics, flight-test anomaly investigation.
- **Why rejected:** Crowded themes, mostly fabricated data, or overlap with my existing projects (SENTINEL, GRIDLOCK).

### D-02 · Data: real notices and part numbers, notional programs
- **Decision:** Use real published EOL notices (Microchip CAAN-02OLLE763, Intel PDN2401) and their real affected part numbers. Programs, BOMs, inventory, costs, and demand history are notional.
- **Why:** Program sustainment data is not public. Using real notices keeps the hardest part (messy documents, real OPN formats) honest.
- **Alternative:** Fully synthetic notices and parts.
- **Why rejected:** It would test nothing real, and reviewers could not trust any extraction number.
- **Guardrail:** Notional non-notice parts use an obvious `NTL-` prefix so no real part's lifecycle status is misrepresented. Nothing from any employer is used.

### D-03 · Scenario replay at the notice's issue date
- **Decision:** The demo runs "as of" 2025-06-10, days after CAAN-02OLLE763 was issued.
- **Why:** The notice's last-time-buy date (2025-12-01) has since passed. Replaying from the issue date keeps every date real instead of inventing a future notice.
- **Alternative:** Edit the notice's dates to be in the future.
- **Why rejected:** It would falsify a real document.

### D-04 · Part matching is deterministic, not an LLM step
- **Decision:** Match BOM lines to notice OPNs by exact identity after normalization. Same-device/different-OPN hits become a `FAMILY_ONLY_MATCH` review flag, never a match.
- **Why:** The ProASIC3 notice says "A3P1000 device families" but only discontinues the PQ208 package. Petrel's A3P1000 in a 484-ball FBGA is **not** affected. Family-level or semantic matching gets this wrong; exact matching is correct, free, and auditable.
- **Alternative:** Ask AIP which BOM parts a notice affects.
- **Why rejected:** Identity questions have one right answer, and an LLM adds cost and error with no benefit. AIP's job is extracting the OPN list from the PDF, which is then checked against ground truth.

### D-05 · AIP flags replacement differences; it never declares compatibility
- **Decision:** Structural differences decodable from part numbers (finish, package, temperature grade) are flagged deterministically. Datasheet parameters are extracted by AIP with citations. Every replacement goes to engineering review.
- **Why:** Form-fit-function compatibility is an engineering judgment with safety consequences. Example: Intel's PDN2401 replacements switch from tin-lead to lead-free finish, which is a tin-whisker review item for high-reliability programs, even though the part is otherwise "pin-compatible."
- **Alternative:** Let AIP decide whether the replacement is compatible.
- **Why rejected:** Insufficient traceability; risk of an unsupported "compatible" call.

### D-06 · Forecast cumulative demand as a distribution, not a point
- **Decision:** A bootstrap over the last 24 months produces a distribution of cumulative demand over the decision window. Buy quantities are chosen at a stated service level.
- **Why:** The operator's question is "how many units will we consume before the redesign is ready, and how sure are we?" A single number hides the risk the buy decision is about.
- **Alternative:** Point forecasts (moving average, Croston/SBA).
- **Why rejected:** Kept as baselines, but they cannot express shortage vs. excess-stock risk.

### D-07 · Calibrate the planning range, and measure it out of sample
- **Decision:** Scale the bootstrap spread by 1.35, fitted on early backtest origins (months 36–48) of a 200-series evaluation corpus. Report results on later, held-out origins (months 51–60).
- **Why:** The raw bootstrap was overconfident. Its P10–P90 range held only 69% of held-out outcomes against an 80% target. Calibrated, it holds 82%.
- **Alternative:** Tune on the 11 program series only.
- **Why rejected:** About 50 forecasts give coverage a standard error of roughly 6 points, too noisy to tell calibration from luck. That first attempt looked calibrated in-sample (80%) and fell to 67% out of sample.
- **Honest limitation:** On point accuracy, the bootstrap median does not beat a plain average across the corpus (MAE ratio 1.05); it is slightly better on the program series (0.95). Its value is the calibrated range, not a sharper point estimate. The corpus is synthetic, so this validates the method's machinery, not real-world accuracy. It must be re-run on real demand history before deployment.
- **Also:** The generator has no autocorrelation, so block size cannot be validated on this data. `block=1` is the default; longer blocks remain an option for real, batch-driven repair demand.

### D-08 · COAs carry holding cost and a trend-sensitivity check
- **Decision:** Each course of action reports procurement, holding (5%/yr of average inventory value, a stated assumption), and engineering cost, plus shortage risk under flat demand **and** under a demand-growth stress scenario (D-10).
- **Why:** Without these, a 17-year life-of-type buy looks cheapest and safe. With them, it costs about the same as the hybrid ($1.53M vs $1.55M), and its shortage risk jumps from 10% to 99% if demand grows 5%/yr as the fleet ages. The hybrid moves only from 14% to 18%. That is the real reason an engineer would choose a bridge buy plus redesign.
- **Alternative:** Rank COAs by procurement cost only.
- **Why rejected:** It hides the long-horizon forecast bet that dominates the decision.

### D-09 · Numbers are computed in code; AIP explains them
- **Decision:** Coverage, gap, severity, buy quantities, and risk are computed deterministically (Python transforms and functions). AIP drafts the explanation and decision memo from those values.
- **Why:** Every number shown to the engineer must trace back to its inputs.
- **Alternative:** Have the LLM compute or estimate figures in its narrative.
- **Why rejected:** Unverifiable arithmetic in a procurement decision.

### D-10 · Stress-test demand growth with a stated scenario, not a fitted trend
- **Decision:** Shortage risk under growth uses an explicit, adjustable assumption (`STRESS_GROWTH = 5%/yr`), not a trend estimated from history.
- **Why:** My first version used a fitted trend. For Heron it returned +17%/yr, while the generator's true trend is +6%. In a 300-series simulation, both a log-linear fit and a Poisson regression were unbiased but off by about 11 points (RMSE) on 6 years of lumpy demand. That is too noisy to put in a procurement decision.
- **Alternative:** Use the fitted trend, or hide growth risk entirely.
- **Why rejected:** The first overstates risk from noise; the second hides the biggest weakness of a multi-decade buy. A stated scenario is transparent, and the engineer can change it.

### D-11 · Ontology modeling: one object per real-world thing, stable string keys
- **Decision:** Ten object types, each backed by one dataset with a unique string primary key; composite keys are joined with `|` (e.g. `notice_line_id = CAAN-02OLLE763|A3P1000-1PQG208I`). Monthly demand stays a dataset, not an object type.
- **Why:** The engineer navigates *things* (a program, a part, an impact case); a key that reads as its meaning makes links auditable by eye. Demand is 800+ numeric rows only ever aggregated; as objects they would add clutter without a workflow that acts on a single month.
- **Alternative:** Row-number IDs; an object per demand month.
- **Why rejected:** Row numbers change when data is regenerated and break links; per-month objects serve no decision.
- **Also:** Impact cases carry a `status` (starts `OPEN`) so the Ontology Action has a property to write when the engineer decides.

### D-12 · Clean the data inside Foundry, from deliberately messy raw exports
- **Decision:** Upload raw, spreadsheet-style exports (`output/raw/`: odd headers, padded and lower-case part numbers, a Digi-Key `-ND` suffix, text dates and `$` amounts) and clean them in a Pipeline Builder pipeline. The Python code stays as the reference implementation, and a test proves the cleaning rules reproduce it exactly.
- **Why:** A real customer hands over exports like these, not tidy tables. Doing the cleaning in Foundry puts raw → clean in the lineage graph, where it can be inspected, and makes the exact-match rule (D-04) a visible join (`bom_notice_matches`, 5 rows).
- **Alternative:** Upload the already-clean CSVs.
- **Why rejected:** Foundry would only store files; the integration work would be invisible and untestable on the platform.

### D-13 · Verify ground truth against the manufacturers' official parts lists
- **Decision:** The 230 affected part numbers were read from the notice PDFs. Before any accuracy claim, they are cross-checked against Microchip's official affected-parts CSV and Intel's OPN list, committed under `data/reference/official/`.
- **Why:** An extraction accuracy number is only as good as its answer key.
- **Alternative:** Trust the transcription.
- **Why rejected:** "How do you know your ground truth is right?" deserves a better answer than "I read it carefully."

### D-14 · AIP extraction is scored field by field, with the same normalizer as matching
- **Decision:** `eval_extraction.score` grades AIP's notice output against the real parts lists: part recall and precision, LTB/LTS date accuracy, replacement accuracy, and citation coverage, per notice and pooled. Part numbers pass through `normalize()` first. The prompt (`docs/AIP_LOGIC.md`) forbids invented parts, dates or replacements, and requires a verbatim quote per row.
- **Why:** Recall answers "did it miss a part that affects a program?" (the costly error); precision answers "did it invent one?". Normalizing first means the score measures extraction, not whitespace or case. Verbatim quotes let the engineer check any row in seconds.
- **Alternative:** An LLM-as-judge rating of the extraction, or one overall accuracy number.
- **Why rejected:** The answer key is exact, so exact comparison is cheaper and unambiguous; one number would hide whether errors are misses or inventions.

### D-15 · What the Palantir MCP can build, and what stays manual
- **Decision:** Build everything the `palantir` MCP server can reach through it, and write exact click-paths for the rest into `docs/MANUAL_STEPS.md`. Tools available on 2026-09-26 (93), grouped by the definition-of-done step they serve:
  - **Step 1 (data):** `create_python_transforms_code_repository`, `clone_code_repository_locally`, `get_repository_context`, `get_python_transforms_documentation`, `build_datasets`, `get_build_status`, `get_job_status`, `search_dataset_builds`, `create_and_write_to_foundry_dataset` (CSV upload), `run_sql_query_on_foundry_dataset`, `get_dataset_stats`, `get_foundry_dataset_schema`, `list_dataset_files`, `list_resources_in_foundry_folder`, `search_foundry_resources`, `search_foundry_projects`, `move_foundry_resources`, `get_resource_graph`, `create_code_repository_pull_request` and PR tools.
  - **Step 2 (Ontology):** `create_or_update_foundry_object_type`, `create_or_update_foundry_link_type`, `view_/delete_foundry_object_type`, `view_/delete_foundry_link_type`, `get_foundry_ontology_rid`, `search_foundry_ontology`, `query_ontology_objects`, `aggregate_ontology_objects`, global branch / proposal tools.
  - **Step 3 (logic):** the same transforms tools as step 1 (`impact`, `forecast`, `coa` run as Python transforms).
  - **Step 4 (AIP):** no tool creates or runs an AIP Logic function. Nearest: TypeScript / Python functions (`get_typescript_v2_functions_documentation`, `publish_function`, `search_foundry_functions`), `get_ml_documentation`, media-set tools (`get_media_set`, `list_media_items`, `get_media_item_metadata`), documentation search.
  - **Step 5 (Action + app):** `create_or_update_foundry_action_type`, `view_/delete_foundry_action_type`. No Workshop tool; OSDK / Developer Console tools (`create_or_update_ontology_sdk_version`, `convert_to_osdk_react`, `connect_to_dev_console_app`) could build a custom app instead.
  - **Not used:** compute modules, REST data sources and webhooks, health checks, network egress, custom widgets, SDK package install.
- **Why:** The brief asks for a Foundry build, and every choice must be explainable. Knowing up front which steps the tools reach avoids pretending a step is automated when it is not.
- **Alternative:** Build everything by hand in the Foundry UI, or skip what the MCP cannot reach.
- **Why rejected:** Hand-building loses the repo mirror and reproducibility; skipping leaves the demo incomplete.

### D-16 · Clean in Python transforms that call the matching code's own `normalize()` (revises D-12)
- **Decision:** The raw → clean step runs as Python transforms in the `continuum-transforms` repository, not in Pipeline Builder. The raw exports are generated in Foundry by a transform (`generate.py` + `raw.py`, fixed seed) and written as CSV files, like a file drop. Each clean transform calls `partnumbers.normalize()` and declares its primary key as a FAIL check. The real notice lists are uploaded as-is (`raw_notices`, `raw_notice_parts`) because they are source data, not something to generate.
- **Why:** Cleaning and matching now share one function, so a part number that cleans one way cannot match another way; the tests that pin `normalize()` also pin the Foundry cleaning. A duplicate key fails the build before it can reach the Ontology. And the MCP can create transforms but not Pipeline Builder pipelines, so this path is reproducible from the repo.
- **Alternative:** Pipeline Builder with trim / upper-case / regex boards (D-12's plan), or uploading the clean CSVs.
- **Why rejected:** Pipeline Builder would re-implement the normalizer in a second place that tests cannot reach. Uploading clean files hides the integration work. The lineage graph still shows raw → clean → analysis, which is what D-12 wanted.

### D-17 · Ontology built on a global branch, merged by a person
- **Decision:** All object and link types are created through the MCP on one global branch (`continuum-ontology`) and reach the main Ontology only when Paris approves its proposal. Impact Case's title is a readable `title` ("Heron · A3P1000-1PQG208I · CRITICAL") rather than the raw `case_id`. Review Flag links to Program and Part as well as Notice, as the README's Ontology table says.
- **Why:** An Ontology change is shared state other apps can depend on, so the same rule as the product applies: the machine proposes, a person approves. The readable title is what Dana scans in a list; the key stays the stable `case_id`. Linking flags to programs lets the Heron page show its own flags.
- **Alternative:** Write straight to the main Ontology; title by `case_id`; link flags only to notices.
- **Why rejected:** No review step for a shared model; `IC-CAAN-02OLLE763-HERON-A3P1000-1PQG208I` is unreadable in a list; flags would be unreachable from the program page.
- **Also:** Foundry prefixes every id with the namespace `one4jwoo.`; `foundry/ONTOLOGY.md` records the ids exactly.

### D-18 · The engineer's decision is one Action that writes three records
- **Decision:** *Approve course of action* takes an Impact Case and the chosen Course of Action. It sets the case's `status` (e.g. `APPROVED: Bridge buy + redesign (hybrid)`), creates a **Procurement Request** (quantity and estimated cost copied from the COA) and creates an **Engineering Review** (replacement qualification / redesign). The two new object types are backed by empty, typed datasets in `ontology/` that only the action fills. The MCP creates the action with its core rule (modify Impact Case); the two create-object rules are added in Ontology Manager (`docs/MANUAL_STEPS.md`) because the MCP's action tool takes a single rule and there is no MCP tool for a function repository.
- **Why:** The decision is the point where the system hands off to people who act on it: buyers and engineers. Writing all three in one transaction means a case can't read "approved" without the purchase and the review that make it real. Copying numbers from the COA, rather than typing them, keeps them traceable to code (D-09).
- **Alternative:** A status field only, or a free-text approval note; or a TypeScript function-backed action.
- **Why rejected:** A status alone leaves the follow-up work in email. A function-backed action is the stronger long-term design (it could also validate that the COA belongs to the case) but cannot be created or published through the tools available; it is noted as the next step.

### D-19 · One extraction harness for evaluation and for AIP Logic; the model run waits on a UI step
- **Decision:** The prompt, page chunking and JSON parsing live in `continuum/extraction.py` (unit-tested with a stub model). A Foundry transform binds two AIP models to it and scores every run with `eval_extraction.score`, in two modes: the whole notice in one call, and one call per page with page 1 (where the dates are) as context. The input is the PDFs' text layer, uploaded as `raw/raw_notice_text`; it contains all 230 ground-truth part numbers verbatim, so the score measures the model, not OCR. The AIP Logic function `extractNoticeLines` uses the same prompt text, so the evaluation numbers describe it.
- **Why:** The same code path for testing and production means the number on the slide describes the thing in the app. Scoring both modes answers AIP_LOGIC.md's open question (is chunking needed for the 120-part Intel notice?) with data instead of a guess. A failed or unparsable call is recorded as a row, never silently dropped, because a silent drop would look like a recall problem.
- **Alternative:** Build the evaluation inside AIP Logic by hand and read scores off the debugger; or extract the PDFs inside Foundry with Document Intelligence.
- **Why rejected:** Hand runs are not reproducible and cannot be re-scored when the prompt changes. Document Intelligence adds a second extraction layer to debug, and here the text layer is already complete.
- **Honest status (2026-09-26):** No model has been run yet, so there are no AIP numbers. Adding `palantir_models` / `language-model-service-api` by editing `meta.yaml` fails dependency resolution in this repository (both names tried); the Libraries panel has to add them. The transform is ready in `foundry/continuum-transforms/pending/`; `docs/MANUAL_STEPS.md` step 2 covers the rest. The deck keeps `[__]` placeholders until real numbers exist.
