"""Step 4 via Pipeline Builder (D-26): parse the Use LLM replies and score them.

Inputs are written by the Pipeline Builder pipeline `extract_notice_lines`
(`aip/extraction_{small,frontier}_raw`: the prompt table plus a `llm_output` column).
Parsing uses the tested continuum.extraction.parse_response; a reply that fails to
parse becomes a row in the calls table, never a silent drop (D-19).
"""

import json

import pandas as pd
from transforms.api import Input, Output, transform

from myproject.continuum.eval_extraction import score
from myproject.continuum.extraction import LINE_COLUMNS, parse_response
from myproject.datasets.paths import AIP, CLEAN


def _parse(raw: pd.DataFrame, label: str):
    lines, calls = [], []
    for r in raw.to_dict("records"):
        rec = {"model": label, "mode": r["mode"], "notice_id": r["notice_id"], "chunk_id": r["chunk_id"],
               "rows": 0, "error": None, "notice_type": None, "caveats": None}
        out = r.get("llm_output")
        if isinstance(out, dict):  # "Include errors" output: {value, error}
            rec["error"] = out.get("error")
            out = out.get("value")
        try:
            obj = parse_response(out or "")
            got = obj.get("lines") or []
            for x in got:
                row = {c: x.get(c) for c in LINE_COLUMNS}
                row["notice_id"] = r["notice_id"]
                lines.append({"model": label, "mode": r["mode"], **row, "chunk_id": r["chunk_id"]})
            rec.update(rows=len(got), notice_type=obj.get("notice_type"), caveats=json.dumps(obj.get("caveats") or []))
        except Exception as e:  # noqa: BLE001 - recorded, not swallowed
            rec["error"] = (rec["error"] or "") + f"{type(e).__name__}: {e}"[:500]
        calls.append(rec)
    cols = ["model", "mode"] + LINE_COLUMNS + ["chunk_id"]
    ldf = pd.DataFrame(lines, columns=cols)
    for c in LINE_COLUMNS:
        ldf[c] = ldf[c].astype("object").where(ldf[c].notna(), None).map(lambda v: None if v is None else str(v))
    return ldf, pd.DataFrame(calls)


@transform.using(
    small_lines=Output(f"{AIP}/extraction_small_lines"),
    small_calls=Output(f"{AIP}/extraction_small_calls"),
    frontier_lines=Output(f"{AIP}/extraction_frontier_lines"),
    frontier_calls=Output(f"{AIP}/extraction_frontier_calls"),
    scores=Output(f"{AIP}/extraction_scores"),
    small_raw=Input(f"{AIP}/extraction_small_raw"),
    frontier_raw=Input(f"{AIP}/extraction_frontier_raw"),
    truth=Input(f"{CLEAN}/notice_lines"),
)
def extraction_parse_and_score(small_lines, small_calls, frontier_lines, frontier_calls, scores,
                               small_raw, frontier_raw, truth):
    gt = truth.pandas()
    gt = gt[gt.notice_id.isin(["CAAN-02OLLE763", "PDN2401"])]
    rows = []
    for label, raw, lo, co in (("small", small_raw, small_lines, small_calls),
                               ("frontier", frontier_raw, frontier_lines, frontier_calls)):
        lines, calls = _parse(raw.pandas(), label)
        lo.write_table(lines)
        co.write_table(calls)
        for mode, g in lines.groupby("mode"):
            per, summary = score(g, gt)
            per.insert(0, "mode", mode)
            per.insert(0, "model", label)
            rows.append(per)
            rows.append(pd.DataFrame([{
                "model": label, "mode": mode, "notice_id": "POOLED",
                "truth_parts": int(per.truth_parts.sum()), "extracted_parts": int(per.extracted_parts.sum()),
                "true_positives": int(per.true_positives.sum()),
                "recall": summary["part_recall"], "precision": summary["part_precision"],
                "ltb_accuracy": summary["ltb_accuracy"], "lts_accuracy": summary["lts_accuracy"],
            }]))
    out = pd.concat(rows, ignore_index=True)
    for c in ("replacement_accuracy", "citation_coverage"):
        out[c] = out[c].astype(float)
    scores.write_table(out)
