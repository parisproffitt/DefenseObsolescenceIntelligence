"""The demo story must be reproducible from the data: these numbers are narrated in the video."""

import pandas as pd
import pytest

from continuum.generate import AS_OF, build, load_notice_parts
from continuum.impact import assess


@pytest.fixture(scope="module")
def scenario():
    data = build()
    parts = load_notice_parts()
    cases, flags = assess("CAAN-02OLLE763", parts, data, AS_OF)
    return data, parts, cases, flags


def test_generator_is_deterministic():
    a, b = build(), build()
    for name in a:
        pd.testing.assert_frame_equal(a[name], b[name])


def test_ground_truth_notice_lists_load():
    parts = load_notice_parts()
    counts = parts.groupby("notice_id").size().to_dict()
    assert counts == {"CAAN-02OLLE763": 110, "PDN2401": 120}


def test_heron_is_the_critical_case(scenario):
    _, _, cases, _ = scenario
    top = cases.iloc[0]
    assert (top.program_id, top.part_number, top.severity) == ("HERON", "A3P1000-1PQG208I", "CRITICAL")
    assert top.on_hand == 312
    assert 13 <= top.coverage_months <= 15          # "about 14 months of stock"
    assert 5 <= top.months_to_ltb <= 6               # LTB 2025-12-01 vs scenario date 2025-06-10
    assert top.redesign_lead_time_months == 24
    assert 9 <= top.gap_months <= 11                 # "a ~10-month gap"


def test_messy_bom_entry_is_matched(scenario):
    _, _, cases, _ = scenario
    # "  a3p250-pqg208i " in the Heron BOM must normalize and match.
    assert ((cases.program_id == "HERON") & (cases.part_number == "A3P250-PQG208I")).any()


def test_different_package_is_flagged_not_matched(scenario):
    _, _, cases, flags = scenario
    assert "A3P1000-1FGG484I" not in set(cases.part_number)
    row = flags[flags.part_number == "A3P1000-1FGG484I"].iloc[0]
    assert row.flag_type == "FAMILY_ONLY_MATCH"


def test_lead_free_replacement_is_flagged():
    data, parts = build(), load_notice_parts()
    _, flags = assess("PDN2401", parts, data, AS_OF)
    assert (flags.flag_type == "FINISH_CHANGE").any()


def test_raw_bom_export_normalizes_back_to_reference():
    """The Pipeline Builder cleaning (trim, upper-case, strip distributor suffix) must
    reproduce the reference bom_lines table exactly."""
    from continuum.partnumbers import normalize
    from continuum.raw import to_raw

    data = build()
    raw = to_raw(data)["raw_bom_export"]
    assert raw["Part No."].map(normalize).tolist() == data["bom_lines"]["part_number"].tolist()
    assert raw["Part No."].str.endswith("-ND").any()          # distributor suffix present
    assert (raw["Part No."] != raw["Part No."].str.strip()).any()  # padding present
