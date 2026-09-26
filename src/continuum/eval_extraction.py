"""Score AIP's notice extraction against ground truth.

AIP Logic reads a notice PDF and returns one row per affected part:
    notice_id, part_number, last_time_buy, last_time_ship,
    replacement_part_number (optional), source_quote (optional; the cited text)

This module compares that output to data/reference/*_affected_parts.csv and
reports what a reviewer can trust (DECISIONS.md D-14):
- part recall / precision  -> did it find every affected part, and only those?
- LTB / LTS date accuracy  -> exact match per extracted row that is a true part
- replacement accuracy     -> exact match where the notice lists a replacement
- citation coverage        -> share of rows that quote their source

Part numbers go through the same deterministic normalize() as matching (D-04), so
the score measures extraction, not formatting noise.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from .partnumbers import normalize

REQUIRED = ("notice_id", "part_number", "last_time_buy", "last_time_ship")


def _prep(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"extraction is missing columns: {missing}")
    out = df.copy()
    out["key"] = out["part_number"].map(normalize)
    for col in ("last_time_buy", "last_time_ship"):
        out[col] = pd.to_datetime(out[col], errors="coerce").dt.date
    if "replacement_part_number" not in out:
        out["replacement_part_number"] = None
    out["replacement_key"] = out["replacement_part_number"].map(
        lambda v: normalize(v) if isinstance(v, str) and v.strip() else "")
    return out.drop_duplicates(subset=["notice_id", "key"])


@dataclass
class NoticeScore:
    notice_id: str
    truth_parts: int
    extracted_parts: int
    true_positives: int
    recall: float
    precision: float
    ltb_accuracy: float
    lts_accuracy: float
    replacement_accuracy: float | None
    citation_coverage: float | None
    missed_examples: str
    extra_examples: str


def score(extracted: pd.DataFrame, truth: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Per-notice scores plus a pooled (micro-averaged) summary."""
    ex, gt = _prep(extracted), _prep(truth)
    rows = []
    for nid, g in gt.groupby("notice_id"):
        e = ex[ex.notice_id == nid]
        joined = g.merge(e, on="key", suffixes=("_gt", "_ex"))
        tp = len(joined)
        missed = sorted(set(g.key) - set(e.key))
        extra = sorted(set(e.key) - set(g.key))
        with_repl = joined[joined.replacement_key_gt != ""]
        cites = e["source_quote"].fillna("").astype(str).str.strip() if "source_quote" in e else None
        rows.append(NoticeScore(
            notice_id=nid,
            truth_parts=len(g), extracted_parts=len(e), true_positives=tp,
            recall=tp / len(g) if len(g) else 0.0,
            precision=tp / len(e) if len(e) else 0.0,
            ltb_accuracy=float((joined.last_time_buy_gt == joined.last_time_buy_ex).mean()) if tp else 0.0,
            lts_accuracy=float((joined.last_time_ship_gt == joined.last_time_ship_ex).mean()) if tp else 0.0,
            replacement_accuracy=(float((with_repl.replacement_key_gt == with_repl.replacement_key_ex).mean())
                                  if len(with_repl) else None),
            citation_coverage=float((cites != "").mean()) if cites is not None and len(cites) else None,
            missed_examples=", ".join(missed[:5]),
            extra_examples=", ".join(extra[:5]),
        ))
    per_notice = pd.DataFrame([asdict(r) for r in rows])
    tp, t, x = per_notice.true_positives.sum(), per_notice.truth_parts.sum(), per_notice.extracted_parts.sum()
    summary = {
        "notices": len(per_notice),
        "part_recall": tp / t if t else 0.0,
        "part_precision": tp / x if x else 0.0,
        "ltb_accuracy": float((per_notice.ltb_accuracy * per_notice.true_positives).sum() / tp) if tp else 0.0,
        "lts_accuracy": float((per_notice.lts_accuracy * per_notice.true_positives).sum() / tp) if tp else 0.0,
    }
    return per_notice, summary
