"""Build review artifacts from explicit assistant annotations, without API calls."""

import json
import hashlib
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    annotations = read(ROOT / "review_annotations.json")
    summary = {"review_method": annotations["method"], "rubric": annotations["rubric"], "runs": {}}
    original_sources = {s["metadata"]["chunk_id"] for s in read(ROOT / "pilot/sources.json")}
    for name in ("pilot", "pilot_v2", "pilot_v2_refined"):
        directory = ROOT / name
        fingerprint = hashlib.sha256((directory / "testset_raw.json").read_bytes()).hexdigest()
        if fingerprint != annotations["source_raw_sha256"][name]:
            raise ValueError(f"Raw data changed; existing annotations cannot be reused for {name}")
        rows, sources = read(directory / "testset_raw.json"), read(directory / "sources.json")
        notes = annotations[name]
        if len(rows) != len(notes):
            raise ValueError(f"Annotation count differs for {name}")
        reviewed = []
        for i, (row, note) in enumerate(zip(rows, notes), 1):
            contexts = row.get("reference_contexts", [])
            matches = [s for s in sources if s["text"] in contexts]
            if len(matches) != 1 or len(contexts) != 1:
                raise ValueError(f"Source provenance differs: {name}, case {i}")
            meta = matches[0]["metadata"]
            reviewed.append({**row, "id": row.get("id", f"pilot-{i:02d}"),
                             "reference_document_ids": [meta["document_id"]],
                             "reference_context_ids": [meta["chunk_id"]],
                             "source_title": meta["title"], "section_path": meta["section_path"],
                             "review_status": note["status"], "review_reason": note["reason"],
                             "duplicate_of": note.get("duplicate_of"), "human_approved": False,
                             "reviewer": "Codex assistant, source-grounded review"})
        write(directory / "testset_review_common_rubric.json", reviewed)
        counts = Counter(r["review_status"] for r in reviewed)
        normalized = {" ".join(r["user_input"].lower().split()) for r in rows}
        common = [r for r in reviewed if r["reference_context_ids"][0] in original_sources]
        usage = read(directory / "usage.json")
        summary["runs"][name] = {
            "cases": len(rows), "accept": counts["accept"], "revise": counts["revise"], "reject": counts["reject"],
            "accept_rate": counts["accept"] / len(rows),
            "unique_questions_normalized": len(normalized),
            "duplicate_information_needs_flagged": sum(bool(r["duplicate_of"]) for r in reviewed),
            "source_chunks": len(sources), "source_documents": len({s["metadata"]["document_id"] for s in sources}),
            "original_source_subset_cases": len(common),
            "original_source_subset_accept": sum(r["review_status"] == "accept" for r in common),
            "successful_run_openai_cost_usd_estimate": usage["openai_cost_usd_callback_estimate"],
            "usage": usage,
        }
        if name == "pilot_v2_refined":
            curated = []
            for row, note in zip(reviewed, notes):
                fixed = {**row, "generation_run": name, "original_review_status": row["review_status"],
                         "review_status": "accepted_after_assistant_review",
                         "question_before_edit": row["user_input"], "reference_before_edit": row["reference"],
                         "edited_by_assistant": "corrected_question" in note or "corrected_reference" in note}
                fixed["user_input"] = note.get("corrected_question", row["user_input"])
                fixed["reference"] = note.get("corrected_reference", row["reference"])
                curated.append(fixed)
            write(directory / "testset_curated.json", curated)
            write(directory / "testset_accepted_raw.json", [r for r in reviewed if r["review_status"] == "accept"])
    summary["historical_review_correction"] = "The initial pilot had previously been labeled 1 accept, 3 revise, 2 reject. On the shared rubric, case 02 is accepted because its answer preserves beneficial/conditional guidance. Raw data and the historical review are unchanged."
    summary["comparison_limits"] = [
        "Small synthetic single-hop samples, reviewed by an assistant, not an independent domain expert.",
        "Source composition and prompts both changed; overall acceptance differences do not isolate prompt effects.",
        "On the original three source chunks, baseline has 2/6 accepted and the refined run 1/3. Conditional policy details remain a weakness.",
        "Raw-generation quality and the quality of assistant-edited cases are reported separately; no retrieval metric was run.",
    ]
    summary["new_work_openai_cost_usd_estimate"] = sum(summary["runs"][k]["successful_run_openai_cost_usd_estimate"] for k in ("pilot_v2", "pilot_v2_refined"))
    write(ROOT / "pilot_comparison.json", summary)
    print(json.dumps({k: {x: v[x] for x in ("cases", "accept", "revise", "reject", "unique_questions_normalized")} for k,v in summary["runs"].items()}, ensure_ascii=False))
    print("New runs OpenAI cost estimate:", summary["new_work_openai_cost_usd_estimate"])


if __name__ == "__main__":
    main()
