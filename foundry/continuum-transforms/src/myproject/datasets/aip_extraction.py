"""Step 4: AIP notice extraction, run on two models and scored against ground truth (D-14, D-17).

The prompt, chunking and parsing live in continuum.extraction (unit-tested outside
Foundry); this file only binds AIP models to it. Each model gets its own transform
so one unavailable model does not block the other.
"""

import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from language_model_service_api.languagemodelservice_api import ChatMessage, ChatMessageRole
from language_model_service_api.languagemodelservice_api_completion_v3 import GptChatCompletionRequest
from palantir_models.transforms import OpenAiGptChatLanguageModelInput
from transforms.api import Input, Output, transform

from myproject.continuum.eval_extraction import score
from myproject.continuum.extraction import chunks, extract
from myproject.datasets.paths import AIP, CLEAN, RAW

MODELS = {
    # label: (model RID, what it stands for in the comparison)
    "small": "ri.language-model-service..language-model.gpt-4-1-nano",
    "frontier": "ri.language-model-service..language-model.gpt-4-1",
}
MODES = ("document", "page")


def _completer(model):
    def complete(system, user):
        msgs = [ChatMessage(ChatMessageRole.SYSTEM, system), ChatMessage(ChatMessageRole.USER, user)]
        try:
            req = GptChatCompletionRequest(messages=msgs, temperature=0.0, max_tokens=16000)
        except TypeError:
            req = GptChatCompletionRequest(msgs)
        for attempt in range(3):
            try:
                return model.create_chat_completion(req).choices[0].message.content
            except Exception:  # noqa: BLE001 - rate limits: back off, then surface the error
                if attempt == 2:
                    raise
                time.sleep(5 * (attempt + 1))
    return complete


def _run(model, label, pages, lines_out, calls_out):
    complete = _completer(model)
    page_df = pages.pandas()
    runs = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        for mode, (lines, calls) in zip(MODES, pool.map(lambda m: extract(page_df, m, complete), MODES)):
            lines.insert(0, "mode", mode)
            calls.insert(0, "mode", mode)
            runs.append((lines, calls))
    lines = pd.concat([r[0] for r in runs], ignore_index=True)
    calls = pd.concat([r[1] for r in runs], ignore_index=True)
    lines.insert(0, "model", label)
    calls.insert(0, "model", label)
    calls.insert(1, "model_rid", MODELS[label])
    lines_out.write_table(lines)
    calls_out.write_table(calls)


@transform.using(
    lines_out=Output(f"{AIP}/extraction_small_lines"),
    calls_out=Output(f"{AIP}/extraction_small_calls"),
    pages=Input(f"{RAW}/raw_notice_text"),
    model=OpenAiGptChatLanguageModelInput(MODELS["small"]),
)
def extraction_small(lines_out, calls_out, pages, model):
    _run(model, "small", pages, lines_out, calls_out)


@transform.using(
    lines_out=Output(f"{AIP}/extraction_frontier_lines"),
    calls_out=Output(f"{AIP}/extraction_frontier_calls"),
    pages=Input(f"{RAW}/raw_notice_text"),
    model=OpenAiGptChatLanguageModelInput(MODELS["frontier"]),
)
def extraction_frontier(lines_out, calls_out, pages, model):
    _run(model, "frontier", pages, lines_out, calls_out)


@transform.using(
    scores=Output(f"{AIP}/extraction_scores"),
    small=Input(f"{AIP}/extraction_small_lines"),
    frontier=Input(f"{AIP}/extraction_frontier_lines"),
    truth=Input(f"{CLEAN}/notice_lines"),
)
def extraction_scores(scores, small, frontier, truth):
    """One row per model x mode x notice, plus a POOLED row, straight from eval_extraction.score."""
    gt = truth.pandas()
    gt = gt[gt.notice_id.isin(["CAAN-02OLLE763", "PDN2401"])]
    rows = []
    for inp in (small, frontier):
        ex = inp.pandas()
        for (model, mode), g in ex.groupby(["model", "mode"]):
            per, summary = score(g, gt)
            per.insert(0, "mode", mode)
            per.insert(0, "model", model)
            rows.append(per)
            rows.append(pd.DataFrame([{
                "model": model, "mode": mode, "notice_id": "POOLED",
                "truth_parts": int(per.truth_parts.sum()), "extracted_parts": int(per.extracted_parts.sum()),
                "true_positives": int(per.true_positives.sum()),
                "recall": summary["part_recall"], "precision": summary["part_precision"],
                "ltb_accuracy": summary["ltb_accuracy"], "lts_accuracy": summary["lts_accuracy"],
            }]))
    out = pd.concat(rows, ignore_index=True)
    for c in ("replacement_accuracy", "citation_coverage"):
        out[c] = out[c].astype(float)
    scores.write_table(out)
