import pandas as pd
import pytest

from continuum.eval_extraction import score
from continuum.generate import load_notice_parts


@pytest.fixture(scope="module")
def truth():
    return load_notice_parts()


def test_perfect_extraction_scores_one(truth):
    per, summary = score(truth.copy(), truth)
    assert summary["part_recall"] == 1.0 and summary["part_precision"] == 1.0
    assert summary["ltb_accuracy"] == 1.0 and summary["lts_accuracy"] == 1.0
    intel = per.set_index("notice_id").loc["PDN2401"]
    assert intel.replacement_accuracy == 1.0


def test_formatting_noise_is_not_penalized(truth):
    noisy = truth.copy()
    noisy["part_number"] = "  " + noisy["part_number"].str.lower() + " "
    _, summary = score(noisy, truth)
    assert summary["part_recall"] == 1.0


def test_dropped_rows_and_hallucinations_are_counted(truth):
    caan = truth[truth.notice_id == "CAAN-02OLLE763"]
    ex = caan.iloc[10:].copy()                       # drop 10 real parts
    fake = ex.iloc[:2].copy()
    fake["part_number"] = ["A3P9999-PQG208", "A3P8888-PQG208"]
    ex = pd.concat([ex, fake])                       # add 2 invented parts
    per, _ = score(ex, caan)
    row = per.iloc[0]
    assert row.true_positives == 100
    assert row.recall == pytest.approx(100 / 110)
    assert row.precision == pytest.approx(100 / 102)
    assert "A3P8888-PQG208" in row.extra_examples


def test_wrong_date_is_caught(truth):
    caan = truth[truth.notice_id == "CAAN-02OLLE763"].copy()
    caan.loc[caan.index[:11], "last_time_buy"] = pd.Timestamp("2025-12-31").date()
    per, _ = score(caan, truth[truth.notice_id == "CAAN-02OLLE763"])
    assert per.iloc[0].ltb_accuracy == pytest.approx(99 / 110)


def test_missing_required_column_raises(truth):
    with pytest.raises(ValueError):
        score(truth.drop(columns=["last_time_ship"]), truth)
