"""Notice -> program impact: matching, coverage, and supply-gap math.

Everything here is deterministic: given the same notice, BOM, inventory, and
forecast, it returns the same answer, and every number can be traced to inputs.
AIP explains and drafts from these facts; it does not compute them.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date

import numpy as np
import pandas as pd

from .forecast import forecast
from .partnumbers import MatchType, match_against_notice, parse


def months_between(a: date, b: date) -> float:
    return (pd.Timestamp(b) - pd.Timestamp(a)).days / 30.4375


def add_months(d: date, months: float) -> date:
    return (pd.Timestamp(d) + pd.Timedelta(days=months * 30.4375)).date()


@dataclass
class ImpactCase:
    case_id: str
    notice_id: str
    program_id: str
    assembly_id: str
    part_number: str
    match_type: str
    replacement_part_number: str | None
    on_hand: int
    forecast_monthly_rate: float
    coverage_months: float
    months_to_ltb: float
    redesign_lead_time_months: int
    stockout_date: date
    redesign_ready_date: date
    gap_months: float
    severity: str
    rationale: str


WATCH_MARGIN_MONTHS = 12
COVERAGE_CAP_MONTHS = 999.0  # display cap for parts with ~zero recent demand


def _severity(coverage_months: float, lead_months: int, months_to_ltb: float, life_months: float) -> tuple[str, str]:
    margin = coverage_months - lead_months
    if coverage_months >= life_months:
        return "LOW", "Stock on hand covers the remaining program support life."
    if margin < 0:
        window = (f"the last-time-buy window closes in {months_to_ltb:.1f} months"
                  if months_to_ltb > 0 else "the last-time-buy window has already closed")
        return "CRITICAL", f"Stock runs out {-margin:.1f} months before a redesign could be ready, and {window}."
    if margin < WATCH_MARGIN_MONTHS:
        return "WATCH", f"A redesign could finish before stockout, but with only {margin:.1f} months of margin."
    return "MODERATE", f"A redesign could finish before stockout with {margin:.1f} months of margin; plan a transition."


def replacement_flags(notice_id: str, line, original: str, replacement: str) -> list[dict]:
    """Deterministic differences between an affected part and its listed replacement.

    Only structural facts decodable from the part numbers are flagged here.
    Electrical / thermal parameters come from datasheets (AIP extraction) and are
    always routed to engineering review; this never declares a part compatible.
    """
    a, b = parse(original), parse(replacement)
    out = []

    def flag(kind: str, text: str) -> None:
        out.append({"notice_id": notice_id, "program_id": line.program_id, "assembly_id": line.assembly_id,
                    "part_number": line.part_number, "related_part_number": replacement,
                    "flag_type": kind, "flag": text})

    if a.lead_free is False and b.lead_free is True:
        flag("FINISH_CHANGE", "Replacement changes the lead finish from tin-lead to lead-free. Pure-tin finishes "
                              "carry tin-whisker risk; requires a lead-free/tin-whisker mitigation review "
                              "before use in a high-reliability program.")
    for attr, label in (("package", "package"), ("temp_grade", "temperature grade"), ("device", "device")):
        va, vb = getattr(a, attr), getattr(b, attr)
        if va and vb and va != vb:
            flag("ATTRIBUTE_CHANGE", f"Replacement {label} differs: {va} -> {vb}.")
    if not out:
        flag("REVIEW_REQUIRED", "No differences decodable from the part number; datasheet comparison and "
                                "engineering review are still required.")
    return out


def assess(
    notice_id: str,
    notice_parts: pd.DataFrame,
    data: dict[str, pd.DataFrame],
    as_of: date,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (impact_cases, review_flags) for one notice."""
    nparts = notice_parts[notice_parts["notice_id"] == notice_id]
    ltb = nparts["last_time_buy"].iloc[0]
    bom = data["bom_lines"]
    programs = data["programs"].set_index("program_id")
    inv = data["inventory"].set_index(["program_id", "part_number"])
    dem = data["demand_monthly"]

    matches = match_against_notice(bom["part_number_as_entered"].tolist(), nparts["part_number"].tolist())
    replacements = nparts.set_index("part_number")["replacement_part_number"].to_dict()
    cases, flags = [], []
    for (_, line), m in zip(bom.iterrows(), matches):
        if m.match_type == MatchType.FAMILY_ONLY:
            flags.append({
                "notice_id": notice_id, "program_id": line.program_id, "assembly_id": line.assembly_id,
                "part_number": line.part_number, "related_part_number": m.notice_part,
                "flag_type": "FAMILY_ONLY_MATCH",
                "flag": "Same device as a discontinued part but a different ordering part number; "
                        "not on the notice. Confirm with the manufacturer.",
            })
            continue
        if m.match_type != MatchType.EXACT:
            continue

        repl = replacements.get(m.notice_part)
        repl = None if pd.isna(repl) or not str(repl).strip() else str(repl)
        if repl:
            flags.extend(replacement_flags(notice_id, line, m.notice_part, repl))

        prog = programs.loc[line.program_id]
        hist = dem[(dem.program_id == line.program_id) & (dem.part_number == line.part_number)] \
            .sort_values("month")["units"].to_numpy()
        fc, _ = forecast(hist, horizon=12, seed=0)
        rate = fc.monthly_rate
        on_hand = int(inv.loc[(line.program_id, line.part_number), "on_hand"])
        coverage = min(on_hand / rate, COVERAGE_CAP_MONTHS) if rate > 0 else COVERAGE_CAP_MONTHS
        to_ltb = months_between(as_of, ltb)
        lead = int(prog.redesign_lead_time_months)
        gap = max(0.0, lead - coverage)
        life = months_between(as_of, pd.Timestamp(prog.end_of_support).date())
        sev, why = _severity(coverage, lead, to_ltb, life)
        cases.append(ImpactCase(
            case_id=f"IC-{notice_id}-{line.program_id}-{line.part_number}",
            notice_id=notice_id, program_id=line.program_id, assembly_id=line.assembly_id,
            part_number=line.part_number, match_type=m.match_type.value,
            replacement_part_number=repl, on_hand=on_hand,
            forecast_monthly_rate=round(rate, 2), coverage_months=round(coverage, 1),
            months_to_ltb=round(to_ltb, 1), redesign_lead_time_months=lead,
            stockout_date=add_months(as_of, coverage), redesign_ready_date=add_months(as_of, lead),
            gap_months=round(gap, 1), severity=sev, rationale=why,
        ))
    order = {"CRITICAL": 0, "WATCH": 1, "MODERATE": 2, "LOW": 3}
    df = pd.DataFrame([asdict(c) for c in cases])
    if not df.empty:
        df = df.sort_values("severity", key=lambda s: s.map(order)).reset_index(drop=True)
    return df, pd.DataFrame(flags)
