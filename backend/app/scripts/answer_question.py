"""Thử retrieval và generation nội bộ, chưa kiểm tra quyền truy cập."""

import argparse
import json
import sys

from app.RAG.service import answer_question


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Answer a question using indexed documents (internal only).")
    parser.add_argument("query", help="Question to answer.")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    print(json.dumps(answer_question(args.query, args.top_k), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
