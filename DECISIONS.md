# Design Decision Log

Format: **Decision** · **Why** (how it serves the operator) · **Alternative** · **Why rejected**.
Newest decisions are appended at the bottom.

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
