# Quản lý các thông số RAG : ví dụ số chunking, dùng model embed nào,..
"""
Framework:        LangChain
Vector Database:  Qdrant
Document Model:   voyage-4
Query Model:      voyage-4-lite
LLM:              API-based LLM
Corpus Storage:   Local filesystem / server storage
App Database:     PostgreSQL
Evaluation:       Retrieval + Generation + Citation metrics
"""

DOCUMENT_EMBEDDING_MODEL = "voyage-4"
QUERY_EMBEDDING_MODEL = "voyage-4-lite"
EMBEDDING_DIMENSION = 1024
