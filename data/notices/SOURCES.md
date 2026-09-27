# CONTINUUM — Public Data Sources

All data is public. Real notices and part numbers; notional programs, inventory, and demand history.
The authoritative provenance register is `docs/DATA_SOURCES.md` (D-22); this file is the original search log.
Commit links and metadata only; keep the PDFs themselves inside Foundry / local (they are manufacturer documents).

## 1. End-of-life notices (the unstructured input)

| Source | Where | Format | Why it's useful |
|---|---|---|---|
| **Microchip** EOL / PCN notices | Microchip PCN portal (no login required to browse): https://www.microchip.com/en-us/support/product-change-notification — also mirrored on Digi-Key and Mouser | PDF **plus an identical .xls parts-affected list** | The .xls gives free ground truth for the eval set — no hand-labeling of part lists needed |
| **Intel / Altera FPGA** discontinuance notices (PDNs) | Intel Resource & Documentation Center (PCN collection); many mirrored on Digi-Key | PDF, multi-attachment tables of hundreds of part numbers | Long, table-heavy notices — stress-tests extraction |
| **Analog Devices** PDNs | analog.com/media/en/PCN/… | PDF, varied layouts, revisions ("Rev A: extended LTB date") | Revisions and foundry-driven EOLs add realistic messiness. **Marked proprietary — use for internal analysis only; don't show on screen or republish** |
| **NXP** discontinuation notices | Mirrored on Digi-Key (mm.digikey.com) | PDF, prose-heavy | Different template and manufacturer voice |
| **Digi-Key / Mouser PCN mirrors** | mm.digikey.com/…/medias/docus/…, mouser.com/PCN/… | PDF | One place to bulk-find notices across many manufacturers |

### Strong demo-notice candidates

1. **Microchip CAAN-02OLLE763 (Jun 6, 2025)** — EOL of selected **ProASIC3 FPGAs** (A3P1000, A3P250, A3P400, A3PE3000, …). Parts no longer offered after Dec 1, 2026. Microchip is qualifying an alternate manufacturing site and *may cancel the EOL if it succeeds* — real-world ambiguity AIP must surface rather than ignore. ProASIC3 flash FPGAs are popular in aerospace/defense designs → the most defense-relevant notice found.
   https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/7131/CAAN-02OLLE763.pdf
2. **Intel PDN2401 (Jan 15, 2024)** — discontinues **leaded (tin-lead) packages** of Cyclone II/III/IV E and MAX II/V devices; recommends migrating to lead-free equivalents. Defense programs often avoid pure-tin finishes because of tin-whisker risk, so a "just switch to lead-free" replacement is exactly the kind of compatibility concern AIP should flag for engineering review.
   https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/5787/PDN2401_Rev1.0.0.pdf
3. **Intel PDN2041 (Dec 4, 2020)** — whole FPGA/CPLD families (Arria GX, Stratix II, MAX 7000A, MAX II) with **no replacement devices available** → forces the redesign COA.
   https://media.digikey.com/pdf/PCNs/Intel/PDN2041.pdf

### Other notices already located
- Microchip ASER-31SUSF550 (ATmega/ATxmega EOL, 2023): https://www.mouser.com/PCN/Microchip_Technology_PCN_ASER_31SUSF550.pdf
- Microchip DSNO-22UTRQ751 (Feb 26, 2026): https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/8898/DSNO-22UTRQ751.pdf
- Intel PDN2312 (Nios II IP, 2023): https://cdrdv2-public.intel.com/781327/pdn2312.pdf
- NXP 202504001DN (Apr 2025): https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/6778/PDN-202504001DN.pdf
- ADI PDN 23_0089 Rev A (Tower 0.35µm process EOL, 105 items): https://www.analog.com/media/en/PCN/ADI_PDN_23_0089_Rev_A_Form.pdf
- ADI PDN 24_0069 / 24_0070 Rev A (Dongbu HiTek foundry EOL, extended LTB dates)

## 2. Policy documents (for realistic timelines in the notional data)
- Microchip EOL policy: typically ~6 months to place final orders + ~6 more for delivery.
- ADI life-cycle policy: 18 months total — 12-month last-time-buy window.

## 3. Government parts data (optional enrichment)
- **DLA PUB LOG** — public NSN ↔ part number ↔ CAGE code data, downloadable monthly from the FLIS Electronic Reading Room: https://www.dla.mil/Information-Operations/FLIS-Data-Electronic-Reading-Room/
  Use: attach real National Stock Numbers to real part numbers in the notional BOMs. Large download — only if time allows (day 2 check).

## 4. Reference (for the story, not the pipeline)
- DoD SD-22 DMSMS Guidebook
- DLA journal article on DMSMS management (25–30 yr service life vs 4–7 yr commercial support)

## Eval-set plan
- 20–25 labeled notices, deliberately varied: Microchip (PDF+XLS ground truth), Intel (long tables), ADI (revisions), NXP (prose).
- 50–100 unlabeled notices from the Digi-Key/Mouser mirrors for volume.
