
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("RAGAS_DO_NOT_TRACK", "true")

import voyageai
from langchain_community.callbacks.manager import get_openai_callback
from langchain_core.documents import Document
from qdrant_client import QdrantClient, models
from ragas.run_config import RunConfig
from ragas.testset.synthesizers import SingleHopSpecificQuerySynthesizer
# Cái này quan trọng : Đây là style tạo ra câu hỏi của Ragas mà ta config nó : SingleHop

from openai_config import make_testset_generator

OUTPUT_DIR = Path(__file__).resolve().parent / "pilot"
SELECTION = [
    ("Ask Me Anything", 2),
    ("GitLab Internal Acceptable Use Policy", 8),
    ("Global Travel and Expense Policy", 6),
]


def load_source_chunks(selection=SELECTION) -> list[Document]:
    # Khởi tạo client Qdrant, để chuẩn bị tìm kiếm Chunks trong Qdrant dựa trên các Selection đã chọn 
    client = QdrantClient(url=os.getenv("EVALUATION_QDRANT_URL", "http://localhost:6333"))
    collection = os.getenv("QDRANT_COLLECTION", "rag_documents")
    documents = []
    try:
        for title, index in selection:
            points, _ = client.scroll(
                collection, limit=2, with_payload=True, with_vectors=False,
                scroll_filter=models.Filter(must=[
                    models.FieldCondition(key="title", match=models.MatchValue(value=title)),
                    models.FieldCondition(key="chunk_index", match=models.MatchValue(value=index)),
                ]),   # Vậy Qdrant hỗ trợ tìm kiếm chunks theo metadata (key)
            )
            if len(points) != 1:
                raise ValueError(f"Expected one source chunk for {title}, chunk index {index}; got {len(points)}")
            payload = dict(points[0].payload or {})
            text = payload.pop("text")
            documents.append(Document(page_content=text, metadata=payload))
    finally:
        client.close()
        # Trả về danh sách chunks lấy trực tiếp từ Qdrant ( chỉ qdrant lưu chunks chứ các nguồn external / storage ko chứa chunks)
    return documents


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    # OUTPUT Dir : Nơi lưu testset được tạo ra là file test raw.json
    output = OUTPUT_DIR / "testset_raw.json"
    if output.exists():
        raise FileExistsError(f"{output} already exists; preserve it before rerunning")
    generator = make_testset_generator()   # gọi lại hàm Generate testset, tạo ra Generator
    documents = load_source_chunks()
    sources = [{"metadata": d.metadata, "text": d.page_content} for d in documents]
    (OUTPUT_DIR / "sources.json").write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    voyage_usage = {"requests": 0, "input_tokens": 0, "missing_usage": 0}
    original_embed = voyageai.AsyncClient.embed

    async def track_voyage(client, *args, **kwargs):
        response = await original_embed(client, *args, **kwargs)
        voyage_usage["requests"] += 1
        tokens = getattr(response, "total_tokens", None)
        if tokens is None:
            voyage_usage["missing_usage"] += 1
        else:
            voyage_usage["input_tokens"] += tokens
        return response

    voyageai.AsyncClient.embed = track_voyage
    started = datetime.now(timezone.utc)
    try:
        with get_openai_callback() as usage:
            try:
                async def generate():
                    # Đây là phần quan trọng nhất 
                    return generator.generate_with_langchain_docs(   #Generator là đối tượng Generatortestset của Ragas 
                        documents, testset_size=6,
                        query_distribution=[(SingleHopSpecificQuerySynthesizer(llm=generator.llm), 1.0)],
                        run_config=RunConfig(max_workers=2, timeout=180),
                        raise_exceptions=True,
                    )
                testset = asyncio.run(generate())
                # Vậy ta có thể thấy, thực tế Generator ở phiên bản pilot này chỉ nhận vào 2 tham số : Documents (chunks), và querry distribution (các loại querry khác nhau : SingleHop, MultiHop)
                rows = testset.to_list()
                output.write_text(json.dumps(rows, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
                print(f"Generated {len(rows)} questions: {output}")
            finally:
                stats = {
                    "started_at_utc": started.isoformat(),
                    "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                    "openai_model": os.getenv("OPENAI_EVAL_MODEL", "gpt-4o-mini"),
                    "openai_successful_requests": usage.successful_requests,
                    "openai_input_tokens": usage.prompt_tokens,
                    "openai_output_tokens": usage.completion_tokens,
                    "openai_cost_usd_callback_estimate": usage.total_cost,
                    "voyage_model": "voyage-4",
                    "voyage_usage": voyage_usage,
                }
                (OUTPUT_DIR / "usage.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
                print("Usage:", json.dumps(stats))
    finally:
        voyageai.AsyncClient.embed = original_embed


if __name__ == "__main__":
    main()

