import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_final import Candidate, Evidence, Review, anchor_evidence, review_passes, validate_candidate, validate_final


def candidate(kind="bridge"):
    return Candidate(keyphrases=["approval"], user_input="Whose approval is required?",
                     reference="Sponsor approval is required.", reasoning_type=kind,
                     connection="Each source supplies a necessary fact.",
                     evidence=[Evidence(context_index=0, quote="Temporary staff use contractor access.", contribution="Identifies the access process."),
                               Evidence(context_index=1, quote="Contractor access needs sponsor approval.", contribution="Identifies the approval authority.")])


def test_multisource_quotes_are_exact_and_both_sources_are_required():
    c = candidate()
    contexts = [e.quote for e in c.evidence]
    validate_candidate(c, contexts, "multi_hop")
    c.evidence[1].quote = "Manager approval is required."
    with pytest.raises(ValueError, match="exactly match"):
        validate_candidate(c, contexts, "multi_hop")
    c.evidence = c.evidence[:1]
    with pytest.raises(ValueError, match="Every source"):
        validate_candidate(c, contexts, "multi_hop")


def test_source_index_and_reasoning_type_are_checked():
    c = candidate("single_hop")
    contexts = [e.quote for e in c.evidence]
    with pytest.raises(ValueError, match="Reasoning type"):
        validate_candidate(c, contexts, "multi_hop")
    c.evidence[1].context_index = 2
    with pytest.raises(ValueError, match="exactly match"):
        validate_candidate(c, contexts, "multi_hop")


def test_altered_excerpt_expands_to_original_source_without_inventing_evidence():
    c = candidate()
    contexts = [e.quote for e in c.evidence]
    c.evidence[0].quote = "An altered quotation that did not appear in the source."
    assert anchor_evidence(c, contexts)
    assert c.evidence[0].quote == contexts[0]
    validate_candidate(c, contexts, "multi_hop")
    assert not anchor_evidence(c, contexts)


def test_plan_has_exact_distribution_and_source_counts():
    plan = json.loads((Path(__file__).parent / "final_plan.json").read_text(encoding="utf-8"))
    assert len(plan) == len({r["id"] for r in plan}) == 50
    assert sum(r["question_type"] == "single_hop" for r in plan) == 35
    assert all(len(r["sources"]) == (1 if r["question_type"] == "single_hop" else 2) for r in plan)


def test_two_context_necessity_gate_only_applies_to_multihop():
    review = Review(accepted=True, issues=[], all_contexts_necessary=False)
    assert review_passes(review, "single_hop")
    assert not review_passes(review, "multi_hop")
    review.all_contexts_necessary = True
    assert review_passes(review, "multi_hop")
    review.issues = ["Missing exception"]
    assert not review_passes(review, "single_hop")


def test_published_artifact_when_present():
    path = Path(__file__).parent / "final_v2" / "testset_final.json"
    if not path.exists():
        pytest.skip("Generation has not completed")
    rows = json.loads(path.read_text(encoding="utf-8"))
    validate_final(rows)
    sources = json.loads((path.parent / "sources.json").read_text(encoding="utf-8"))
    by_id = {s["metadata"]["chunk_id"]: s for s in sources}
    assert len(by_id) == 55
    assert all(row["human_approved"] is False for row in rows)
    assert sum(row["edited_by_assistant"] for row in rows) == 18
    for row in rows:
        for chunk_id, text, metadata in zip(row["reference_context_ids"], row["reference_contexts"], row["sources"], strict=True):
            assert text == by_id[chunk_id]["text"]
            assert metadata == by_id[chunk_id]["metadata"]
    broken = copy.deepcopy(rows)
    broken[-1]["user_input"] = broken[0]["user_input"]
    with pytest.raises(ValueError, match="Near-duplicate"):
        validate_final(broken)
    with pytest.raises(ValueError, match="exactly 35"):
        validate_final(rows[:-1])
