from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict[str, str]:
    """Verify database connectivity and that the persistent upload volume is writable."""
    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    probe = upload_dir / f".healthcheck-{uuid4().hex}"
    try:
        db.execute(text("SELECT 1"))
        upload_dir.mkdir(parents=True, exist_ok=True)
        probe.write_bytes(b"ready")
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Required infrastructure is unavailable",
        ) from exc
    finally:
        try:
            probe.unlink(missing_ok=True)
        except OSError:
            pass
    return {"status": "ready"}
