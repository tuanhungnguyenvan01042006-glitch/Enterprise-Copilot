from __future__ import annotations

import sys

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.department import Department
from app.models.user import User


def _required_password(value: str | None, name: str) -> str:
    if not value:
        raise RuntimeError(f"{name} must be set before running the seed")
    return value


def seed() -> None:
    settings = get_settings()
    admin_password = _required_password(settings.seed_admin_password, "SEED_ADMIN_PASSWORD")
    manager_password = _required_password(settings.seed_manager_password, "SEED_MANAGER_PASSWORD")
    employee_password = _required_password(settings.seed_employee_password, "SEED_EMPLOYEE_PASSWORD")

    db = SessionLocal()
    try:
        department = db.scalar(select(Department).where(Department.code == "OPERATIONS"))
        if department is None:
            department = Department(id=1, code="OPERATIONS", name="Operations")
            db.add(department)
            db.flush()

        demo_must_change = settings.app_env.lower() == "production"
        accounts = [
            {
                "email": settings.seed_admin_email.strip().lower(),
                "password": admin_password,
                "full_name": "System Administrator",
                "employee_code": None,
                "job_title": "System Administrator",
                "account_type": "ADMIN",
                "department_role": None,
                "department_id": None,
            },
            {
                "email": "manager@gmail.com",
                "password": manager_password,
                "full_name": "Operations Manager",
                "employee_code": "M001",
                "job_title": "Operations Manager",
                "account_type": "STAFF",
                "department_role": "MANAGER",
                "department_id": department.id,
            },
        ]
        accounts.extend(
            {
                "email": f"employee{number:02d}@gmail.test",
                "password": employee_password,
                "full_name": f"Operations Employee {number:02d}",
                "employee_code": f"E{number:03d}",
                "job_title": "Operations Specialist",
                "account_type": "STAFF",
                "department_role": "EMPLOYEE",
                "department_id": department.id,
            }
            for number in range(1, 7)
        )

        created = 0
        for account in accounts:
            user = db.scalar(select(User).where(User.email == account["email"]))
            if user is not None:
                continue
            db.add(
                User(
                    email=account["email"],
                    password_hash=hash_password(account["password"]),
                    full_name=account["full_name"],
                    employee_code=account["employee_code"],
                    job_title=account["job_title"],
                    account_type=account["account_type"],
                    department_role=account["department_role"],
                    department_id=account["department_id"],
                    is_active=True,
                    must_change_password=demo_must_change,
                )
            )
            created += 1
        db.commit()
        print(f"Seed complete: department=1, accounts_created={created}, accounts_total={len(accounts)}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    try:
        seed()
    except Exception as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

