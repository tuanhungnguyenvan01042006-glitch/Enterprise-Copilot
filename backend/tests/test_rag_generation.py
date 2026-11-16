from types import SimpleNamespace

import pytest

from app.RAG import generation, service


CHUNKS = [
    {"text": "Nhân viên được nghỉ phép.", "document_id": "doc-1", "chunk_id": "chunk-1",
     "title": "Sổ tay", "section_path": "Nghỉ phép", "score": 0.9},
    {"text": "Quy trình gửi đơn.", "document_id": "doc-2", "chunk_id": "chunk-2",
     "title": "Quy trình", "section_path": "Đơn nghỉ"},
]


def mock_model(monkeypatch, response):
    monkeypatch.setattr(generation, "get_settings", lambda: SimpleNamespace(
        openai_api_key="test-key", openai_generation_model="gpt-4o-mini"))
    calls = {}

    class FakeModel:
        def __init__(self, **kwargs):
            calls["config"] = kwargs

        def with_structured_output(self, schema, method):
            calls["schema"] = schema
            calls["method"] = method
            return self

        def invoke(self, messages):
            calls["messages"] = messages
            if isinstance(response, Exception):
                raise response
            return response

    monkeypatch.setattr(generation, "ChatOpenAI", FakeModel)
    return calls


def test_generate_answer_returns_only_cited_sources(monkeypatch):
    calls = mock_model(monkeypatch, generation.ModelAnswer(answer="Gửi đơn [2].", source_numbers=[2]))
    result = generation.generate_answer("Làm thế nào?", CHUNKS)
    assert result == {"answer": "Gửi đơn [2].", "sources": [{"number": 2, "document_id": "doc-2",
                      "chunk_id": "chunk-2", "title": "Quy trình", "section_path": "Đơn nghỉ"}]}
    assert calls["config"]["model"] == "gpt-4o-mini"
    assert calls["method"] == "function_calling"
    assert "Nhân viên được nghỉ phép." in calls["messages"][1][1]


def test_empty_context_needs_no_model_or_api_key(monkeypatch):
    monkeypatch.setattr(generation, "get_settings", lambda: pytest.fail("No model needed"))
    assert generation.generate_answer("Câu hỏi", []) == {
        "answer": "Không tìm thấy thông tin liên quan trong tài liệu.", "sources": []}


@pytest.mark.parametrize("answer,numbers", [("Nguồn [3].", [3]), ("Nguồn [3].", [1])])
def test_invalid_citations_are_rejected(monkeypatch, answer, numbers):
    mock_model(monkeypatch, generation.ModelAnswer(answer=answer, source_numbers=numbers))
    with pytest.raises(ValueError, match="citations"):
        generation.generate_answer("Câu hỏi", CHUNKS)


def test_inconsistent_citations_are_retried(monkeypatch):
    calls = mock_model(monkeypatch, generation.ModelAnswer(answer="Nguồn [1].", source_numbers=[1]))
    responses = iter([
        generation.ModelAnswer(answer="Nguồn [3].", source_numbers=[3]),
        generation.ModelAnswer(answer="Nguồn [1].", source_numbers=[1]),
    ])
    class RetryModel:
        def __init__(self, **kwargs):
            pass

        def with_structured_output(self, schema, method):
            return self

        def invoke(self, messages):
            calls["retry_messages"] = messages[:]
            return next(responses)

    monkeypatch.setattr(generation, "ChatOpenAI", RetryModel)
    result = generation.generate_answer("Câu hỏi", CHUNKS)
    assert result["sources"][0]["chunk_id"] == "chunk-1"
    assert "invalid source" in calls["retry_messages"][-1][1]


def test_missing_inline_citations_are_added_from_model_sources(monkeypatch):
    mock_model(monkeypatch, generation.ModelAnswer(answer="Thông tin từ tài liệu.", source_numbers=[2]))
    result = generation.generate_answer("Câu hỏi", CHUNKS)
    assert result["answer"] == "Thông tin từ tài liệu.\n\nSources: [2]"
    assert [source["chunk_id"] for source in result["sources"]] == ["chunk-2"]


def test_inconsistent_valid_sources_are_reconciled(monkeypatch):
    mock_model(monkeypatch, generation.ModelAnswer(answer="Thông tin [1].", source_numbers=[2]))
    result = generation.generate_answer("Câu hỏi", CHUNKS)
    assert result["answer"] == "Thông tin [1].\n\nSources: [2]"
    assert [source["number"] for source in result["sources"]] == [1, 2]


def test_model_errors_propagate(monkeypatch):
    mock_model(monkeypatch, RuntimeError("provider unavailable"))
    with pytest.raises(RuntimeError, match="provider unavailable"):
        generation.generate_answer("Câu hỏi", CHUNKS)


def test_service_connects_retrieval_to_generation(monkeypatch):
    monkeypatch.setattr(service, "retrieve_chunks", lambda query, top_k: CHUNKS if top_k == 2 else [])
    monkeypatch.setattr(service, "generate_answer", lambda query, chunks: {"query": query, "chunks": chunks})
    assert service.answer_question("Câu hỏi", 2) == {"query": "Câu hỏi", "chunks": CHUNKS}
