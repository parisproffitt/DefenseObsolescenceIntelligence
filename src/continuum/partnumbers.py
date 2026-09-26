"""Deterministic part-number normalization and matching.

Why this is code and not an LLM step: matching a bill-of-materials line to a
discontinued ordering part number is an exact-identity question. The notice for
ProASIC3 names "A3P1000 device families", but only the PQ208 package is actually
discontinued. A family-level (or fuzzy / semantic) match would wrongly flag an
A3P1000 in a 484-ball FBGA package. Exact matching on a normalized key is
correct, cheap, and auditable; the family-level signal is kept separately as a
"needs review" hint rather than a match.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

# Distributor / packaging decorations that are not part of the manufacturer OPN.
_DISTRIBUTOR_SUFFIXES = ("-ND", "-CT", "-TR", "-DKR")


def normalize(raw: str) -> str:
    """Canonical form of a part number for identity comparison.

    Uppercases, strips whitespace and stray punctuation at the ends, removes
    internal spaces, and drops common distributor suffixes. Hyphens inside the
    OPN are significant (A3P1000-1PQG208 != A3P10001PQG208 in general) and kept.
    """
    if raw is None:
        return ""
    s = re.sub(r"\s+", "", str(raw).upper()).strip(".,;:\"'")
    for suffix in _DISTRIBUTOR_SUFFIXES:
        if s.endswith(suffix):
            s = s[: -len(suffix)]
    return s


@dataclass(frozen=True)
class ParsedPart:
    raw: str
    normalized: str
    manufacturer: str | None
    family: str | None       # e.g. "ProASIC3", "Cyclone IV E", "MAX II"
    device: str | None       # e.g. "A3P1000", "EP4CE10", "EPM240"
    package: str | None      # e.g. "PQ208", "E22", "T100"
    temp_grade: str | None   # "C" commercial, "I" industrial, "M" military
    lead_free: bool | None
    variant: str | None      # custom / packaging suffix, e.g. "X538", "RR"


_PROASIC3 = re.compile(
    r"^(?P<device>(?:M1|M7)?A3PE?\d+L?)"      # A3P1000, M1A3P400, A3PE3000L
    r"-(?P<speed>[12])?"                      # optional speed grade
    r"(?P<pkg>PQ|FG|VQ|QN|CS|FGG|PQG|VQG|QNG|CSG)"
    r"(?P<pins>\d+)"
    r"(?P<rest>.*)$"
)

_INTEL = re.compile(
    r"^(?P<device>EP2C\d+|EP3C\d+|EP4CE\d+|EPM\d+G?|5M\d+Z|10M\d+SA)"
    r"(?P<pkg>[A-Z]{1,2}\d{2,3})"
    r"(?P<temp>[CIA])(?P<speed>\d)"
    r"(?P<rest>[A-Z]*)$"
)

_INTEL_FAMILIES = {
    "EP2C": "Cyclone II",
    "EP3C": "Cyclone III",
    "EP4CE": "Cyclone IV E",
    "EPM": "MAX II",
    "5M": "MAX V",
    "10M": "MAX 10",
}


def parse(raw: str) -> ParsedPart:
    """Best-effort structural parse. Unknown formats return mostly-None fields."""
    n = normalize(raw)

    m = _PROASIC3.match(n)
    if m:
        pkg = m["pkg"]
        lead_free = len(pkg) == 3 and pkg.endswith("G")  # PQG / FGG = RoHS-compliant finish
        rest = m["rest"]
        temp = rest[0] if rest[:1] in ("I", "M") else "C"
        variant = rest[1:] if temp != "C" else rest
        return ParsedPart(
            raw=raw, normalized=n, manufacturer="Microchip", family="ProASIC3",
            device=m["device"], package=pkg[:2] + m["pins"],
            temp_grade=temp, lead_free=lead_free, variant=variant or None,
        )

    m = _INTEL.match(n)
    if m:
        device = m["device"]
        family = next((f for p, f in _INTEL_FAMILIES.items() if device.startswith(p)), None)
        rest = m["rest"]
        # Intel's lead-free marker is an "N" (or "G" for MAX 10) after the speed grade;
        # a trailing "L" is a low-power grade, not a finish.
        core = rest[1:] if rest.startswith("L") else rest
        lead_free = core.startswith("N") or core.startswith("G")
        return ParsedPart(
            raw=raw, normalized=n, manufacturer="Intel", family=family, device=device,
            package=m["pkg"], temp_grade=m["temp"], lead_free=lead_free,
            variant=(core[1:] if lead_free else core) or None,
        )

    return ParsedPart(raw, n, None, None, None, None, None, None, None)


class MatchType(str, Enum):
    EXACT = "EXACT"                  # normalized OPN identical -> affected
    FAMILY_ONLY = "FAMILY_ONLY"      # same device, different package/grade -> not affected, flag for review
    NONE = "NONE"


@dataclass(frozen=True)
class MatchResult:
    bom_part: str
    match_type: MatchType
    notice_part: str | None


def match_against_notice(bom_parts: list[str], notice_parts: list[str]) -> list[MatchResult]:
    """Match BOM part numbers against a notice's affected OPNs.

    EXACT wins. Otherwise, if the device matches some affected OPN, report
    FAMILY_ONLY so an engineer can confirm it is genuinely unaffected.
    """
    exact = {normalize(p): p for p in notice_parts}
    by_device: dict[str, str] = {}
    for p in notice_parts:
        d = parse(p).device
        if d:
            by_device.setdefault(d, p)

    results = []
    for bp in bom_parts:
        n = normalize(bp)
        if n in exact:
            results.append(MatchResult(bp, MatchType.EXACT, exact[n]))
            continue
        device = parse(bp).device
        if device and device in by_device:
            results.append(MatchResult(bp, MatchType.FAMILY_ONLY, by_device[device]))
        else:
            results.append(MatchResult(bp, MatchType.NONE, None))
    return results
