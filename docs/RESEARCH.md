# Research and sources

Two research tracks shaped CONTINUUM: **the customer's problem** (how DMSMS is managed
today and what manufacturers actually publish) and **the platform** (what Foundry and AIP
provide to solve it). Every claim below was checked against the source on 2026-09-27;
where a source could not be opened, that is stated. Fictional program data is described in
[DATA_SOURCES.md](DATA_SOURCES.md) and is never implied to be real. (D-24)

## 1. Domain research

### DoD SD-22, DMSMS Guidebook: the domain source of truth
Defense Standardization Program Office, *Diminishing Manufacturing Sources and Material
Shortages: A Guidebook of Best Practices for Implementing a Robust DMSMS Management
Program* (SD-22). The [DSP DMSMS page](https://www.dsp.dla.mil/Programs/DMSMS/) states it
was **updated in January 2026** and covers electrical and mechanical parts, with results
analyzed in terms of cost, schedule and performance.

SD-22 defines the work CONTINUUM supports (quoted from the
[January 2016 edition](https://www.nasa.gov/wp-content/uploads/2023/06/dmsms-guidebook-sd-22-jan2016-tagged.pdf);
the definition is unchanged in substance in later editions as far as could be checked):

> "DMSMS management is a multidisciplinary process to identify issues resulting from
> obsolescence, loss of manufacturing sources, or material shortages; to assess the
> potential for negative impacts on schedule and/or readiness; to analyze potential
> mitigation strategies; and then to implement the most cost-effective strategy."

It organizes the work in five steps. CONTINUUM follows them rather than inventing its own:

| SD-22 step | SD-22 says | CONTINUUM |
|---|---|---|
| Prepare | Management plan, team, processes, access to data | Ontology, pipelines and checks built once; notices and BOMs connected |
| Identify | "Identify items with immediate or near-term obsolescence issues" | AIP reads the notice; code matches it to every BOM; autonomous intake (D-23) |
| Assess | "Identify and prioritize the items and assemblies most at risk" for readiness | Impact cases: coverage, supply gap, severity, ranked |
| Analyze | "Develop a set of potential DMSMS resolutions… Determine the most cost-effective resolution" | Calibrated demand range; three costed courses of action; AIP memo |
| Implement | "Budget, fund, contract or arrange for, schedule, and execute the selected resolutions" | Dana approves; one Action opens the purchase request and engineering review |

Resolution options named in SD-22 and used here: life-of-need (life-of-type) procurement,
alternative or substitute items, redesign. The notice-driven, reactive case shown in the
demo sits inside SD-22's broader proactive practice (monitoring before notices arrive),
which is where the autonomous intake points.

### DoD Engineering of Defense Systems Guidebook
OUSD(R&E), [Engineering of Defense Systems Guidebook](https://www.cto.mil/wp-content/uploads/2024/10/Eng-Def-Sys-Change2-7October2024-v3.pdf)
(February 2022, Change 2, October 2024). §3.1.3.2 calls for a plan "to proactively manage
and mitigate Parts Management and Diminishing Manufacturing Sources and Material Shortages
(DMSMS) issues across the life cycle" and to "include DMSMS resilience considerations" in
designs. **Used for:** DMSMS is a systems-engineering concern (design, technical data,
refresh), not only procurement, which is why the redesign option and the engineering
review are first-class in the workflow.

### Sandborn, Prabhakar & Ahmad (2011)
P. Sandborn, V. Prabhakar, O. Ahmad, "Forecasting electronic part procurement lifetimes to
enable the management of DMSMS obsolescence," *Microelectronics Reliability* 51(2):392–399,
2011. [doi:10.1016/j.microrel.2010.08.005](https://doi.org/10.1016/j.microrel.2010.08.005).
Uses historical obsolescence data to forecast when parts become non-procurable.
**Used for:** precedent for data-driven forecasting in DMSMS. **Not claimed:** it forecasts
*when a part goes obsolete*; CONTINUUM forecasts *how many units a program will consume*
after the notice. The paper supports the approach, not this specific model.

### Mastrangelo, Olson & Summers (2021)
C. M. Mastrangelo, K. A. Olson, D. M. Summers, "A risk-based approach to forecasting
component obsolescence," *Microelectronics Reliability* 127:114330, 2021.
[doi:10.1016/j.microrel.2021.114330](https://doi.org/10.1016/j.microrel.2021.114330).
A Weibull-based conditional-probability method for the chance a component becomes obsolete
in a time window. **Used for:** framing DMSMS decisions as probabilities, which is why
CONTINUUM reports a calibrated range (337 / 573 / 880 units) and a chance of running short
per option instead of one "buy exactly N" answer (D-06, D-07).

### SAE STD0016A
SAE International, [STD0016A, *Standard for Preparing a DMSMS Management Plan*](https://www.sae.org/standards/content/std0016a/)
(2023). The industry standard for DMSMS management plans (the SD-22 "Prepare" step).
**Used for:** confirming the workflow and terms are established practice. Not read in
full (paywalled); cited for its existence and scope only.

### Manufacturer notices and policies
- **Microchip** [Product Change Notifications](https://www.microchip.com/en-us/support/product-change-notification)
  and its PCN/EOL notification policy: the source of the demo notice CAAN-02OLLE763.
  (The policy PDF blocks automated readers; its notice types are not quoted here.)
- **Intel** PDN2401: the second, table-heavy notice (DATA_SOURCES.md).
- **Analog Devices** [Product Life Cycle Information](https://www.analog.com/en/support/customer-service-resources/sales/product-life-cycle-information.html):
  a discontinuance notice includes, at a minimum, "PDN Number, Publication Date, Last Time
  Buy Date, Last Time Ship Date, Reason for Discontinuance, … models affected, Recommended
  Replacement Parts, Supporting Information, Contact Information"; ADI gives a 12-month
  last-time-buy period and ships for up to 18 months from the notice. **Used for:** the
  extraction schema (notice ID, dates, affected parts, replacements, caveats) matches what
  manufacturers commit to publish. Gap noted: *reason for discontinuance* is not yet
  extracted; it is a next step.
- **Analog Devices HMC252** ([product page](https://www.analog.com/en/products/hmc252.html)):
  all variants obsolete, HMC252A "recommended for new designs". A research example of real
  lifecycle and replacement data; not used in the scenario.

### Defense Standardization Program Journal (2014)
"DMSMS Management: The Key to Higher Availability and Lower Costs," *DSP Journal*, Jul/Sep
2014, p. 4 ([PDF](https://www.dsp.dla.mil/Portals/26/Documents/Publications/Journal/140901-DSPJ.pdf)):
"extended service life of 25 to 30 years, run counter to the now 4- to 7-year support cycle".
The figures on the problem slide and cover.

## 2. Platform and product research
| Source | Used for |
|---|---|
| [Foundry platform overview](https://www.palantir.com/docs/foundry/platform-overview/overview) | Pipelines, Code Repositories, schedules, lineage |
| [Ontology overview](https://www.palantir.com/docs/foundry/ontology/overview) | Object types, links, Actions as the decision write-back |
| [AIP overview](https://www.palantir.com/docs/foundry/aip/overview) and [AIP Logic](https://www.palantir.com/docs/foundry/logic/overview) | extractNoticeLines, draftDecisionMemo, model choice |
| [Automate AIP Logic](https://www.palantir.com/docs/foundry/logic/aip-logic-integration-automate) | Autonomous intake and notifications (D-23) |
| [Palantir Foundry impact studies](https://www.palantir.com/palantir-foundry/impact/) | How deployments are framed: a user, a decision, a measured outcome (closing slide metrics) |
| [Interviewing at Palantir: our advice](https://blog.palantir.com/interviewing-at-palantir-advice-from-palantirians-88444a90e7c4) | Decompose the problem, learn the domain, explain the reasoning |
