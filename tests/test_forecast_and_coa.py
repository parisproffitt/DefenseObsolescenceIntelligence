import numpy as np

from continuum.coa import annual_growth, build_coas, buy_outcomes, tradeoff_curve
from continuum.forecast import bootstrap_samples, forecast, naive_mean, sba


def test_bootstrap_is_deterministic_and_nonnegative():
    h = np.array([0, 5, 0, 0, 12, 3, 0, 8] * 6)
    a = bootstrap_samples(h, 12, seed=1)
    b = bootstrap_samples(h, 12, seed=1)
    assert np.array_equal(a, b)
    assert (a >= 0).all()


def test_spread_widens_interval_around_same_median():
    h = np.random.default_rng(0).poisson(4, 48)
    narrow = bootstrap_samples(h, 12, seed=3, spread=1.0)
    wide = bootstrap_samples(h, 12, seed=3, spread=1.5)
    assert np.median(narrow) == np.median(wide)
    assert np.ptp(np.percentile(wide, [10, 90])) > np.ptp(np.percentile(narrow, [10, 90]))


def test_forecast_quantiles_are_ordered():
    fc, _ = forecast(np.random.default_rng(1).poisson(6, 60), 12)
    assert fc.p10 <= fc.p50 <= fc.p80 <= fc.p90


def test_point_methods_on_constant_series():
    h = np.full(36, 4)
    assert naive_mean(h, 12) == 48
    assert abs(sba(h, 12) - 48 * 0.95) < 1e-9     # SBA bias correction (1 - alpha/2)


def test_buying_more_never_increases_shortage_risk():
    curve = tradeoff_curve(np.random.default_rng(2).poisson(10, 48), on_hand=50, unit_cost=100, window_months=24)
    assert curve["p_shortage"].is_monotonic_decreasing
    assert curve["expected_excess_usd"].is_monotonic_increasing


def test_buy_outcomes_basic():
    out = buy_outcomes(np.array([10, 20, 30]), on_hand=5, qty=15, unit_cost=2.0)
    assert out["p_shortage"] == 1 / 3
    assert out["expected_excess_units"] == (10 + 0 + 0) / 3


def test_annual_growth_recovers_trend():
    months = np.arange(60)
    h = np.round(20 * 1.10 ** (months / 12)).astype(int)
    assert abs(annual_growth(h) - 0.10) < 0.02


def test_hybrid_bridge_reduces_shortage_vs_redesign_only():
    h = np.random.default_rng(5).poisson(20, 72)
    lot, redesign, hybrid = build_coas(h, on_hand=200, unit_cost=100, redesign_lead_months=24,
                                       redesign_nre_usd=1e6, remaining_life_months=180)
    assert hybrid.p_shortage < redesign.p_shortage
    assert hybrid.buy_qty < lot.buy_qty
