"""Check the answer key against the notice text, in both directions (D-13, D-20).

Forward: every part (and listed replacement) in the key appears verbatim in the text.
Reverse: every token in the text that parses as a Microchip / Intel OPN is in the key,
so a part the transcription missed would show up here.
"""

from __future__ import annotations

import re

import pandas as pd

from .partnumbers import parse

_TOKEN = re.compile(r"\b[A-Z0-9][A-Z0-9-]{5,}[A-Z0-9]\b")


def check(text: str, key: pd.DataFrame) -> dict:
    """`key` has part_number and (optionally) replacement_part_number for ONE notice."""
    tokens = set(_TOKEN.findall(text))
    opns = {t for t in tokens if parse(t).manufacturer}
    parts = set(key["part_number"])
    repl = set(key.get("replacement_part_number", pd.Series(dtype=str)).fillna("")) - {""}
    return {
        "key_parts": len(parts),
        "key_parts_in_text": len(parts & tokens),
        "key_replacements": len(repl),
        "key_replacements_in_text": len(repl & tokens),
        "opns_in_text": len(opns),
        "text_opns_missing_from_key": sorted(opns - parts - repl),
        "key_parts_missing_from_text": sorted(parts - tokens),
    }
