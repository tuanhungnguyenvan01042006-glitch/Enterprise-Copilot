"""Inspect or remove private upload files that have no database reference."""

import argparse
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.document import Document


def run(apply: bool) -> int:
    root = get_settings().upload_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    try:
        referenced = {Path(document.storage_key).as_posix() for document in db.scalars(select(Document)).all()}
    finally:
        db.close()

    orphaned = []
    for path in root.rglob("*"):
        if not path.is_file() or ".tmp" in path.parts:
            continue
        if path.relative_to(root).as_posix() not in referenced:
            orphaned.append(path)

    for path in orphaned:
        print(f"ORPHAN {'REMOVE' if apply else 'WOULD_REMOVE'} {path.relative_to(root)}")
        if apply:
            path.unlink(missing_ok=True)
    print(f"Orphan files: {len(orphaned)} ({'applied' if apply else 'dry-run'})")
    return len(orphaned)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect or clean unreferenced document upload files")
    parser.add_argument("--apply", action="store_true", help="Delete orphaned files; default is dry-run")
    args = parser.parse_args()
    run(args.apply)
