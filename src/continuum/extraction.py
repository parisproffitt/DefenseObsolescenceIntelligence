"""Notice extraction harness: prompt, chunking and parsing around an LLM call.

The model call itself is injected (`complete(system, user) -> str`), so the same
code runs in a Foundry transform against AIP models and in tests with a stub.
The prompt is the one specified in docs/AIP_LOGIC.md; the AIP Logic function
`extractNoticeLines` uses the same text, so evaluation numbers carry over.

Two modes (D-19):
- "document": one call per notice with the whole text.
- "page":     one call per page, each prefixed with page 1 (where the notice
              states its dates), results unioned. AIP_LOGIC.md suggested this
              for long notices; the evaluation measures whether it helps.
"""

from __future__ import annotations

import json
import re
from typing import Callable

import pandas as pd

SYSTEM_PROMPT = """You extract facts from semiconductor end-of-life / discontinuance notices for a
defense sustainment engineer. Accuracy matters more than completeness of prose.

Rules:
1. List EVERY affected ordering part number in the text, exactly as printed.
   Do not group, abbreviate, expand ranges, or normalize.
2. Never invent a part number, date, or replacement. If a field is not stated
   for a part, return null for it.
3. Dates: convert to YYYY-MM-DD. If the notice gives one LTB/LTS for all parts,
   apply it to every part.
4. A replacement counts only if the notice explicitly pairs it with that part.
   Do not suggest one, and never state that a part is compatible.
5. For every row, quote the shortest verbatim text that supports it.
6. Copy any sentence that could change a buy decision (possible cancellation,
   non-cancellable orders, allocation limits) into `caveats`, verbatim.
Return only the JSON object described in the schema."""

SCHEMA = """Schema:
{"notice_type": "EOL" | "PDN" | "PCN",
 "caveats": [string],
 "lines": [{"notice_id": string, "part_number": string,
            "last_time_buy": "YYYY-MM-DD" | null, "last_time_ship": "YYYY-MM-DD" | null,
            "replacement_part_number": string | null, "source_quote": string}]}"""

LINE_COLUMNS = ["notice_id", "part_number", "last_time_buy", "last_time_ship",
                "replacement_part_number", "source_quote"]


def user_message(notice_id: str, text: str) -> str:
    return f"{SCHEMA}\n\nnotice_id: {notice_id}\n\nNotice text:\n{text}"


def chunks(pages: pd.DataFrame, mode: str) -> list[tuple[str, str, str]]:
    """(notice_id, chunk_id, text) per model call. `pages` has notice_id, page, text."""
    out = []
    for nid, g in pages.sort_values(["notice_id", "page"]).groupby("notice_id"):
        texts = g["text"].fillna("").tolist()
        if mode == "document":
            out.append((nid, "all", "\n\n".join(texts)))
        elif mode == "page":
            for i, t in enumerate(texts, start=1):
                body = t if i == 1 else f"[Page 1, for context]\n{texts[0]}\n\n[Page {i}]\n{t}"
                out.append((nid, f"p{i:02d}", body))
        else:
            raise ValueError(f"unknown mode {mode!r}")
    return out


def parse_response(raw: str) -> dict:
    """The JSON object in a model reply; tolerates code fences and leading prose."""
    s = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", s, re.S)
    if fence:
        s = fence.group(1).strip()
    start, end = s.find("{"), s.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object in response")
    return json.loads(s[start:end + 1])


def extract(pages: pd.DataFrame, mode: str, complete: Callable[[str, str], str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run the model over every chunk. Returns (lines, calls).

    `calls` records one row per model call (chunk, rows returned, parse error),
    so a failed or truncated call is visible instead of silently lowering recall.
    """
    lines, calls = [], []
    for nid, chunk_id, text in chunks(pages, mode):
        rec = {"notice_id": nid, "chunk_id": chunk_id, "rows": 0, "error": None,
               "notice_type": None, "caveats": None}
        try:
            obj = parse_response(complete(SYSTEM_PROMPT, user_message(nid, text)))
            rows = obj.get("lines") or []
            for r in rows:
                row = {c: r.get(c) for c in LINE_COLUMNS}
                row["notice_id"] = nid  # the chunk's notice, whatever the model echoed
                row["chunk_id"] = chunk_id
                lines.append(row)
            rec.update(rows=len(rows), notice_type=obj.get("notice_type"),
                       caveats=json.dumps(obj.get("caveats") or []))
        except Exception as e:  # noqa: BLE001 - recorded, not swallowed
            rec["error"] = f"{type(e).__name__}: {e}"[:500]
        calls.append(rec)
    df = pd.DataFrame(lines, columns=LINE_COLUMNS + ["chunk_id"])
    for c in LINE_COLUMNS:
        df[c] = df[c].astype("object").where(df[c].notna(), None)
    return df, pd.DataFrame(calls)
