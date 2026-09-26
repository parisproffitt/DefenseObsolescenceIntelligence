"""Phase 1b: raw exports -> clean, typed, keyed tables that back the Ontology.

Every part number goes through partnumbers.normalize(), the same function the
matching step uses (D-04, D-16): trim, upper-case, drop distributor suffixes.
Each output declares its primary key as a FAIL check, so a duplicate key stops
the build instead of reaching the Ontology.
"""

import pandas as pd
from transforms import expectations as E
from transforms.api import Check, Input, Output, transform

from myproject.continuum.partnumbers import normalize
from myproject.datasets.paths import CLEAN, RAW


def _pk(col):
    return Check(E.primary_key(col), f"Primary key {col}", on_error="FAIL")


def _read_csv(inp, name):
    with inp.filesystem().open(f"{name}.csv") as f:
        return pd.read_csv(f, dtype=str, keep_default_na=False)


def _strings(df):
    """Uploaded tables: every column as text, nulls (None / NaN / pd.NA) as ""."""
    return df.astype("string").fillna("").astype(str)


def _to_date(s, fmt=None):
    return pd.to_datetime(s.mask(s == ""), format=fmt).dt.date


@transform.using(
    out=Output(f"{CLEAN}/programs", checks=_pk("program_id")),
    raw=Input(f"{RAW}/raw_programs"),
)
def programs(out, raw):
    df = _read_csv(raw, "raw_programs")
    out.write_table(pd.DataFrame({
        "program_id": df["Program Code"],
        "name": df["Program Name"],
        "description": df["Description"],
        "platform_type": df["Platform"],
        "fleet_size": df["Fleet Size"].astype(int),
        "end_of_support": _to_date(df["Planned EOS"], "%m/%d/%Y"),
        "redesign_lead_time_months": df["Redesign Lead Time (mo)"].astype(int),
        "redesign_nre_usd": df["Redesign NRE ($)"].astype(float),
    }))


@transform.using(
    out=Output(f"{CLEAN}/bom_lines", checks=_pk("bom_line_id")),
    raw=Input(f"{RAW}/raw_bom_export"),
)
def bom_lines(out, raw):
    df = _read_csv(raw, "raw_bom_export")
    out.write_table(pd.DataFrame({
        "bom_line_id": df["Assy No."] + "-" + df["Line"].astype(int).map("{:02d}".format),
        "assembly_id": df["Assy No."],
        "program_id": df["Program"],
        "part_number_as_entered": df["Part No."],
        "part_number": df["Part No."].map(normalize),
        "qty_per_assembly": df["Qty/Assy"].astype(int),
    }))


@transform.using(
    out=Output(f"{CLEAN}/assemblies", checks=_pk("assembly_id")),
    raw=Input(f"{RAW}/raw_bom_export"),
)
def assemblies(out, raw):
    df = _read_csv(raw, "raw_bom_export")
    df = df[["Assy No.", "Program", "Assy Name"]].drop_duplicates()
    out.write_table(df.set_axis(["assembly_id", "program_id", "name"], axis=1).reset_index(drop=True))


@transform.using(
    out=Output(f"{CLEAN}/parts", checks=_pk("part_number")),
    raw=Input(f"{RAW}/raw_parts_master"),
)
def parts(out, raw):
    df = _read_csv(raw, "raw_parts_master")
    out.write_table(pd.DataFrame({
        "part_number": df["Part No."].map(normalize),
        "manufacturer": df["Mfr"],
        "family": df["Family"].mask(df["Family"] == ""),
        "description": df["Description"],
        "unit_cost_usd": df["Unit Cost"].str.replace(r"[$,]", "", regex=True).astype(float),
        "is_real_part_number": df["Real OPN"].eq("True"),
    }))


@transform.using(
    out=Output(f"{CLEAN}/inventory", checks=_pk("inventory_id")),
    raw=Input(f"{RAW}/raw_inventory"),
)
def inventory(out, raw):
    df = _read_csv(raw, "raw_inventory")
    pn = df["Part No."].map(normalize)
    out.write_table(pd.DataFrame({
        "inventory_id": "INV-" + df["Program"] + "-" + pn,
        "program_id": df["Program"],
        "part_number": pn,
        "on_hand": df["Qty OH"].astype(int),
        "location": df["Depot"],
        "as_of": _to_date(df["As Of"], "%d-%b-%Y"),
    }))


@transform.using(
    out=Output(f"{CLEAN}/demand_monthly"),
    raw=Input(f"{RAW}/raw_demand_history"),
)
def demand_monthly(out, raw):
    df = _read_csv(raw, "raw_demand_history")
    out.write_table(pd.DataFrame({
        "program_id": df["Program"],
        "part_number": df["Part No."].map(normalize),
        "month": _to_date(df["Period"] + "-01", "%Y-%m-%d"),
        "units": df["Units Issued"].astype(int),
    }))


@transform.using(
    out=Output(f"{CLEAN}/notices", checks=_pk("notice_id")),
    raw=Input(f"{RAW}/raw_notices"),
)
def notices(out, raw):
    df = _strings(raw.pandas())
    out.write_table(pd.DataFrame({
        "notice_id": df["notice_id"],
        "manufacturer": df["manufacturer"],
        "notice_type": df["notice_type"],
        "issue_date": _to_date(df["issue_date"]),
        "last_time_buy": _to_date(df["last_time_buy"]),
        "last_time_ship": _to_date(df["last_time_ship"]),
        "affected_part_count": pd.to_numeric(df["affected_part_count"].mask(df["affected_part_count"] == "")).astype("Int64"),
        "replacements_listed": df["replacements_listed"].str.lower().map({"true": True, "false": False}).astype("boolean"),  # blank = unknown
        "source_url": df["source_url"],
        "notes": df["notes"],
    }))


@transform.using(
    out=Output(f"{CLEAN}/notice_lines", checks=_pk("notice_line_id")),
    raw=Input(f"{RAW}/raw_notice_parts"),
)
def notice_lines(out, raw):
    """The real affected-part lists (ground truth, D-13). One row per notice x OPN."""
    df = _strings(raw.pandas())
    out.write_table(pd.DataFrame({
        "notice_line_id": df["notice_id"] + "|" + df["part_number"],
        "notice_id": df["notice_id"],
        "manufacturer": df["manufacturer"],
        "part_number": df["part_number"],
        "replacement_part_number": df["replacement_part_number"].mask(df["replacement_part_number"] == ""),
        "last_time_buy": _to_date(df["last_time_buy"]),
        "last_time_ship": _to_date(df["last_time_ship"]),
    }))


@transform.using(
    out=Output(f"{CLEAN}/bom_notice_matches", checks=_pk("match_id")),
    bom=Input(f"{CLEAN}/bom_lines"),
    lines=Input(f"{CLEAN}/notice_lines"),
)
def bom_notice_matches(out, bom, lines):
    """The exact-match rule (D-04) as a visible join: normalized BOM part = notice OPN.

    Expect 5 rows. Petrel's A3P1000-1FGG484I shares a device with the notice but
    not an OPN, so it must NOT appear here (it becomes a review flag instead).
    """
    m = bom.pandas().merge(lines.pandas(), on="part_number", how="inner")
    m.insert(0, "match_id", m["notice_line_id"] + "|" + m["bom_line_id"])
    out.write_table(m[["match_id", "notice_id", "notice_line_id", "bom_line_id", "program_id",
                       "assembly_id", "part_number", "part_number_as_entered",
                       "replacement_part_number", "last_time_buy", "last_time_ship"]])
