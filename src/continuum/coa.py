"""Course-of-action (COA) quantification.

Deterministic numbers for each mitigation option, computed from the demand
distribution. AIP's job is to explain these trade-offs and draft the decision
memo; the engineer chooses. Options follow resolution types in DoD DMSMS
guidance (life-of-type buy, redesign / replacement qualification, bridge buy).

Stated assumptions (notional, surfaced in the UI rather than hidden):
- HOLDING_RATE: annual cost of storing stock (warehousing, handling, capital),
  applied to the average inventory value over the COA window.
- The bootstrap assumes recent demand persists. For multi-decade buys that is
  the weakest assumption, so each COA also reports shortage risk if the
  historical growth trend continues.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from .forecast import bootstrap_samples

BRIDGE_SERVICE_LEVEL = 0.85    # target P(no shortage) for the hybrid bridge buy
LIFETIME_SERVICE_LEVEL = 0.90  # target P(no shortage) for a life-of-type buy
HOLDING_RATE = 0.05            # per year, fraction of inventory value
ORDER_MULTIPLE = 10


def _round_up(q: float, multiple: int = ORDER_MULTIPLE) -> int:
    return int(max(0, math.ceil(q / multiple) * multiple))


def annual_growth(history: np.ndarray) -> float:
    """Demand growth per year from a log-linear fit of annual totals (clipped to +/-20%)."""
    years = len(history) // 12
    if years < 2:
        return 0.0
    totals = history[-years * 12:].reshape(years, 12).sum(axis=1).astype(float)
    if (totals <= 0).any():
        return 0.0
    slope = np.polyfit(np.arange(years), np.log(totals), 1)[0]
    return float(np.clip(np.exp(slope) - 1, -0.2, 0.2))


def trend_multiplier(growth: float, months: int) -> float:
    """Average demand multiplier over a window if `growth` per year continues."""
    t = np.arange(1, months + 1)
    return float(np.mean((1 + growth) ** (t / 12)))


def buy_outcomes(samples: np.ndarray, on_hand: int, qty: int, unit_cost: float) -> dict:
    stock = on_hand + qty
    shortfall = np.maximum(samples - stock, 0)
    excess = np.maximum(stock - samples, 0)
    return {
        "p_shortage": float((samples > stock).mean()),
        "expected_shortfall_units": float(shortfall.mean()),
        "expected_excess_units": float(excess.mean()),
        "expected_excess_usd": float(excess.mean() * unit_cost),
    }


@dataclass
class COA:
    coa_id: str
    name: str
    buy_qty: int
    procurement_usd: float
    holding_usd: float
    engineering_usd: float
    total_usd: float
    window_months: int
    p_shortage: float
    p_shortage_if_trend_continues: float
    expected_shortfall_units: float
    expected_excess_usd: float
    summary: str


def build_coas(
    history: np.ndarray,
    on_hand: int,
    unit_cost: float,
    redesign_lead_months: int,
    redesign_nre_usd: float,
    remaining_life_months: int,
    seed: int = 0,
) -> list[COA]:
    bridge = bootstrap_samples(history, redesign_lead_months, seed=seed)
    life = bootstrap_samples(history, remaining_life_months, seed=seed + 1)
    g = annual_growth(history)
    bridge_trend = bridge * trend_multiplier(g, redesign_lead_months)
    life_trend = life * trend_multiplier(g, remaining_life_months)

    def holding(stock: int, months: int) -> float:
        # Stock drains roughly linearly, so average inventory is about half of it.
        return HOLDING_RATE * unit_cost * (stock / 2) * (months / 12)

    lot_qty = _round_up(np.quantile(life, LIFETIME_SERVICE_LEVEL) - on_hand)
    lot = buy_outcomes(life, on_hand, lot_qty, unit_cost)
    lot_hold = holding(on_hand + lot_qty, remaining_life_months)

    red = buy_outcomes(bridge, on_hand, 0, unit_cost)

    bridge_qty = _round_up(np.quantile(bridge, BRIDGE_SERVICE_LEVEL) - on_hand)
    hyb = buy_outcomes(bridge, on_hand, bridge_qty, unit_cost)
    hyb_hold = holding(on_hand + bridge_qty, redesign_lead_months)

    def p_trend(samples: np.ndarray, qty: int) -> float:
        return float((samples > on_hand + qty).mean())

    years = remaining_life_months // 12
    return [
        COA("COA-1", "Life-of-type buy", lot_qty, lot_qty * unit_cost, lot_hold, 0.0,
            lot_qty * unit_cost + lot_hold, remaining_life_months, lot["p_shortage"],
            p_trend(life_trend, lot_qty), lot["expected_shortfall_units"], lot["expected_excess_usd"],
            f"Buy {lot_qty} units to cover {years} years of support at {LIFETIME_SERVICE_LEVEL:.0%} confidence. "
            f"No engineering change, but relies on a {years}-year demand forecast: if the {g:+.0%}/yr "
            f"trend continues, shortage risk rises to {p_trend(life_trend, lot_qty):.0%}."),
        COA("COA-2", "Redesign only (no buy)", 0, 0.0, 0.0, redesign_nre_usd, redesign_nre_usd,
            redesign_lead_months, red["p_shortage"], p_trend(bridge_trend, 0),
            red["expected_shortfall_units"], 0.0,
            f"Start a {redesign_lead_months}-month redesign without buying stock: "
            f"{red['p_shortage']:.0%} chance of running out before the new design is qualified."),
        COA("COA-3", "Bridge buy + redesign (hybrid)", bridge_qty, bridge_qty * unit_cost, hyb_hold,
            redesign_nre_usd, bridge_qty * unit_cost + hyb_hold + redesign_nre_usd, redesign_lead_months,
            hyb["p_shortage"], p_trend(bridge_trend, bridge_qty), hyb["expected_shortfall_units"],
            hyb["expected_excess_usd"],
            f"Buy {bridge_qty} units to bridge the {redesign_lead_months}-month redesign at "
            f"{BRIDGE_SERVICE_LEVEL:.0%} confidence and qualify a replacement in parallel. "
            f"Removes the long-horizon forecast risk; costs the redesign up front."),
    ]


def tradeoff_curve(history: np.ndarray, on_hand: int, unit_cost: float, window_months: int,
                   max_qty: int = 800, step: int = 10, seed: int = 0) -> pd.DataFrame:
    """Shortage risk vs. excess-stock cost across candidate buy quantities."""
    samples = bootstrap_samples(history, window_months, seed=seed)
    rows = [{"buy_qty": q, **buy_outcomes(samples, on_hand, q, unit_cost)} for q in range(0, max_qty + 1, step)]
    return pd.DataFrame(rows)


def coas_frame(coas: list[COA]) -> pd.DataFrame:
    return pd.DataFrame([asdict(c) for c in coas])
