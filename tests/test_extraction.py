import json

import pandas as pd

from continuum.eval_extraction import score
from continuum.extraction import chunks, extract, parse_response

PAGES = pd.DataFrame({
    "notice_id": ["N1", "N1", "N2"],
    "page": [1, 2, 1],
    "text": ["LTB 2025-12-01. Parts: A1", "A2", "B1"],
})


def test_page_mode_prefixes_page_one_for_dates():
    c = chunks(PAGES, "page")
    assert [x[1] for x in c] == ["p01", "p02", "p01"]
    assert "LTB 2025-12-01" in c[1][2] and "A2" in c[1][2]


def test_document_mode_is_one_call_per_notice():
    assert len(chunks(PAGES, "document")) == 2


def test_parse_tolerates_fences_and_prose():
    raw = 'Here you go:\n```json\n{"lines": [], "caveats": ["x"]}\n```'
    assert parse_response(raw)["caveats"] == ["x"]


def test_failed_call_is_recorded_not_dropped():
    def complete(system, user):
        if "notice_id: N2" in user:
            return "sorry, I can't"
        return json.dumps({"notice_type": "EOL", "caveats": [], "lines": [
            {"notice_id": "WRONG", "part_number": "A1", "last_time_buy": "2025-12-01",
             "last_time_ship": None, "replacement_part_number": None, "source_quote": "A1"}]})

    lines, calls = extract(PAGES, "document", complete)
    assert set(lines.notice_id) == {"N1"}          # the chunk's notice id wins over the echo
    assert calls.set_index("notice_id").loc["N2", "error"].startswith("ValueError")


def test_extraction_output_is_scoreable():
    truth = pd.DataFrame({"notice_id": ["N1"], "part_number": ["A1"], "replacement_part_number": [None],
                          "last_time_buy": ["2025-12-01"], "last_time_ship": ["2026-12-01"]})

    def complete(system, user):
        return json.dumps({"lines": [{"part_number": "a1 ", "last_time_buy": "2025-12-01",
                                      "last_time_ship": "2026-12-01", "source_quote": "A1"}]})

    lines, _ = extract(PAGES[PAGES.notice_id == "N1"].head(1), "document", complete)
    _, summary = score(lines, truth)
    assert summary["part_recall"] == 1.0 and summary["lts_accuracy"] == 1.0


def test_unwrap_include_errors_struct():
    from continuum.extraction import unwrap_llm_output

    fenced = '```json\n{"lines": []}\n```'
    assert unwrap_llm_output({"ok": fenced, "error": None}) == (fenced, None)
    assert unwrap_llm_output({"ok": None, "error": "rate limited"}) == ("", "rate limited")
    assert unwrap_llm_output(json.dumps({"ok": fenced, "error": None})) == (fenced, None)
    assert unwrap_llm_output('{"lines": []}') == ('{"lines": []}', None)  # plain reply, not a struct
    assert parse_response(unwrap_llm_output({"ok": fenced, "error": None})[0]) == {"lines": []}
