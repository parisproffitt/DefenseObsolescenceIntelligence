"""Phase 3: the decision logic, running in Foundry on the clean tables.

Ports impact.py, forecast.py and coa.py unchanged (vendored in myproject.continuum),
so Foundry produces exactly the numbers the tests pin (D-09: code computes, AIP explains).
"""

import numpy as np
import pandas as pd
from transforms import expectations as E
from transforms.api import Check, Input, Output, transform

from myproject.continuum.coa import build_coas, coas_frame, tradeoff_curve
from myproject.continuum.forecast import backtest, calibrate_spread, forecast
from myproject.continuum.generate import AS_OF, evaluation_corpus
from myproject.continuum.impact import assess, months_between
from myproject.datasets.paths import ANALYSIS, CLEAN

COA_SEVERITIES = ("CRITICAL",)  # cases that get courses of action computed


def _pk(col):
    return Check(E.primary_key(col), f"Primary key {col}", on_error="FAIL")


def _history(demand, program_id, part_number):
    d = demand[(demand.program_id == program_id) & (demand.part_number == part_number)]
    return d.sort_values("month")["units"].to_numpy()


@transform.using(
    impact_cases=Output(f"{ANALYSIS}/impact_cases", checks=_pk("case_id")),
    review_flags=Output(f"{ANALYSIS}/review_flags", checks=_pk("flag_id")),
    programs=Input(f"{CLEAN}/programs"),
    bom_lines=Input(f"{CLEAN}/bom_lines"),
    inventory=Input(f"{CLEAN}/inventory"),
    demand_monthly=Input(f"{CLEAN}/demand_monthly"),
    notice_lines=Input(f"{CLEAN}/notice_lines"),
)
def impact(impact_cases, review_flags, programs, bom_lines, inventory, demand_monthly, notice_lines):
    data = {
        "programs": programs.pandas(),
        "bom_lines": bom_lines.pandas(),
        "inventory": inventory.pandas(),
        "demand_monthly": demand_monthly.pandas(),
    }
    parts = notice_lines.pandas()
    cases, flags = [], []
    for nid in sorted(parts["notice_id"].unique()):
        c, f = assess(nid, parts, data, AS_OF)
        cases.append(c)
        flags.append(f)
    cases = pd.concat(cases, ignore_index=True)
    flags = pd.concat(flags, ignore_index=True)

    # Forecast range over each case's redesign window: same sampler and seed as the
    # COA bridge buy, so the range Dana sees and the buy quantity agree.
    rng = []
    for c in cases.itertuples():
        fc, _ = forecast(_history(data["demand_monthly"], c.program_id, c.part_number),
                         horizon=int(c.redesign_lead_time_months), seed=0)
        rng.append((round(fc.p10, 1), round(fc.p50, 1), round(fc.p90, 1)))
    cases["window_demand_p10"], cases["window_demand_p50"], cases["window_demand_p90"] = zip(*rng)
    cases.insert(1, "status", "OPEN")
    cases["title"] = cases["program_id"].str.title() + " · " + cases["part_number"] + " · " + cases["severity"]

    flags.insert(0, "flag_id", flags["notice_id"] + "|" + flags["program_id"] + "|"
                 + flags["part_number"] + "|" + flags["flag_type"])
    impact_cases.write_table(cases)
    review_flags.write_table(flags)


@transform.using(
    coas=Output(f"{ANALYSIS}/coas", checks=_pk("coa_key")),
    tradeoff=Output(f"{ANALYSIS}/tradeoff_curve"),
    impact_cases=Input(f"{ANALYSIS}/impact_cases"),
    programs=Input(f"{CLEAN}/programs"),
    parts=Input(f"{CLEAN}/parts"),
    demand_monthly=Input(f"{CLEAN}/demand_monthly"),
)
def courses_of_action(coas, tradeoff, impact_cases, programs, parts, demand_monthly):
    cases = impact_cases.pandas()
    progs = programs.pandas().set_index("program_id")
    cost = parts.pandas().set_index("part_number")["unit_cost_usd"]
    dem = demand_monthly.pandas()
    frames, curves = [], []
    for c in cases[cases.severity.isin(COA_SEVERITIES)].itertuples():
        prog = progs.loc[c.program_id]
        hist = _history(dem, c.program_id, c.part_number)
        life = int(months_between(AS_OF, pd.Timestamp(prog.end_of_support).date()))
        cf = coas_frame(build_coas(hist, int(c.on_hand), float(cost[c.part_number]),
                                   int(prog.redesign_lead_time_months), float(prog.redesign_nre_usd), life))
        cf.insert(0, "case_id", c.case_id)
        cf.insert(0, "coa_key", cf["case_id"] + "|" + cf["coa_id"])
        frames.append(cf)
        tc = tradeoff_curve(hist, int(c.on_hand), float(cost[c.part_number]), int(prog.redesign_lead_time_months))
        tc.insert(0, "case_id", c.case_id)
        curves.append(tc)
    coas.write_table(pd.concat(frames, ignore_index=True))
    tradeoff.write_table(pd.concat(curves, ignore_index=True))


@transform.using(
    summary=Output(f"{ANALYSIS}/backtest_summary"),
    calibration=Output(f"{ANALYSIS}/calibration_table"),
    demand_monthly=Input(f"{CLEAN}/demand_monthly"),
)
def forecast_evaluation(summary, calibration, demand_monthly):
    """Held-out backtest (D-07): calibrate the spread on months 36-48, score on 51-60."""
    corpus = evaluation_corpus()
    _, table = calibrate_spread(corpus)
    results = []
    for label, frame, spread in (("corpus_raw", corpus, 1.0), ("corpus_calibrated", corpus, None),
                                 ("programs_calibrated", demand_monthly.pandas(), None)):
        _, s = backtest(frame, spread=spread)
        s.insert(0, "evaluation", label)
        results.append(s)
    out = pd.concat(results, ignore_index=True)
    out["p10_p90_coverage"] = out["p10_p90_coverage"].astype(float).replace({np.nan: None})
    summary.write_table(out)
    calibration.write_table(table)
