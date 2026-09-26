"""Raw export layer: what a program office would actually hand an FDSE.

The clean tables in output/ are the *reference* result. The raw files in
output/raw/ are deliberately messy (spreadsheet headers, padded/lower-case part
numbers, distributor suffixes, text dates) so the cleaning is done inside
Foundry, in Pipeline Builder, where it is visible in lineage (DECISIONS.md D-12).
The reference tables let us check that the Foundry pipeline reproduces them.
"""

from __future__ import annotations

import pandas as pd


def to_raw(data: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    programs = data["programs"].rename(columns={
        "program_id": "Program Code", "name": "Program Name", "description": "Description",
        "platform_type": "Platform", "fleet_size": "Fleet Size", "end_of_support": "Planned EOS",
        "redesign_lead_time_months": "Redesign Lead Time (mo)", "redesign_nre_usd": "Redesign NRE ($)",
    })
    programs["Planned EOS"] = pd.to_datetime(programs["Planned EOS"]).dt.strftime("%m/%d/%Y")

    bom = data["bom_lines"].merge(data["assemblies"][["assembly_id", "name"]], on="assembly_id")
    bom = bom.merge(data["parts"][["part_number", "description"]], on="part_number")
    bom_export = pd.DataFrame({
        "Program": bom["program_id"],
        "Assy No.": bom["assembly_id"],
        "Assy Name": bom["name"],
        "Line": bom["bom_line_id"].str[-2:].astype(int),
        "Part No.": bom["part_number_as_entered"],       # as typed: padding, case, -ND suffix
        "Description": bom["description"],
        "Qty/Assy": bom["qty_per_assembly"],
    })

    parts = data["parts"].rename(columns={
        "part_number": "Part No.", "manufacturer": "Mfr", "family": "Family",
        "description": "Description", "unit_cost_usd": "Unit Cost", "is_real_part_number": "Real OPN",
    })
    parts["Unit Cost"] = parts["Unit Cost"].map(lambda v: f"${v:,.2f}")

    inv = data["inventory"]
    inventory = pd.DataFrame({
        "Depot": inv["location"],
        "Program": inv["program_id"],
        "Part No.": inv["part_number"].str.lower(),
        "Qty OH": inv["on_hand"],
        "As Of": pd.to_datetime(inv["as_of"]).dt.strftime("%d-%b-%Y"),
    })

    dem = data["demand_monthly"]
    demand = pd.DataFrame({
        "Period": pd.to_datetime(dem["month"]).dt.strftime("%Y-%m"),
        "Program": dem["program_id"],
        "Part No.": dem["part_number"],
        "Units Issued": dem["units"],
    })

    return {
        "raw_programs": programs,
        "raw_bom_export": bom_export,
        "raw_parts_master": parts,
        "raw_inventory": inventory,
        "raw_demand_history": demand,
    }
