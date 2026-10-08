"""Batch-import Markdown documents from the GitLab Handbook.

Each source file becomes one Document with one current file. The document UUID
is deterministic for a source-relative path, so rerunning the importer is safe
when the source file has not changed.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

import app.db.base  # Register every ORM table referenced by Document foreign keys.
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.user import User


PROJECT_ROOT = Path(__file__).resolve().parents[3]  
# lấy địa chỉ thư mục hiện tại, sau đó đi lên 4 bậc để tìm Project root
IMPORT_NAMESPACE = uuid.UUID("b6ec1e5a-2a6d-4c60-91c9-83e8ba62d3d3")
# cái này để sau tại ID cho Document.
FRONT_MATTER_BOUNDARY = re.compile(r"^---\s*$")
DOCUMENT_CATEGORIES = ("POLICY", "SOP", "GUIDE", "REFERENCE")
# Thư viện re, và hàm compile() để tạo ra một đối tượng regex pattern.
# Có dạng giống chuỗi mở đầu và kết thúc chứa Metadata --> để đoạn sau parse (trích xuất) được Metadata : Title, Description, ...


@dataclass(frozen=True)
class SourceDocument:         # hiểu đơn giản, đây là đang định nghĩa class mới, là Source Document, dùng để lưu trữ thông tin về các tài liệu nguồn (source documents) mà bạn muốn nhập vào hệ thống.
    path: Path
    relative_path: str
    title: str
    description: str | None
    category: str
    size_bytes: int
    checksum_sha256: str


def _parse_args() -> argparse.Namespace:  # hàm trả về Namepsace : là 1 đối tượng để chứa các tham số mà arparse đọc được từ lệnh 
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Import GitLab Handbook Markdown files into the knowledge base.")
    # argparse là thư viện python để trích xuất tham số từ lệnh Terminal
    parser.add_argument(
    # Hàm add_argument có tác dụng khai báo 1 tham số mà ng dùng có thể truyền vào khi chạy lệnh terminal. Argparse sẽ đọc tham số và đưa vào namespace
        "--source-dir",     # ở đây khai báo tham số --source-dir (tham số trong lệnh terminal), là đường dẫn đến thư mục chứa các file Markdown cần import
        type=Path,    # chuyển giá trị người dùng nhập thành đối tượng Path (thư viện pathlib) để dễ dàng thao tác với đường dẫn
        default=PROJECT_ROOT / ".external" / "gitlab-handbook" / "content",
        # giá trị mặc định là đường dẫn tới địa chỉ external lưu documents
        help="Directory containing Markdown files (default: .external/gitlab-handbook/content).",
    )
    parser.add_argument(
        "--upload-dir",
        type=Path,
        default=settings.upload_dir,
        help="Storage root used by the API (default: UPLOAD_DIR).",
    )
    parser.add_argument(
        "--actor-email",
        default=settings.seed_admin_email,
        help="Existing user recorded as created_by/uploaded_by (default: SEED_ADMIN_EMAIL).",
    )
    parser.add_argument(
        "--language",
        choices=("vi", "en", "other"),
        default="en",
        help="Language assigned to imported documents (default: en).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report the import without copying files or committing database rows.",
    )
    return parser.parse_args()


def _resolve_path(path: Path) -> Path:
    return path.expanduser().resolve()


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


# hàm này nhận vào Documents, và sẽ trả về riêng 2 phần : Metadata và nội dung Documents
def _front_matter_and_body(text: str) -> tuple[dict[str, str], str]:
    lines = text.splitlines()    # tách Documents thành từng dòng 
    if not lines or not FRONT_MATTER_BOUNDARY.match(lines[0]):   # nếu file rỗng (ko có line nào) hoặc dòng đầu tiên ko phải định dạng regex của phần Metadata
        return {}, text

    end_index = next((index for index in range(1, len(lines)) if FRONT_MATTER_BOUNDARY.match(lines[index])), None)
    # tìm dòng (index) kết thúc Metadata ( --- )
    if end_index is None:
        raise ValueError("front matter starts with '---' but has no closing '---'")

    metadata: dict[str, str] = {}
    for line in lines[1:end_index]:
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key in {"title", "description", "category"}:
            metadata[key] = _unquote(value)
    body = "\n".join(lines[end_index + 1 :])
    return metadata, body   # trả về metadata và body (nội dung Documents)

# hàm này dùng khi trong meta data ko có title
# truyền vào đường dẫn của Documents đó (và ta sẽ dùng đường dẫn đó để tạo tạm titile cho Documents)
def _fallback_title(path: Path) -> str:
    stem = path.stem   # lấy tên file ko có phần mở rộng 
    if stem == "_index":   # nếu file tên là index, thì lấy tên thư mục cha làm title
        stem = path.parent.name or "Handbook"
    return re.sub(r"[-_]+", " ", stem).strip().title()


# File Documents sẽ được chuẩn hóa thành 1 dạng class là SourceDocument : chứa các trường liên quan đến dữ liệu gốc
# sau đó mới chuyển từ SourceDocument sang Document để lưu vào database ( thêm 1 số trường để đầy đủ thông tin)
# chứ ko phải là ta trích xuất thông tin từ file rồi trực tiếp khởi tạo Document, lưu trong DB
# Ta sinh ra bước này, để tách biệt giữa dữ liệu gốc (dữ liệu được lưu trong Documents gốc) và dữ liệu lưu trong DB (dữ liệu thêm vào để phục vụ hệ thống, bài toán).
def _read_source(path: Path, source_root: Path) -> SourceDocument:
    # nhận vào 2 tham số : Path của Documents ,và source_root : đường dẫn thư mục gốc chứa toàn bộ handbook
    text = path.read_text(encoding="utf-8-sig")  # đọc toàn bộ nội dung của file từ path Document
    # hàm read_text có chức năng đọc nội dung của file và trả về chuỗi (string) chứa nội dung đó. Ở đây, encoding được đặt là "utf-8-sig" để xử lý các file có BOM (Byte Order Mark) nếu có.
    metadata, _ = _front_matter_and_body(text) # lấy ra metadata và body (nội dung Documents) từ file Markdown
    title = (metadata.get("title") or _fallback_title(path)).strip()
    description = metadata.get("description")
    description = description.strip() if description and description.strip() else None
    category = (metadata.get("category") or "").strip().upper()

    if not title:
        raise ValueError("title is empty")
    if category not in DOCUMENT_CATEGORIES:
        allowed_categories = ", ".join(DOCUMENT_CATEGORIES)
        raise ValueError(f"category must be one of: {allowed_categories}")
    if len(title) > 200:
        raise ValueError(f"title is longer than 200 characters ({len(title)})")
    if description and len(description) > 2000:
        description = description[:2000]

    digest = hashlib.sha256()   # đối tượng tính mã băm, hoặc đúng hơn là mã hóa tài liệu : sang 1 dạng khác gọn nhẹ hơn
    size_bytes = 0       
    with path.open("rb") as source_file:       #  Mở file ở chế độ đọc nhị phân 
        while chunk := source_file.read(1024 * 1024):   # đọc file theo từng khối 1MB 
            size_bytes += len(chunk)
            digest.update(chunk)        # digest là đối tượng băm, trong mỗi vòng lặp, nó lại nhận thêm 1 chunk dữ liệu mới để tính toán mã băm tổng thể của toàn bộ file. Khi vòng lặp kết thúc, digest sẽ chứa mã băm SHA-256 của toàn bộ nội dung file.
    if size_bytes == 0:
        raise ValueError("file is empty")

    return SourceDocument(
        path=path,
        relative_path=path.relative_to(source_root).as_posix(),
        title=title,
        description=description,
        category=category,
        size_bytes=size_bytes,
        checksum_sha256=digest.hexdigest(),    # vai trò của mã băm / Checksum là để kiểm tra xem file gốc và file sau khi đưa vào Storage (trong BE) có giống nhau không
                                         # bởi 2 file giống hệt nhau sẽ có cùng mã băm, và nhiều tác dụng khác dựa trên 
    )
# Tóm lại hàm này nhận vào đường tài liệu gốc, trả về Object SourceDocument, để sau dễ quản lý, và add vào DB Documents, chứ chưa chuyển nội dung file vào storage 
# Tức là file gốc ta vẫn chưa quản lý nó theo metadata, mà chỉ là file raw nằm ở External. Nên cần sinh ra SourceDocument để quản lý tài liệu ban đầu 

def _stable_id(relative_path: str) -> uuid.UUID:
    return uuid.uuid5(IMPORT_NAMESPACE, f"document:{relative_path}")


def _copy_to_storage(source: Path, destination: Path) -> None:
    # Note : Destination là đường dẫn, đã bao gồm cả tên file, và destination.parent sẽ thư mục chứa fie đó, còn destination.name là tên file đó
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.importing-{uuid.uuid4().hex}")
    # Tạo file temporary với tên tạm thời dựa trên tên file đích, để tránh xung đột với các file khác trong quá trình sao chép.
    try:
        shutil.copyfile(source, temporary)  # chép nội dung file nguồn vào file tạm 
        temporary.replace(destination)      # đổi tên file tạm thành tên file đích (nếu file đích đã tồn tại, nó sẽ bị ghi đè)
    finally:
        temporary.unlink(missing_ok=True)

    # Đây là 1 quy trình chép file an toàn rất quen thuộc, ta cx bắt gặp nó trong tính năng upload file (cx phải chép ra file temp trước)

def _load_actor(db, email: str) -> User:
    actor = db.scalar(select(User).where(User.email == email.strip().lower()))
    if actor is None:
        raise RuntimeError(f"Cannot find import user: {email}")
    if actor.account_type != "ADMIN":
        raise RuntimeError(f"Import user must have account_type=ADMIN: {email}")
    return actor
# Tức là hàm này nhằm đảm bảo chỉ Admin mới có quyền import tài liệu, nhưng nếu vậy có nghĩa là ta lại phải xây API,UI cho chức năng này à ??


def _import_one(           # Đây là hàm import từng Document 
    db,
    source: SourceDocument,
    upload_root: Path,
    actor: User,
    language: str,
    dry_run: bool,
    copied_path: list[Path | None] | None = None,
) -> str:
    document_id = _stable_id(source.relative_path)  # Tạo Document ID dựa trên đường dẫn tương đối (tức là dựa trên tên file, vì vậy 2 file nếu cùng đường dẫn sẽ cùng id)
    existing_document = db.get(Document, document_id)   # Tìm trong DB có tài liệu nào có ID tương tự không
    storage_key = existing_document.storage_key if existing_document is not None else f"COMPANY/{document_id}/{document_id}.md"
    
    destination = upload_root / storage_key

    if existing_document is not None:    # Đây là trường hợp tài liệu (cùng id : tên) đã tồn tại 
        # nếu tài liệu đã tồn tại, ta xử lý tiếp tục như sau : 
        if existing_document.checksum_sha256 != source.checksum_sha256: # kiểm tra nội dung file, nếu khác nhau thì báo lỗi, vì ta ko muốn ghi đè file cũ (vì có thể file cũ đang được dùng)
            raise RuntimeError(
                f"Imported file checksum changed: {source.relative_path}; refusing to overwrite the current file."
            )
        # Còn nếu nội dung file giống nhau, thì kiểm tra file đích có tồn tại ko? Nếu chưa : thì import file vào | Còn nếu file đích tồn tại, thì in ra skip 
        if not destination.is_file():     # Kiểm tra xem file đích có tồn tại không, nếu không, thì bắt đầu chạy các lệnh phía sau
            # Dry run mode : chạy thử nghiệm để xem có xảy ra lỗi gì không 
            if dry_run: 
                return f"RESTORE_FILE {source.relative_path}"   # nếu đang chạy thử thì in ra thông báo restore (do hiện tại ko có file nào bên trong, nên ta có thể upload flie vào vị trí đó, tức chính là resotore file tại địa chỉ đó)
            if copied_path is not None:
                copied_path[0] = destination
            _copy_to_storage(source.path, destination)
        return f"SKIP {source.relative_path}"  # nếu tồn tại file đích, thì in ra skip :vì ko muốn ghi đè

    if dry_run:
        return f"CREATE {source.relative_path} -> {storage_key}"   # in ra thông báo create  nếu, ko có Document cùng document id trong db
    # vậy bản chất của dry run chỉ là kiểm tra xem luồng có chạy ổn không (luồng chạy đến đâu in ra thông báo đến đấy), và có lỗi gì không, chứ ko hề chạy 1 tác vụ nào 
    copied = False
    try:
        if copied_path is not None:
            copied_path[0] = destination
        _copy_to_storage(source.path, destination)  # Copy nội dung file từ external vào Storage 
        copied = True   # copy thành công, thì chuyển copied thành true 
        db.add(
            Document(
                id=document_id,
                knowledge_scope="COMPANY",
                department_id=None,
                title=source.title,
                description=source.description,
                category=source.category,
                language=language, # cái này lấy ở đâu ? 
                created_by=actor.id,
                updated_by=actor.id,
                original_filename=source.path.name[:255],
                storage_key=storage_key,    
                mime_type="text/markdown",
                size_bytes=source.size_bytes,
                checksum_sha256=source.checksum_sha256,
                uploaded_by=actor.id,
                uploaded_at=datetime.now(timezone.utc),
                revision=1,
            )
        )
        db.add(
            AuditLog(
                actor_id=actor.id,
                action="DOCUMENT_IMPORTED",
                entity_type="document",
                entity_id=str(document_id),
                result="SUCCESS",
                request_id="handbook-import",
                details={"source_path": source.relative_path, "file": source.path.name},
            )
        )
        db.flush()
        return f"CREATE {source.relative_path} -> {storage_key}"
    except Exception:
        if copied:
            destination.unlink(missing_ok=True)
        raise


def import_handbook(args: argparse.Namespace) -> int:
    source_root = _resolve_path(args.source_dir)   # Tham số Source root : Thư mục source chứa toàn bộ Document .external/.../handbook
    upload_root = _resolve_path(args.upload_dir)   # thư mục 
    if not source_root.is_dir():
        raise RuntimeError(f"Cannot find source directory: {source_root}")

    paths = sorted(path for path in source_root.rglob("*.md") if path.is_file() and not path.is_symlink())
    # hàm source root.rglob("*.md") tìm tất cả file đuôi md trong thư mục nguồn và mọi thư mục con 
    # Paths là dsach đường dẫn tới tất cả file Markdown hợp lệ 
    if not paths:
        raise RuntimeError(f"Cannot find Markdown files in: {source_root}")

    # đây là đoạn chuyển từ path thành SourceDocument
    sources: list[SourceDocument] = []   #Sources : danh sách SourceDocument
    for path in paths:
        try:
            sources.append(_read_source(path, source_root))  
            # ở đây, read source là hàm viết từ rước đó, nó sẽ đọc và kiểm tra file raw, sau đó trả về SourceDocument với đầy đủ metadata
            # hàm append : thêm đối tượng đó vào List
        except Exception as exc:
            raise RuntimeError(f"Cannot read {path.relative_to(source_root)}: {exc}") from exc

    db = SessionLocal()
    created = skipped = restored = 0
    try:
        actor = _load_actor(db, args.actor_email)
        # Ở đây hàm load actor, vốn đã dùng lệnh select ( nghĩa là đã begin 1 transaction)
        db.commit()    # Vậy nên ngay đoạn dưới này ta cần commit.
        print(f"Source: {source_root}")
        print(f"Upload root: {upload_root}")
        print(f"Markdown files: {len(sources)}")
        print(f"Actor: {actor.email} ({actor.id})")
        if args.dry_run:
            print("Mode: DRY RUN")

        for source in sources:
            copied_path: list[Path | None] = [None]
            try:
                if db.in_transaction():
                    db.rollback()
                result = _import_one(
                    db=db,
                    source=source,
                    upload_root=upload_root,
                    actor=actor,
                    language=args.language,
                    dry_run=args.dry_run,
                    copied_path=copied_path,
                )
                # _import_one() may execute a SELECT (dry-run/skip) or flush
                # new rows. Commit explicitly so the next file starts with a
                # clean Session transaction in SQLAlchemy 2.x.
                db.commit()
                
                copied_path[0] = None
                print(result)
                if result.startswith("CREATE "):
                    created += 1
                elif result.startswith("RESTORE_FILE "):
                    restored += 1
                else:
                    skipped += 1
            except Exception:
                db.rollback()
                if copied_path[0] is not None:
                    copied_path[0].unlink(missing_ok=True)
                raise

        print(f"Completed: created={created}, restored={restored}, skipped={skipped}")
        return 0
    finally:
        db.close()


def main() -> int:
    try:
        return import_handbook(_parse_args())
    except Exception as exc:
        print(f"Handbook import failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
