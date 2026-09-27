"""Autonomous intake, step 1 (D-23): the inbox of notices released for processing.

`raw/notice_releases` (notice_id, released_at) is the switch: adding a notice_id to it
"delivers" that notice. In production this would be a Data Connection sync from
manufacturer PCN feeds; here it lets the demo release PDN2401 on camera. The inbox is the
text layer of released notices only, and is what the build schedule watches (MANUAL_STEPS 6a).
"""

from transforms.api import Input, Output, transform

from myproject.datasets.paths import RAW


@transform.using(
    inbox=Output(f"{RAW}/notice_inbox"),
    pages=Input(f"{RAW}/raw_notice_text"),
    releases=Input(f"{RAW}/notice_releases"),
)
def notice_inbox(inbox, pages, releases):
    released = set(releases.pandas()["notice_id"].astype(str))
    df = pages.pandas()
    inbox.write_table(df[df["notice_id"].astype(str).isin(released)].reset_index(drop=True))
