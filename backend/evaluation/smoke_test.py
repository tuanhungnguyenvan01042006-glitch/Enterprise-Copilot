"""Check Ragas integration locally without calling any external APIs."""

import os

os.environ.setdefault("RAGAS_DO_NOT_TRACK", "true")

from langchain_core.embeddings import FakeEmbeddings
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from ragas.dataset_schema import SingleTurnSample
from ragas.metrics import IDBasedContextRecall
from ragas.testset import TestsetGenerator

from app.RAG.service import retrieve_chunks

# File này chủ yếu để kiểm tra những Tác vụ Cơ bản nhất của quá trình Eval, nhằm tìm ra những lỗi rất to 
# ví dụ như : Kết nối tới model, tạo TestsetGenerator, Retriveve chunks, khả năng tính toán của Ragas

def main() -> None:
    generator = TestsetGenerator.from_langchain(
        llm=FakeListChatModel(responses=["test"]),
        embedding_model=FakeEmbeddings(size=1024),
    )
    assert generator is not None and callable(retrieve_chunks)
    # lệnh assert yêu cầu 2 điều kiện phải đúng, nếu không nó sẽ đưa ra AssertionError, dừng ctrinh
    sample = SingleTurnSample(retrieved_context_ids=["a", "c"], reference_context_ids=["a", "b"])
    score = IDBasedContextRecall().single_turn_score(sample)
    assert abs(score - 0.5) < 1e-6, score
    # kiểm tra xem Ragas có tính điểm IDBasedContextRecall đúng không 
    print(f"Ragas generator, retrieval import and ID-based recall smoke test passed (score={score:.2f})")


if __name__ == "__main__":
    main()
