"""The AIP memo may only repeat numbers the Ontology gave it (D-09, D-21)."""

from continuum.memo import SYSTEM_PROMPT, build_input, unsupported_numbers

HERON = dict(program_id="HERON", part_number="A3P1000-1PQG208I", notice_id="CAAN-02OLLE763",
             severity="CRITICAL", on_hand=312, coverage_months=13.8, months_to_ltb=5.7,
             redesign_lead_time_months=24, gap_months=10.2, last_time_buy="2025-12-01")
COAS = [
    dict(name="Life-of-type buy", buy_qty=5640, total_usd=1_530_000, p_shortage=0.10, p_shortage_under_stress=0.99),
    dict(name="Redesign only", buy_qty=0, total_usd=1_450_000, p_shortage=0.93, p_shortage_under_stress=0.94),
    dict(name="Bridge buy + redesign", buy_qty=500, total_usd=1_550_000, p_shortage=0.14, p_shortage_under_stress=0.18),
]


def test_input_block_carries_the_invariants():
    block = build_input(HERON, COAS)
    for s in ["units_on_hand: 312", "stock_coverage_months: 13.8", "months_to_last_time_buy: 5.7",
              "supply_gap_months: 10.2", "buy_units: 500", "$1.55M", "14%", "18%"]:
        assert s in block


def test_faithful_memo_passes():
    block = build_input(HERON, COAS)
    memo = ("Situation: Heron holds 312 units, 13.8 months of stock; a redesign takes 24 months, "
            "a 10.2-month gap. Options: bridge buy of 500 units, $1.55M, 14% risk (18% under stress). "
            "Decision needed by 2025-12-01.")
    assert unsupported_numbers(memo, block) == []


def test_invented_or_recomputed_number_is_caught():
    block = build_input(HERON, COAS)
    memo = "The bridge buy costs about $1.6M and cuts risk by 76 points."
    assert unsupported_numbers(memo, block) == ["1.6", "76"]


def test_prompt_forbids_recommending_and_compatibility_claims():
    assert "Do not recommend" in SYSTEM_PROMPT
    assert "Never state that a replacement part is compatible" in SYSTEM_PROMPT
