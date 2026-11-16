"""Token counts for the document embedding model and chunking."""

from functools import lru_cache
from tokenizers import Tokenizer


TOKENIZER_ID = "voyageai/voyage-4"


@lru_cache(maxsize=1)   # Hàm này lưu kết quả gần nhất để tái sử dụng, mỗi lần gọi hàm này , thì sẽ chỉ phải load lại tokenizer 1 lần , ko cần tải lại từ internet
def get_voyage_tokenizer() -> Tokenizer:
    tokenizer = Tokenizer.from_pretrained(TOKENIZER_ID)
    tokenizer.no_truncation()
    return tokenizer


def count_voyage_tokens(text: str) -> int:
    return len(get_voyage_tokenizer().encode(text).ids)
