"""Apply explicit, source-grounded assistant edits and review the final 50 cases."""

import argparse
import asyncio
import json
from pathlib import Path

from langchain_community.callbacks.manager import get_openai_callback

from generate_final import Candidate, HERE, REVIEW, Review, review_passes, validate_candidate, validate_final, write_json
from openai_config import make_openai_llm


async def finalize(output, edits, llm):
    config = json.loads((output / "run_config.json").read_text(encoding="utf-8"))
    if config["model"] != llm.model_name:
        raise ValueError("Use the generation model for the curation review")
    sources = json.loads((output / "sources.json").read_text(encoding="utf-8"))
    source_map = {(s["metadata"]["title"], s["metadata"]["chunk_index"]): s for s in sources}
    reviewer = llm.with_structured_output(Review, method="function_calling")
    review_path = output / "curation_reviews.json"
    reviews = json.loads(review_path.read_text(encoding="utf-8")) if review_path.exists() else {}
    rows = []
    for item in config["plan"]:
        history = json.loads((output / "cases" / (item["id"] + ".json")).read_text(encoding="utf-8"))
        original = history[-1].get("accepted_row")
        selected = [source_map[tuple(k)] for k in item["sources"]]
        contexts = [s["text"] for s in selected]
        if item["id"] in edits:
            edit = edits[item["id"]]
            candidate = Candidate(**{k: edit[k] for k in ("user_input", "reference", "keyphrases", "reasoning_type", "connection")},
                                  evidence=[{"context_index": i, "quote": text, "contribution": edit["contributions"][i]} for i, text in enumerate(contexts)])
            validate_candidate(candidate, contexts, item["question_type"])
            cached = reviews.get(item["id"], {})
            if cached.get("candidate") == candidate.model_dump() and cached.get("review", {}).get("accepted"):
                review = Review.model_validate(cached["review"])
            else:
                request = {"question_type": item["question_type"], "contexts": contexts, "candidate": candidate.model_dump()}
                review = await reviewer.ainvoke([("system", REVIEW), ("human", json.dumps(request, ensure_ascii=False))])
                reviews[item["id"]] = {"candidate": candidate.model_dump(), "review": review.model_dump(), "edit_reason": edit["reason"]}
                write_json(review_path, reviews)
            if not review_passes(review, item["question_type"]):
                raise ValueError(f"Curation review failed for {item['id']}: {review.issues}")
            row = {**candidate.model_dump(), "id": item["id"], "question_type": item["question_type"],
                   "planned_focus": item["focus"], "reference_contexts": contexts,
                   "reference_context_ids": [s["metadata"]["chunk_id"] for s in selected],
                   "reference_document_ids": list(dict.fromkeys(s["metadata"]["document_id"] for s in selected)),
                   "sources": [s["metadata"] for s in selected], "automated_review": review.model_dump(),
                   "review_status": "assistant_curated_and_automated_review_passed", "human_approved": False,
                   "edited_by_assistant": True, "assistant_edit_reason": edit["reason"],
                   "before_assistant_edit": original or history[-1].get("candidate"),
                   "evidence_quote_expanded_to_source": True}
            print(f"Reviewed edit {item['id']}", flush=True)
        elif original:
            row = {**original, "edited_by_assistant": False}
        else:
            raise ValueError(f"Case {item['id']} needs a source-grounded edit")
        rows.append({**row, "assistant_reviewed": True})
    validate_final(rows)
    write_json(output / "assistant_edits.json", edits)
    write_json(output / "testset_final.json", rows)
    print(f"Finalized {len(rows)} cases; {len(edits)} explicit assistant edits")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=HERE / "final_v2")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if (output / "testset_final.json").exists():
        raise FileExistsError("Preserve the existing final testset before finalizing again")
    edits = json.loads((HERE / "final_edits.json").read_text(encoding="utf-8"))
    with get_openai_callback() as usage:
        try:
            asyncio.run(finalize(output, edits, make_openai_llm()))
        finally:
            usage_path = output / "curation_usage.json"
            stats = json.loads(usage_path.read_text(encoding="utf-8")) if usage_path.exists() else []
            stats.append({"successful_requests": usage.successful_requests, "input_tokens": usage.prompt_tokens,
                          "output_tokens": usage.completion_tokens, "cost_usd_callback_estimate": usage.total_cost})
            write_json(usage_path, stats)


if __name__ == "__main__":
    main()
