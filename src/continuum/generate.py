"""Notional sustainment data generator.

Real: notice part numbers and dates (data/reference/*.csv).
Notional: programs, assemblies, BOMs, inventory, unit costs, demand history.

The generator is deterministic (fixed seed) so every number in the demo is
reproducible. The HERON scenario is calibrated so the demo story holds:
~312 units on hand, ~14 months of coverage, LTB window ~6 months out from the
scenario date, and a 24-month redesign/qualification lead time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_DIR = REPO_ROOT / "data" / "reference"

# Scenario replay: Dana receives the real Microchip notice a few days after issue.
AS_OF = date(2025, 6, 10)
HISTORY_MONTHS = 72


@dataclass(frozen=True)
class PartSpec:
    part_number: str          # as written in the BOM (may be messy on purpose)
    description: str
    unit_cost: float
    monthly_rate: float       # demand level at AS_OF (units / month)
    annual_trend: float       # growth in demand per year (aging fleets trend up)
    p_nonzero: float          # probability a month has any demand (lumpiness)
    on_hand: int | None = None  # None -> derived from coverage_months
    coverage_months: float | None = None
    qty_per: int = 1


PROGRAMS = [
    {
        "program_id": "HERON",
        "name": "Heron",
        "description": "Long-serving tactical airlift fleet (notional)",
        "platform_type": "Airlift aircraft",
        "fleet_size": 52,
        "end_of_support": "2042-12-31",
        "redesign_lead_time_months": 24,
        "redesign_nre_usd": 1_450_000,
    },
    {
        "program_id": "KITE",
        "name": "Kite",
        "description": "Advanced jet trainer (notional)",
        "platform_type": "Trainer aircraft",
        "fleet_size": 96,
        "end_of_support": "2038-06-30",
        "redesign_lead_time_months": 18,
        "redesign_nre_usd": 900_000,
    },
    {
        "program_id": "PETREL",
        "name": "Petrel",
        "description": "Airborne surveillance radar upgrade (notional)",
        "platform_type": "Radar system",
        "fleet_size": 30,
        "end_of_support": "2045-12-31",
        "redesign_lead_time_months": 30,
        "redesign_nre_usd": 2_100_000,
    },
]

# assembly_id -> (program_id, name, nomenclature)
ASSEMBLIES = {
    "HER-MCP-210": ("HERON", "Mission Computer Processor Card", "CCA, Processor, Mission Computer"),
    "HER-DIU-115": ("HERON", "Display Interface Unit", "LRU, Display Interface"),
    "HER-PDU-040": ("HERON", "Power Distribution Unit", "LRU, Power Distribution"),
    "KIT-FCC-300": ("KITE", "Flight Control Interface Card", "CCA, Flight Control I/O"),
    "KIT-AVB-120": ("KITE", "Avionics Bus Controller", "CCA, 1553 Bus Controller"),
    "PET-RSP-500": ("PETREL", "Radar Signal Processor", "LRU, Signal Processor"),
    "PET-TIM-220": ("PETREL", "Timing & Control Module", "CCA, Timing and Control"),
}

# Real affected OPNs are written the way humans type them into BOMs: some clean,
# some lower-case / padded, to exercise normalization. Notional parts use an
# obviously fictional "NTL-" prefix so no real part's status is misrepresented.
BOM: dict[str, list[PartSpec]] = {
    "HER-MCP-210": [
        # The demo part: ProASIC3 A3P1000, industrial, PQ208 -> on CAAN-02OLLE763.
        PartSpec("A3P1000-1PQG208I", "FPGA, ProASIC3, 1M gates, PQFP-208, industrial",
                 185.0, monthly_rate=312 / 14, annual_trend=0.06, p_nonzero=0.62,
                 on_hand=312),
        PartSpec("NTL-OSC-25M-01", "Oscillator, 25 MHz", 14.0, 6.0, 0.03, 0.7, coverage_months=40),
        PartSpec("NTL-DDR-512-04", "SDRAM, 512 Mb", 22.0, 9.0, 0.04, 0.7, coverage_months=26),
    ],
    "HER-DIU-115": [
        PartSpec("  a3p250-pqg208i ", "FPGA, ProASIC3, 250k gates, PQFP-208, industrial",
                 96.0, 5.5, 0.02, 0.45, coverage_months=31),
        PartSpec("NTL-LVDS-TX-08", "LVDS transmitter", 9.5, 7.0, 0.02, 0.6, coverage_months=48),
    ],
    "HER-PDU-040": [
        PartSpec("NTL-PWR-0412", "DC/DC converter, 28V in", 64.0, 3.0, 0.05, 0.4, coverage_months=22),
    ],
    "KIT-FCC-300": [
        PartSpec("A3P250-PQG208I", "FPGA, ProASIC3, 250k gates, PQFP-208, industrial",
                 96.0, 2.0, 0.0, 0.3, coverage_months=140),
        # Real OPN from Intel PDN2401 (leaded finish, replacement is lead-free "N").
        PartSpec("EP4CE10E22I7", "FPGA, Cyclone IV E, EQFP-144, industrial, SnPb finish",
                 48.0, 4.0, 0.01, 0.5, coverage_months=96),
    ],
    "KIT-AVB-120": [
        PartSpec("NTL-1553-XCVR-2", "MIL-STD-1553 transceiver", 210.0, 1.5, 0.02, 0.3, coverage_months=60),
    ],
    "PET-RSP-500": [
        PartSpec("M1A3P400-1PQG208I", "FPGA, ProASIC3 w/ Cortex-M1, PQFP-208, industrial",
                 142.0, 3.5, 0.04, 0.4, coverage_months=38),
        # Same device as an affected family, DIFFERENT package (FBGA-484): NOT on the notice.
        PartSpec("A3P1000-1FGG484I", "FPGA, ProASIC3, 1M gates, FBGA-484, industrial",
                 240.0, 2.5, 0.03, 0.35, coverage_months=44),
        PartSpec("NTL-ADC-14B-02", "ADC, 14-bit, 105 MSPS", 88.0, 4.0, 0.03, 0.5, coverage_months=30),
    ],
    "PET-TIM-220": [
        PartSpec("NTL-PLL-JC-06", "Jitter-cleaning PLL", 31.0, 3.0, 0.02, 0.5, coverage_months=52),
    ],
}


def _month_index(as_of: date, months: int) -> pd.DatetimeIndex:
    end = pd.Timestamp(as_of.year, as_of.month, 1) - pd.offsets.MonthBegin(1)
    return pd.date_range(end=end, periods=months, freq="MS")


def simulate_demand(spec: PartSpec, rng: np.random.Generator, months: int = HISTORY_MONTHS) -> np.ndarray:
    """Intermittent, lumpy monthly demand with a trend.

    Each month: demand occurs with probability p_nonzero; if it occurs, the
    batch size is negative-binomial (over-dispersed) with a mean chosen so the
    expected demand equals the trended level for that month.
    """
    t = np.arange(months) - (months - 1)          # 0 at the most recent month
    level = spec.monthly_rate * (1 + spec.annual_trend) ** (t / 12)
    occurs = rng.random(months) < spec.p_nonzero
    size_mean = level / spec.p_nonzero
    dispersion = 2.0                               # smaller -> lumpier
    p = dispersion / (dispersion + size_mean)
    sizes = rng.negative_binomial(dispersion, p)
    return np.where(occurs, sizes, 0).astype(int)


def build(seed: int = 7) -> dict[str, pd.DataFrame]:
    from .partnumbers import normalize, parse

    rng = np.random.default_rng(seed)
    idx = _month_index(AS_OF, HISTORY_MONTHS)

    assemblies, bom_rows, parts, inventory, demand = [], [], {}, [], []
    for asm_id, (prog, name, nomen) in ASSEMBLIES.items():
        assemblies.append({"assembly_id": asm_id, "program_id": prog, "name": name, "nomenclature": nomen})
        for line_no, spec in enumerate(BOM[asm_id], start=1):
            pn = normalize(spec.part_number)
            pp = parse(spec.part_number)
            parts.setdefault(pn, {
                "part_number": pn,
                "manufacturer": pp.manufacturer or "Notional",
                "family": pp.family,
                "description": spec.description,
                "unit_cost_usd": spec.unit_cost,
                "is_real_part_number": pp.manufacturer is not None,
            })
            bom_rows.append({
                "bom_line_id": f"{asm_id}-{line_no:02d}",
                "assembly_id": asm_id,
                "program_id": prog,
                "part_number_as_entered": spec.part_number,
                "part_number": pn,
                "qty_per_assembly": spec.qty_per,
            })
            series = simulate_demand(spec, rng)
            for month, qty in zip(idx, series):
                demand.append({"program_id": prog, "part_number": pn, "month": month.date(), "units": int(qty)})
            if spec.on_hand is not None:
                on_hand = spec.on_hand
            else:
                on_hand = int(round(spec.monthly_rate * spec.coverage_months))
            inventory.append({
                "inventory_id": f"INV-{prog}-{pn}",
                "program_id": prog,
                "part_number": pn,
                "on_hand": on_hand,
                "location": {"HERON": "Depot A", "KITE": "Depot B", "PETREL": "Depot C"}[prog],
                "as_of": AS_OF,
            })

    return {
        "programs": pd.DataFrame(PROGRAMS),
        "assemblies": pd.DataFrame(assemblies),
        "parts": pd.DataFrame(parts.values()),
        "bom_lines": pd.DataFrame(bom_rows),
        "inventory": pd.DataFrame(inventory),
        "demand_monthly": pd.DataFrame(demand),
    }


def evaluation_corpus(n_series: int = 200, seed: int = 123) -> pd.DataFrame:
    """Many synthetic demand series with randomized level, trend, and lumpiness.

    Used only to evaluate and calibrate forecasting methods: 11 program series
    give ~50 backtest forecasts, too few to measure 80% interval coverage (SE ~6pts).
    """
    rng = np.random.default_rng(seed)
    idx = _month_index(AS_OF, HISTORY_MONTHS)
    rows = []
    for i in range(n_series):
        spec = PartSpec(
            part_number=f"EVAL-{i:03d}", description="", unit_cost=0.0,
            monthly_rate=float(rng.uniform(1, 30)),
            annual_trend=float(rng.uniform(-0.02, 0.08)),
            p_nonzero=float(rng.uniform(0.25, 0.75)),
            on_hand=0,
        )
        for month, qty in zip(idx, simulate_demand(spec, rng)):
            rows.append({"program_id": "EVAL", "part_number": spec.part_number,
                         "month": month.date(), "units": int(qty)})
    return pd.DataFrame(rows)


def load_notice_parts() -> pd.DataFrame:
    frames = [pd.read_csv(p) for p in sorted(REFERENCE_DIR.glob("*_affected_parts.csv"))]
    df = pd.concat(frames, ignore_index=True)
    for col in ("last_time_buy", "last_time_ship"):
        df[col] = pd.to_datetime(df[col]).dt.date
    return df
