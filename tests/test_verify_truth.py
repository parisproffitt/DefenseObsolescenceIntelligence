import pandas as pd

from continuum.verify_truth import check

KEY = pd.DataFrame({"part_number": ["A3P1000-1PQG208I", "EP4CE10E22I7"],
                    "replacement_part_number": ["", "EP4CE10E22I7N"]})


def test_complete_key_passes_both_directions():
    text = "Affected: A3P1000-1PQG208I, EP4CE10E22I7 -> EP4CE10E22I7N. Ref CAAN-02OLLE763."
    r = check(text, KEY)
    assert r["key_parts_in_text"] == 2 and r["key_replacements_in_text"] == 1
    assert r["text_opns_missing_from_key"] == [] and r["key_parts_missing_from_text"] == []


def test_part_missing_from_key_is_reported():
    text = "A3P1000-1PQG208I A3P250-PQG208I EP4CE10E22I7 EP4CE10E22I7N"
    assert check(text, KEY)["text_opns_missing_from_key"] == ["A3P250-PQG208I"]


def test_key_part_absent_from_text_is_reported():
    assert check("A3P1000-1PQG208I only", KEY)["key_parts_missing_from_text"] == ["EP4CE10E22I7"]
