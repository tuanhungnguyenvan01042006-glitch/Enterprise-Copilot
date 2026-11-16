"""Configure the OpenAI judge and Voyage embeddings for Ragas evaluation."""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_voyageai import VoyageAIEmbeddings
from ragas.testset import TestsetGenerator

from app.RAG.config import DOCUMENT_EMBEDDING_MODEL, EMBEDDING_DIMENSION

PROJECT_ROOT = Path(__file__).resolve().parents[2]

"""
file này thực hiện 2 nhiệm vụ : Gọi LLM sử dụng cho testset, và thực hiện hàm testsetGenerator
+ mặc dù đều có hàm có sẵn, nhưng ta vẫn đóng gói các hàm có sẵn này vào trong hàm nội bộ, chủ yếu là để kiểm tra input đầu vào đã ổn chưa 

"""

def make_openai_llm() -> ChatOpenAI:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    if not os.getenv("OPENAI_API_KEY", "").strip():
        raise ValueError("OPENAI_API_KEY is missing; configure it in the environment or project .env")
    model = os.getenv("OPENAI_EVAL_MODEL", "gpt-4o-mini").strip()
    if not model:
        raise ValueError("OPENAI_EVAL_MODEL must not be empty")
    return ChatOpenAI(model=model, temperature=0)


def make_testset_generator() -> TestsetGenerator:
    llm = make_openai_llm()
    if not os.getenv("VOYAGE_API_KEY", "").strip():
        raise ValueError("VOYAGE_API_KEY is missing; configure it in the environment or project .env")
    embeddings = VoyageAIEmbeddings(model=DOCUMENT_EMBEDDING_MODEL, output_dimension=EMBEDDING_DIMENSION, truncation=False)
    return TestsetGenerator.from_langchain(llm=llm, embedding_model=embeddings)
"""
* Giải thích hàm TestsetGenerator.from_langchain() : 
+ Điều đặc biệt là hàm này cần cả LLM và Embedding model :
+ Đương nhiên cần LLM (bộ não) để có khả năng sinh ra câu hỏi từ Chunks có sẵn, vậy tại sao cần Embeding Model: 
 * NOTE : Embeding model này có thể truyền vào 1 Embeding model bất kì, ko cần cùng loại với Embeding model dùng để Embeding chunks/querry
 - Mô tả dễ hiểu : Embeding model này sẽ dùng để embed các chunks, và để đo Sematic similarity giữa các chunks
 + Những chunks có nội dung liên quan nhiều đến nhau, sẽ được sử dụng để tạo câu hỏi 
  - Mặc dù theo mình LLM có thể thực hiện việc này : Ví dụ như prompt : hãy dựa trên các chunks có nội dung liên quan nhau ---> tạo câu hỏi
  vì LLM có khả năng general, nên maybe, nó có thể xử lý tác vụ này , nhưng ta nên dùng embeding để tính toán ra số liệu cụ thể, đàng hoàng
* NOTE : Thực tế đối tượng Generator này có các trường : LLM, Embedding model, Knowledge graph (lưu chunks), persona list (vai trò người hỏi), llm context : những chỉ dẫn , bổ sung ngữ cảnh giúp LLM có thể trả lời đúng theo Context project
"""