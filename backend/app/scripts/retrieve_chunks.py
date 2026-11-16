"""Chạy retrieval nội bộ để kiểm tra kết quả trước khi benchmark."""
# Giải thích : Thực tế cần file này, tại vì chưa có luồng Backend chatbot , nơi 
# mình nhập vào querry, sau đó đem đi retrieve 
import argparse
import json

from app.RAG.service import retrieve_chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Search indexed chunks (internal benchmarking only).")
    parser.add_argument("query", help="Question to search for.")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    print(json.dumps(retrieve_chunks(args.query, args.top_k), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
 