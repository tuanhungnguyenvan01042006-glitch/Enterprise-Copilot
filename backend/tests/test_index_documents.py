from types import SimpleNamespace
from uuid import uuid4

from app.scripts import index_documents


def test_bulk_index_continues_after_failure_and_reports_summary(tmp_path, monkeypatch, capsys):
    good = SimpleNamespace(id=uuid4(), storage_key="good.md", knowledge_scope="COMPANY",
                           department_id=None, title="Good", category="GUIDE")
    missing = SimpleNamespace(id=uuid4(), storage_key="missing.md", knowledge_scope="COMPANY",
                              department_id=None, title="Missing", category="GUIDE")
    (tmp_path / "good.md").write_text("# Hello", encoding="utf-8")
    class Session:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def scalars(self, statement): return [good, missing]
    calls = []
    monkeypatch.setattr(index_documents, "SessionLocal", Session)
    monkeypatch.setattr(index_documents, "get_settings", lambda: SimpleNamespace(upload_dir=tmp_path))
    monkeypatch.setattr(index_documents, "index_uploaded_document", lambda path, **kwargs: calls.append((path, kwargs)) or True)
    assert index_documents.index_documents(limit=2) == 1
    assert calls[0][1]["document_id"] == good.id
    output = capsys.readouterr().out
    assert f"FAILED {missing.id}" in output
    assert "indexed=1, failed=1, total=2" in output
