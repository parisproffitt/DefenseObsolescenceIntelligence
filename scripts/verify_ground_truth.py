"""Verify data/reference/*_affected_parts.csv against the notices' own text (D-20).

The notice PDFs are not in the repo. Point this at a CSV of their text layer
(columns notice_id, page, text; the same file uploaded to Foundry as raw_notice_text):

    python scripts/verify_ground_truth.py path/to/raw_notice_text.csv

Exits non-zero if any part is missing in either direction.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from continuum.generate import load_notice_parts  # noqa: E402
from continuum.verify_truth import check  # noqa: E402


def main(path: str) -> int:
    pages = pd.read_csv(path)
    key = load_notice_parts()
    ok = True
    for nid, g in key.groupby("notice_id"):
        text = " ".join(pages[pages.notice_id == nid].sort_values("page")["text"].fillna(""))
        r = check(text, g)
        print(nid, r)
        ok &= not r["text_opns_missing_from_key"] and not r["key_parts_missing_from_text"]
    print("OK" if ok else "MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
