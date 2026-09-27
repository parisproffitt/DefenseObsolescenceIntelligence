"""Step 4 via Pipeline Builder (D-26): the prompt table the Use LLM nodes run over.

One row per model call, both modes: `document` (whole notice) and `page` (one page,
with page 1 prepended so the dates are in view). The prompt text is built by the
tested continuum.extraction code, so Pipeline Builder only sends it to a model.
The system prompt is continuum.extraction.SYSTEM_PROMPT (docs/AIP_LOGIC.md).
"""

import pandas as pd
from transforms.api import Input, Output, transform

from myproject.continuum.extraction import chunks, user_message
from myproject.datasets.paths import AIP, RAW


@transform.using(
    prompts=Output(f"{AIP}/extraction_prompts"),
    pages=Input(f"{RAW}/raw_notice_text"),
)
def extraction_prompts(prompts, pages):
    df = pages.pandas()
    rows = []
    for mode in ("document", "page"):
        for nid, chunk_id, text in chunks(df, mode):
            rows.append({"call_id": f"{mode}|{nid}|{chunk_id}", "mode": mode, "notice_id": nid,
                         "chunk_id": chunk_id, "prompt": user_message(nid, text)})
    prompts.write_table(pd.DataFrame(rows))
