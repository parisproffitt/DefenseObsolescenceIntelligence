"""The intake gate releases only notices the extraction read completely (D-23)."""

import pandas as pd

from continuum.gate import gate

PAGES = pd.DataFrame([
    {"notice_id": "N1", "page": 1, "text": "Last date for bookings (LTB): December 1, 2025.\nA3P1000-1PQG208I   A3P250-PQG208I"},
])


def row(pn, quote=None, ltb="2025-12-01", repl=None):
    return {"notice_id": "N1", "part_number": pn, "last_time_buy": ltb, "last_time_ship": "2026-12-01",
            "replacement_part_number": repl, "source_quote": quote if quote is not None else pn}


def test_complete_clean_extraction_is_released():
    lines = pd.DataFrame([row("A3P1000-1PQG208I"), row("A3P250-PQG208I")])
    acc, rej, status = gate(lines, PAGES)
    assert len(acc) == 2 and rej.empty
    assert status.iloc[0]["status"] == "RELEASED"


def test_invented_part_is_rejected_and_notice_held():
    lines = pd.DataFrame([row("A3P1000-1PQG208I"), row("A3P250-PQG208I"), row("A3P600-PQG208I")])
    acc, rej, status = gate(lines, PAGES)
    assert list(rej["part_number"]) == ["A3P600-PQG208I"]
    assert "not found verbatim" in rej.iloc[0]["gate_reasons"]
    assert status.iloc[0]["status"] == "HELD_FOR_REVIEW"


def test_missed_part_holds_the_notice():
    lines = pd.DataFrame([row("A3P1000-1PQG208I")])
    _, rej, status = gate(lines, PAGES)
    assert rej.empty
    s = status.iloc[0]
    assert s["status"] == "HELD_FOR_REVIEW" and s["opns_in_text_not_extracted"] == 1
    assert s["missed_examples"] == "A3P250-PQG208I"


def test_bad_quote_and_bad_date_are_reasons():
    lines = pd.DataFrame([row("A3P1000-1PQG208I", quote="made-up sentence", ltb="Dec 1 2025"), row("A3P250-PQG208I")])
    _, rej, _ = gate(lines, PAGES)
    reasons = rej.iloc[0]["gate_reasons"]
    assert "quote not found" in reasons and "valid YYYY-MM-DD" in reasons
