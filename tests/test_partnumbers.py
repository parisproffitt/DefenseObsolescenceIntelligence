from continuum.partnumbers import MatchType, match_against_notice, normalize, parse


def test_normalize_strips_case_space_and_distributor_suffix():
    assert normalize("  a3p250-pqg208i ") == "A3P250-PQG208I"
    assert normalize("A3P250-PQG208I-ND") == "A3P250-PQG208I"


def test_parse_proasic3_fields():
    p = parse("A3P1000-1PQG208I")
    assert (p.family, p.device, p.package, p.temp_grade, p.lead_free) == (
        "ProASIC3", "A3P1000", "PQ208", "I", True)


def test_parse_proasic3_fbga_package_is_not_pq208():
    p = parse("A3P1000-1FGG484I")
    assert p.device == "A3P1000"
    assert p.package == "FG484"


def test_parse_proasic3_custom_variant():
    p = parse("A3P600L-1PQG208IDX402")
    assert (p.device, p.temp_grade, p.variant) == ("A3P600L", "I", "DX402")


def test_parse_intel_lead_free_marker():
    old, new = parse("EP4CE10E22I7"), parse("EP4CE10E22I7N")
    assert old.family == "Cyclone IV E" and old.lead_free is False
    assert new.lead_free is True
    assert parse("EP4CE10E22C8LN").lead_free is True     # low-power grade + lead-free
    assert parse("EPM240T100C5NRR").lead_free is True


def test_unknown_format_returns_normalized_only():
    p = parse("ntl-osc-25m-01")
    assert p.normalized == "NTL-OSC-25M-01" and p.family is None


def test_exact_match_beats_family_level_match():
    notice = ["A3P1000-1PQG208I", "A3P1000-PQG208"]
    bom = ["a3p1000-1pqg208i", "A3P1000-1FGG484I", "NTL-OSC-25M-01"]
    got = [r.match_type for r in match_against_notice(bom, notice)]
    # The FBGA part shares the device name but is NOT discontinued: flag, don't match.
    assert got == [MatchType.EXACT, MatchType.FAMILY_ONLY, MatchType.NONE]
