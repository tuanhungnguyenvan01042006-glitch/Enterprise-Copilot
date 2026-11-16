from app.RAG.Chunking import tokenizer


class WhitespaceTokenizer:
    def encode(self, text: str):
        from types import SimpleNamespace
        return SimpleNamespace(ids=text.split())

    def no_truncation(self):
        pass


def test_token_counter_uses_voyage_tokenizer(monkeypatch):
    fake_tokenizer = WhitespaceTokenizer()
    monkeypatch.setattr(tokenizer, "get_voyage_tokenizer", lambda: fake_tokenizer)

    assert tokenizer.count_voyage_tokens("một tài liệu RAG") == 4


def test_voyage_tokenizer_is_loaded_lazily_and_cached(monkeypatch):
    calls = []
    fake_tokenizer = WhitespaceTokenizer()

    def load_tokenizer(model_id: str):
        calls.append(model_id)
        return fake_tokenizer

    monkeypatch.setattr(tokenizer.Tokenizer, "from_pretrained", load_tokenizer)
    tokenizer.get_voyage_tokenizer.cache_clear()
    try:
        first = tokenizer.get_voyage_tokenizer()
        second = tokenizer.get_voyage_tokenizer()
    finally:
        tokenizer.get_voyage_tokenizer.cache_clear()

    assert first is second
    assert calls == ["voyageai/voyage-4"]
