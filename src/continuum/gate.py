"""Code gate for autonomous intake (D-23): AIP-extracted rows are checked before they drive anything.

When a new notice arrives, nobody has written an answer key for it, so the extraction
cannot be scored. Instead every row must pass checks that need only the notice itself:
the part number appears verbatim in the notice text, parses as a known manufacturer's
part, and its dates are real dates. Rows that fail become review flags for the engineer,
never silent drops. A notice-level gate also catches the dangerous case, a model that
returns too few rows: if the text contains part numbers the extraction missed, the
whole notice is held for review.
"""

from __future__ import annotations

import re
from datetime import date

import pandas as pd

from .partnumbers import parse
from .verify_truth import _TOKEN

_WS = re.compile(r"\s+")


def _squash(s: str) -> str:
    return _WS.sub(" ", s or "").strip()


def _is_date(v) -> bool:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return True  # a null date is allowed (the notice may not state it)
    try:
        date.fromisoformat(str(v)[:10])
        return True
    except ValueError:
        return False


def gate(lines: pd.DataFrame, pages: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split extracted rows into (accepted, rejected, notice_status).

    lines: notice_id, part_number, last_time_buy, last_time_ship, replacement_part_number, source_quote
    pages: notice_id, page, text  (the notice's text layer)
    """
    text_by_notice = pages.sort_values(["notice_id", "page"]).groupby("notice_id")["text"].apply("\n".join)
    accepted, rejected, status = [], [], []
    for nid, grp in lines.groupby("notice_id", sort=True):
        text = text_by_notice.get(nid, "")
        squashed, tokens = _squash(text), set(_TOKEN.findall(text))
        seen = set()
        for r in grp.to_dict("records"):
            pn = (r.get("part_number") or "").strip()
            reasons = []
            if not pn or pn not in tokens:
                reasons.append("part number not found verbatim in the notice")
            elif not parse(pn).manufacturer:
                reasons.append("part number does not parse as a known manufacturer's part")
            if pn in seen:
                reasons.append("duplicate row")
            if not (_is_date(r.get("last_time_buy")) and _is_date(r.get("last_time_ship"))):
                reasons.append("date is not a valid YYYY-MM-DD")
            q = _squash(r.get("source_quote") or "")
            if not q or q not in squashed:
                reasons.append("source quote not found in the notice")
            repl = (r.get("replacement_part_number") or "").strip()
            if repl and repl not in tokens:
                reasons.append("replacement not found verbatim in the notice")
            seen.add(pn)
            (rejected if reasons else accepted).append({**r, "gate_reasons": "; ".join(reasons) or None})
        opns_in_text = {t for t in tokens if parse(t).manufacturer}
        found = {a["part_number"] for a in accepted if a["notice_id"] == nid}
        repls = {(a.get("replacement_part_number") or "") for a in accepted if a["notice_id"] == nid}
        missed = sorted(opns_in_text - found - repls)
        status.append({
            "notice_id": nid,
            "rows_accepted": sum(a["notice_id"] == nid for a in accepted),
            "rows_rejected": sum(x["notice_id"] == nid for x in rejected),
            "opns_in_text_not_extracted": len(missed),
            "missed_examples": ", ".join(missed[:10]) or None,
            # Release only a notice the extraction read completely and cleanly.
            "status": "RELEASED" if not missed and not any(x["notice_id"] == nid for x in rejected) else "HELD_FOR_REVIEW",
        })
    cols = list(lines.columns) + ["gate_reasons"]
    return pd.DataFrame(accepted, columns=cols), pd.DataFrame(rejected, columns=cols), pd.DataFrame(status)
