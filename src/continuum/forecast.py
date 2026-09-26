"""Demand forecasting for intermittent spare-parts demand.

The operational question is not "what is next month's demand" but "how many
units will this program consume over the next H months, and how uncertain is
that?" Every method therefore forecasts *cumulative* demand over a horizon.

Methods
- naive_mean:   full-history monthly mean x H (what a spreadsheet often does)
- recent_mean:  trailing 12-month mean x H
- sba:          Syntetos-Boylan Approximation (Croston variant for intermittent demand)
- bootstrap:    moving-block bootstrap of recent months -> full distribution;
                the only method that yields a planning range.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


def naive_mean(history: np.ndarray, horizon: int) -> float:
    return float(np.mean(history) * horizon)


def recent_mean(history: np.ndarray, horizon: int, window: int = 12) -> float:
    return float(np.mean(history[-window:]) * horizon)


def sba(history: np.ndarray, horizon: int, alpha: float = 0.1) -> float:
    """Syntetos-Boylan Approximation: smoothed size / smoothed interval, bias-corrected."""
    nz = np.flatnonzero(history)
    if len(nz) == 0:
        return 0.0
    size = float(history[nz[0]])
    interval = float(nz[0] + 1)
    last = nz[0]
    for i in nz[1:]:
        size = alpha * history[i] + (1 - alpha) * size
        interval = alpha * (i - last) + (1 - alpha) * interval
        last = i
    return float((1 - alpha / 2) * size / interval * horizon)


# Chosen by rolling-origin backtest (see DECISIONS.md, D-07). SPREAD widens the
# distribution around its median; the raw bootstrap (SPREAD=1) was overconfident.
DEFAULT_WINDOW = 24
DEFAULT_BLOCK = 1
DEFAULT_SPREAD = 1.35   # fitted by calibrate_spread on evaluation_corpus(); see D-07


def bootstrap_samples(
    history: np.ndarray,
    horizon: int,
    window: int = DEFAULT_WINDOW,
    block: int = DEFAULT_BLOCK,
    n: int = 4000,
    seed: int = 0,
    spread: float | None = None,
) -> np.ndarray:
    """Cumulative-demand samples via moving-block bootstrap over the recent window.

    Restricting to the recent window lets the level follow fleet aging instead of
    the long-run mean. Blocks (block > 1) preserve short-run clustering such as
    batched repairs. `spread` scales deviations from the median; it is fitted so
    the P10-P90 range holds ~80% of outcomes on held-out backtest origins.
    """
    rng = np.random.default_rng(seed)
    recent = np.asarray(history[-window:], dtype=float)
    block = max(1, min(block, len(recent)))
    starts = np.arange(len(recent) - block + 1)
    n_blocks = -(-horizon // block)
    chosen = rng.choice(starts, size=(n, n_blocks))
    paths = recent[chosen[..., None] + np.arange(block)].reshape(n, -1)[:, :horizon]
    totals = paths.sum(axis=1)
    k = DEFAULT_SPREAD if spread is None else spread
    if k != 1.0:
        med = np.median(totals)
        totals = np.maximum(med + k * (totals - med), 0.0)
    return totals


@dataclass(frozen=True)
class Forecast:
    horizon_months: int
    p10: float
    p50: float
    p80: float
    p90: float
    mean: float

    @property
    def monthly_rate(self) -> float:
        return self.p50 / self.horizon_months


def forecast(history: np.ndarray, horizon: int, **kw) -> tuple[Forecast, np.ndarray]:
    s = bootstrap_samples(history, horizon, **kw)
    q = np.percentile(s, [10, 50, 80, 90])
    return Forecast(horizon, *map(float, q), float(s.mean())), s


def _series(demand: pd.DataFrame):
    for key, g in demand.sort_values("month").groupby(["program_id", "part_number"]):
        yield key, g["units"].to_numpy()


def calibrate_spread(
    demand: pd.DataFrame,
    horizon: int = 12,
    origins: range = range(36, 49, 3),
    target: float = 0.80,
    grid: np.ndarray = np.round(np.arange(1.0, 2.51, 0.05), 2),
) -> tuple[float, pd.DataFrame]:
    """Smallest spread whose P10-P90 coverage reaches `target` on the calibration origins."""
    rows = []
    for k in grid:
        hits = []
        for _, y in _series(demand):
            for o in origins:
                if o + horizon > len(y):
                    continue
                s = bootstrap_samples(y[:o], horizon, seed=o, spread=k)
                lo, hi = np.percentile(s, [10, 90])
                hits.append(lo <= y[o:o + horizon].sum() <= hi)
        rows.append({"spread": float(k), "coverage": float(np.mean(hits))})
    table = pd.DataFrame(rows)
    ok = table[table.coverage >= target]
    return (float(ok.spread.iloc[0]) if not ok.empty else float(grid[-1])), table


def backtest(
    demand: pd.DataFrame,
    horizon: int = 12,
    origins: range = range(51, 61, 3),
    spread: float | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rolling-origin backtest across every (program, part) series.

    Default origins (months 51-60) are held out from `calibrate_spread`
    (months 36-48), so reported coverage is out-of-sample. Returns per-forecast
    rows and a per-method summary: MAE of cumulative horizon demand, MAE
    relative to naive_mean (<1 = better), and P10-P90 coverage (target 80%).
    """
    rows = []
    for (prog, pn), y in _series(demand):
        for origin in origins:
            if origin + horizon > len(y):
                continue
            hist, actual = y[:origin], float(y[origin:origin + horizon].sum())
            fc, _ = forecast(hist, horizon, seed=origin, spread=spread)
            point = {
                "naive_mean": naive_mean(hist, horizon),
                "recent_mean": recent_mean(hist, horizon),
                "sba": sba(hist, horizon),
                "bootstrap_p50": fc.p50,
            }
            for method, pred in point.items():
                rows.append({
                    "program_id": prog, "part_number": pn, "origin": origin,
                    "method": method, "forecast": pred, "actual": actual,
                    "abs_error": abs(pred - actual),
                    "in_p10_p90": (fc.p10 <= actual <= fc.p90) if method == "bootstrap_p50" else np.nan,
                })
    detail = pd.DataFrame(rows)
    summary = detail.groupby("method").agg(mae=("abs_error", "mean"), n=("abs_error", "size"))
    summary["mae_vs_naive"] = summary["mae"] / summary.loc["naive_mean", "mae"]
    summary["p10_p90_coverage"] = detail.groupby("method")["in_p10_p90"].mean()
    return detail, summary.sort_values("mae").reset_index()
