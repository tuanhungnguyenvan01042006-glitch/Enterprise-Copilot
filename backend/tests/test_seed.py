from types import SimpleNamespace

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models.department import Department
from app.models.user import User
from app.scripts import seed


def test_seed_skips_existing_employee_code_without_modifying_account(monkeypatch, capsys):
    engine = create_engine("sqlite://")
    Department.__table__.create(engine)
    User.__table__.create(engine)
    sessions = sessionmaker(bind=engine)
    with sessions.begin() as db:
        db.add(Department(id=1, code="OPERATIONS", name="Operations"))
        db.add(User(email="existing@example.test", password_hash="original-hash", full_name="Existing",
                    employee_code="E001", account_type="STAFF", department_role="EMPLOYEE",
                    department_id=1, is_active=True, must_change_password=False))
    settings = SimpleNamespace(seed_admin_password="admin", seed_manager_password="manager",
                               seed_employee_password="employee", seed_admin_email="admin@example.test",
                               app_env="development")
    monkeypatch.setattr(seed, "get_settings", lambda: settings)
    monkeypatch.setattr(seed, "SessionLocal", sessions)
    monkeypatch.setattr(seed, "hash_password", lambda password: "hashed-" + password)

    seed.seed()
    seed.seed()

    with sessions() as db:
        users = db.scalars(select(User)).all()
        existing = next(user for user in users if user.employee_code == "E001")
        assert existing.email == "existing@example.test"
        assert existing.password_hash == "original-hash"
        assert len(users) == 8
        assert not any(user.email == "employee01@gmail.com" for user in users)
    assert "employee code E001 already belongs" in capsys.readouterr().err
    engine.dispose()
