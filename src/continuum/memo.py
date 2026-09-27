"""Decision memo drafted by AIP (D-21): the prompt, its input block, and a numeric guardrail.

AIP Logic `draftDecisionMemo` reads an Impact Case and its Courses of Action from the
Ontology and writes a one-page memo for the program office. The model only arranges
words around values it is given (D-09). `unsupported_numbers` checks that promise:
every number in the memo must appear in the input block, or the memo is not shown.
"""

from __future__ import annotations

import re
from typing import Iterable, Mapping

SYSTEM_PROMPT = """\
You draft a short decision memo for a defense program office about one obsolete part.
Rules:
1. Use only the facts in the INPUT block. Copy every number exactly as written there.
   Never compute, round, convert or estimate a new number.
2. Do not recommend or choose a course of action. Present each option's quantity, cost
   and chance of running short (flat demand and under the stated stress), then state
   the decision the engineer must make and the date it must be made by.
3. If a caveat is given, quote it verbatim.
4. Never state that a replacement part is compatible.
5. Three headed sections: Situation, Options, Decision needed. Under 220 words.
Return the memo as plain text."""

_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def _usd(x: float) -> str:
    return f"${x / 1e6:.2f}M" if x >= 1e6 else f"${x:,.0f}"


def build_input(case: Mapping, coas: Iterable[Mapping], caveats: Iterable[str] = ()) -> str:
    """Render Ontology property values as the only facts the model may use."""
    lines = [
        f"program: {case['program_id']}",
        f"part_number: {case['part_number']}",
        f"notice_id: {case['notice_id']}",
        f"severity: {case['severity']}",
        f"units_on_hand: {case['on_hand']}",
        f"stock_coverage_months: {case['coverage_months']:.1f}",
        f"months_to_last_time_buy: {case['months_to_ltb']:.1f}",
        f"redesign_lead_time_months: {case['redesign_lead_time_months']}",
        f"supply_gap_months: {case['gap_months']:.1f}",
        f"last_time_buy_date: {case['last_time_buy']}",
    ]
    for c in coas:
        lines.append(
            f"option: {c['name']} | buy_units: {c['buy_qty']:,} | total_cost: {_usd(c['total_usd'])}"
            f" | shortage_risk_flat: {_pct(c['p_shortage'])}"
            f" | shortage_risk_demand_plus_5pct_per_year: {_pct(c['p_shortage_under_stress'])}"
        )
    for q in caveats:
        lines.append(f"caveat: \"{q}\"")
    return "INPUT\n" + "\n".join(lines)


def _numbers(text: str) -> set[str]:
    return {n.replace(",", "").rstrip(".") for n in _NUMBER.findall(text)}


def unsupported_numbers(memo: str, input_block: str) -> list[str]:
    """Numbers in the memo that do not appear in the input. Empty list = memo may be shown."""
    return sorted(_numbers(memo) - _numbers(input_block))
