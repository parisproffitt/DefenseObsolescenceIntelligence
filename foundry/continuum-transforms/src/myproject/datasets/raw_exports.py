"""Phase 1a: the program office's exports, as they would arrive (D-12, D-16).

Ports generate.py (notional programs, BOMs, inventory, demand; fixed seed) and
raw.py (spreadsheet headers, padded / lower-case part numbers, a Digi-Key -ND
suffix, text dates and $ amounts). Each output holds one CSV file, like a file
drop, so the cleaning step below has real work to do.
"""

from transforms.api import Output, transform

from myproject.continuum.generate import build
from myproject.continuum.raw import to_raw
from myproject.datasets.paths import RAW


def _write_csv(output, df, name):
    with output.filesystem().open(f"{name}.csv", "w") as f:
        df.to_csv(f, index=False)


@transform.using(
    raw_programs=Output(f"{RAW}/raw_programs"),
    raw_bom_export=Output(f"{RAW}/raw_bom_export"),
    raw_parts_master=Output(f"{RAW}/raw_parts_master"),
    raw_inventory=Output(f"{RAW}/raw_inventory"),
    raw_demand_history=Output(f"{RAW}/raw_demand_history"),
)
def compute(raw_programs, raw_bom_export, raw_parts_master, raw_inventory, raw_demand_history):
    raw = to_raw(build())
    outputs = {
        "raw_programs": raw_programs,
        "raw_bom_export": raw_bom_export,
        "raw_parts_master": raw_parts_master,
        "raw_inventory": raw_inventory,
        "raw_demand_history": raw_demand_history,
    }
    for name, output in outputs.items():
        _write_csv(output, raw[name], name)
