import sys
from pathlib import Path

import pytest
from langchain_core.documents import Document
from ragas.testset.synthesizers.base import QueryLength, QueryStyle

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_pilot_v2 import FocusedSingleHop, focused_prompt, map_sources


def test_scenario_styles_and_prompt_do_not_modify_ragas_defaults():
    from ragas.testset.synthesizers.single_hop.prompts import QueryAnswerGenerationPrompt
    from ragas.testset.persona import Persona
    from langchain_core.language_models.fake_chat_models import FakeListChatModel
    from ragas.llms import LangchainLLMWrapper
    synth = FocusedSingleHop(llm=LangchainLLMWrapper(FakeListChatModel(responses=["test"])))
    persona = Persona(name="Employee", role_description="Workplace questions")
    result = synth.prepare_combinations(object(), ["policy"], [persona], {"Employee": ["policy"]})
    assert result[0]["styles"] == [QueryStyle.PERFECT_GRAMMAR]
    assert result[0]["lengths"] == [QueryLength.MEDIUM]
    assert focused_prompt().instruction != QueryAnswerGenerationPrompt().instruction


def test_exact_source_mapping_and_ambiguous_source_rejection():
    doc = Document(page_content="Evidence", metadata={"document_id": "doc", "chunk_id": "chunk", "title": "Policy", "section_path": "Rules"})
    row = {"user_input": "Question?", "reference_contexts": ["Evidence"], "reference": "Answer"}
    mapped = map_sources([row], [doc])[0]
    assert mapped["reference_context_ids"] == ["chunk"]
    assert mapped["human_approved"] is False
    with pytest.raises(ValueError, match="source provenance"):
        map_sources([row], [doc, doc])
    with pytest.raises(ValueError, match="empty question or reference"):
        map_sources([{**row, "user_input": " "}], [doc])
