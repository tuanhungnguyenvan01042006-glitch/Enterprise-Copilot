import pytest

from evaluation import openai_config


def test_generator_initializes_with_configured_models_without_network(monkeypatch):
    monkeypatch.setattr(openai_config, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-voyage-key")
    monkeypatch.setenv("OPENAI_EVAL_MODEL", "gpt-4o-mini")
    assert openai_config.make_openai_llm().model_name == "gpt-4o-mini"
    assert openai_config.make_testset_generator() is not None


def test_missing_openai_key_has_actionable_error(monkeypatch):
    monkeypatch.setattr(openai_config, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY is missing"):
        openai_config.make_openai_llm()


def test_missing_voyage_key_has_actionable_error(monkeypatch):
    monkeypatch.setattr(openai_config, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="VOYAGE_API_KEY is missing"):
        openai_config.make_testset_generator()
