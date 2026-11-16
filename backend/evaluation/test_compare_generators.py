import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compare_generators import Judgment, has_generator_instruction, make_graph


def test_ragas_graph_keeps_the_planned_pair_and_relation():
    item = {"question_type": "multi_hop", "focus": "expense rules"}
    graph = make_graph(item, ["First source", "Second source"])
    pairs = graph.find_two_nodes_single_rel(lambda rel: rel.type == "entities_overlap")
    assert len(pairs) == 1
    assert {pairs[0][0].get_property("page_content"), pairs[0][2].get_property("page_content")} == {"First source", "Second source"}
    assert pairs[0][1].get_property("overlapped_items") == ["expense rules"]


def test_review_accepts_empty_string_as_no_issues_without_changing_verdicts():
    review = Judgment(source_conditions=[], missing_conditions=[], question_issues=[],
                      grounded=True, complete=True, clear=True, useful=True,
                      matches_focus=True, all_contexts_necessary=False, issues="")
    assert review.issues == []
    assert review.all_contexts_necessary is False


def test_flags_generator_instruction_not_an_ordinary_question():
    assert has_generator_instruction("What is the limit? Preserve every qualifier.")
    assert not has_generator_instruction("How do the policies apply to a business trip?")
