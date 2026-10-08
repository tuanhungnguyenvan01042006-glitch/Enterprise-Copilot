"""
Với SQLAlchemy, Session là 1 khái niệm rất quan trọng,
mỗi lần Request thực hiện Querries thì nó phải tạo 1 phiên Session để giao tiếp vs DB 
file này có vai trò : 
kết nối tới database
tạo database session
cung cấp get_db() cho FastAPI
đóng session sau khi request xong
rollback nếu có lỗi  ( hoạt động giống 1 Transaction )
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)     # Kết nối tới Database
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


# Hàm rất quan trọng :  tạo và quản lý session cho mỗi request.

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()      # tạo session 
    try:
        yield db     # Trả Session cho Route, FastAPI sẽ nhận Session thông qua Depend(get(db))
    except Exception: 
        db.rollback()   # (Giống Transaction) : nếu có lỗi trong quá trình thực hiện querries thì rollback  
        raise 
    finally:
        db.close()    # Đóng DB Connection 

 