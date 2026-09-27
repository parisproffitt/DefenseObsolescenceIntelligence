"""Autonomous intake, steps 2-4 (D-23). Held until the language-model libraries are added
(MANUAL_STEPS step 2); drop in next to aip_extraction.py and set KEPT to the kept label.

inbox -> aip/notice_lines_auto (kept model, page mode, identical rows unioned)
      -> gate(): aip/notice_lines_accepted, aip/notice_lines_rejected, aip/notice_intake_status
      -> clean/notice_lines_live (accepted rows of RELEASED notices, same schema as clean/notice_lines)
"""

import pandas as pd
from palantir_models.transforms import OpenAiGptChatLanguageModelInput
from transforms.api import Input, Output, transform

from myproject.continuum.extraction import LINE_COLUMNS, extract
from myproject.continuum.gate import gate
from myproject.datasets.aip_extraction import MODELS, _completer
from myproject.datasets.paths import AIP, CLEAN, RAW

KEPT = "small"  # set from aip/extraction_scores (D-19)


@transform.using(
    lines_out=Output(f"{AIP}/notice_lines_auto"),
    calls_out=Output(f"{AIP}/notice_lines_auto_calls"),
    inbox=Input(f"{RAW}/notice_inbox"),
    model=OpenAiGptChatLanguageModelInput(MODELS[KEPT]),
)
def notice_lines_auto(lines_out, calls_out, inbox, model):
    lines, calls = extract(inbox.pandas(), "page", _completer(model))
    # Page mode repeats page 1 in every chunk: union identical rows. A part returned
    # with conflicting values stays duplicated, and the gate holds the notice for it.
    lines = lines.drop(columns=["chunk_id"]).astype("string").drop_duplicates().reset_index(drop=True)
    lines_out.write_table(lines.astype(object).where(lines.notna(), None))
    calls.insert(0, "model", KEPT)
    calls_out.write_table(calls)


@transform.using(
    accepted_out=Output(f"{AIP}/notice_lines_accepted"),
    rejected_out=Output(f"{AIP}/notice_lines_rejected"),
    status_out=Output(f"{AIP}/notice_intake_status"),
    lines=Input(f"{AIP}/notice_lines_auto"),
    inbox=Input(f"{RAW}/notice_inbox"),
)
def notice_gate(accepted_out, rejected_out, status_out, lines, inbox):
    accepted, rejected, status = gate(lines.pandas()[LINE_COLUMNS], inbox.pandas())
    accepted_out.write_table(accepted.astype("string").astype(object).where(accepted.notna(), None))
    rejected_out.write_table(rejected.astype("string").astype(object).where(rejected.notna(), None))
    status_out.write_table(status)


@transform.using(
    live=Output(f"{CLEAN}/notice_lines_live"),
    accepted=Input(f"{AIP}/notice_lines_accepted"),
    status=Input(f"{AIP}/notice_intake_status"),
    notices=Input(f"{CLEAN}/notices"),
)
def notice_lines_live(live, accepted, status, notices):
    st = status.pandas()
    released = set(st.loc[st["status"] == "RELEASED", "notice_id"])
    a = accepted.pandas()
    a = a[a["notice_id"].isin(released)]
    mfr = notices.pandas().set_index("notice_id")["manufacturer"]
    live.write_table(pd.DataFrame({
        "notice_line_id": a["notice_id"] + "|" + a["part_number"],
        "notice_id": a["notice_id"],
        "manufacturer": a["notice_id"].map(mfr),
        "part_number": a["part_number"],
        "replacement_part_number": a["replacement_part_number"].where(a["replacement_part_number"].fillna("") != "", None),
        "last_time_buy": pd.to_datetime(a["last_time_buy"]).dt.date,
        "last_time_ship": pd.to_datetime(a["last_time_ship"]).dt.date,
    }).reset_index(drop=True))
