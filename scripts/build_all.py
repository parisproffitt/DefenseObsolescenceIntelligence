"""Generate notional data, run the demo scenario and the forecast backtest.

Writes Foundry-ready CSVs to output/ (upload these as datasets):
  programs, assemblies, parts, bom_lines, inventory, demand_monthly,
  notice_affected_parts, impact_cases, review_flags, coas, tradeoff_curve,
  backtest_detail, backtest_summary
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from continuum.coa import build_coas, coas_frame, tradeoff_curve  # noqa: E402
from continuum.forecast import DEFAULT_SPREAD, backtest, calibrate_spread  # noqa: E402
from continuum.generate import AS_OF, build, evaluation_corpus, load_notice_parts  # noqa: E402
from continuum.impact import assess, months_between  # noqa: E402

DEMO_NOTICE = "CAAN-02OLLE763"
OUT = ROOT / "output"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    data = build()
    notice_parts = load_notice_parts()
    for name, df in {**data, "notice_affected_parts": notice_parts}.items():
        df.to_csv(OUT / f"{name}.csv", index=False)

    cases, flags = [], []
    for nid in notice_parts["notice_id"].unique():
        c, f = assess(nid, notice_parts, data, AS_OF)
        cases.append(c)
        flags.append(f)
    impact = pd.concat(cases, ignore_index=True)
    review = pd.concat(flags, ignore_index=True)
    impact.to_csv(OUT / "impact_cases.csv", index=False)
    review.to_csv(OUT / "review_flags.csv", index=False)

    # COAs for the demo case (highest-severity case on the demo notice).
    demo = impact[impact.notice_id == DEMO_NOTICE].iloc[0]
    prog = data["programs"].set_index("program_id").loc[demo.program_id]
    part = data["parts"].set_index("part_number").loc[demo.part_number]
    dem = data["demand_monthly"]
    hist = dem[(dem.program_id == demo.program_id) & (dem.part_number == demo.part_number)] \
        .sort_values("month")["units"].to_numpy()
    life = int(months_between(AS_OF, pd.Timestamp(prog.end_of_support).date()))
    coas = build_coas(hist, int(demo.on_hand), float(part.unit_cost_usd),
                      int(prog.redesign_lead_time_months), float(prog.redesign_nre_usd), life)
    cf = coas_frame(coas)
    cf.insert(0, "case_id", demo.case_id)
    cf.to_csv(OUT / "coas.csv", index=False)
    tradeoff_curve(hist, int(demo.on_hand), float(part.unit_cost_usd),
                   int(prog.redesign_lead_time_months)).to_csv(OUT / "tradeoff_curve.csv", index=False)

    corpus = evaluation_corpus()
    fitted, cal_table = calibrate_spread(corpus)
    cal_table.to_csv(OUT / "calibration_table.csv", index=False)
    if abs(fitted - DEFAULT_SPREAD) > 1e-9:
        print(f"WARNING: calibration now suggests spread={fitted}, code default is {DEFAULT_SPREAD}")
    results = []
    for label, frame, spread in (("corpus_raw", corpus, 1.0), ("corpus_calibrated", corpus, None),
                                 ("programs_calibrated", data["demand_monthly"], None)):
        detail, summary = backtest(frame, spread=spread)
        summary.insert(0, "evaluation", label)
        results.append(summary)
        if label == "corpus_calibrated":
            detail.to_csv(OUT / "backtest_detail.csv", index=False)
    summary = pd.concat(results, ignore_index=True)
    summary.to_csv(OUT / "backtest_summary.csv", index=False)

    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", 20)
    print(f"Scenario date: {AS_OF}\n")
    print("IMPACT CASES")
    print(impact[["notice_id", "program_id", "part_number", "on_hand", "forecast_monthly_rate",
                  "coverage_months", "months_to_ltb", "redesign_lead_time_months", "gap_months",
                  "severity"]].to_string(index=False))
    print("\nREVIEW FLAGS (for engineering review)")
    print(review[["notice_id", "program_id", "part_number", "related_part_number", "flag_type"]].to_string(index=False)
          if not review.empty else "none")
    print(f"\nDEMO CASE: {demo.rationale}")
    print("\nCOURSES OF ACTION")
    print(cf[["coa_id", "name", "buy_qty", "procurement_usd", "holding_usd", "engineering_usd", "total_usd",
              "p_shortage", "p_shortage_if_trend_continues"]]
          .round(3).to_string(index=False))
    print(f"\nFORECAST BACKTEST (12-month cumulative demand, held-out origins; fitted spread={fitted})")
    print(summary[["evaluation", "method", "n", "mae", "mae_vs_naive", "p10_p90_coverage"]]
          .round(3).to_string(index=False))


if __name__ == "__main__":
    main()
