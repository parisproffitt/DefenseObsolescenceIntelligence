"""Step 5: empty, typed datasets behind the two object types the engineer's decision creates.

Procurement Request and Engineering Review objects are created only by the
*Approve course of action* action; these datasets give them a schema and a home
(edit-only object types are not available on this stack). Rows come from Ontology
edits, never from this transform.
"""

import pyarrow as pa
from transforms.api import Output, transform

from myproject.datasets.paths import ONTOLOGY

PROCUREMENT = pa.schema([
    ("request_id", pa.string()), ("case_id", pa.string()), ("coa_key", pa.string()),
    ("program_id", pa.string()), ("part_number", pa.string()), ("quantity", pa.int64()),
    ("estimated_cost_usd", pa.float64()), ("status", pa.string()), ("requested_by", pa.string()),
    ("requested_at", pa.timestamp("us")), ("justification", pa.string()),
])
REVIEW = pa.schema([
    ("review_id", pa.string()), ("case_id", pa.string()), ("coa_key", pa.string()),
    ("program_id", pa.string()), ("part_number", pa.string()), ("review_type", pa.string()),
    ("status", pa.string()), ("opened_by", pa.string()), ("opened_at", pa.timestamp("us")),
    ("notes", pa.string()),
])


@transform.using(
    procurement_requests=Output(f"{ONTOLOGY}/procurement_requests"),
    engineering_reviews=Output(f"{ONTOLOGY}/engineering_reviews"),
)
def compute(procurement_requests, engineering_reviews):
    procurement_requests.write_table(PROCUREMENT.empty_table())
    engineering_reviews.write_table(REVIEW.empty_table())
