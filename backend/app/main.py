""" Vai trò của file : 1. Tạo ứng dụng FastAPI  2. Gắn tính năng chung cho mọi request 
3. Đăng kí API route
"""
# Đây là nơi mọi request đi vào, mọi response đi ra, nên có thể gắn các middleware, exception handler, CORS, ... vào đây
import uuid # tạo id ngẫu nhiên 
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import admin, announcements, auth, dashboard, department, documents, health, profile, workspace
from app.core.config import get_settings
from app.core.errors import http_exception_handler, validation_exception_handler

# lý do cần Middleware: là do 1 Request đi vào 1 Controller nào đó, thì request luôn cần phải được xử lý thông tin trước : thêm id request,... 
# mà đây là nơi mọi request đi vào, mọi response đi ra, nên có thể gắn các middleware, exception handler, CORS, ... vào đây
# Nhưng tại sao không tạo riêng 1 folder middelware ? Có lẽ sau này sẽ cần folder, file middleware cho riêng từng module, nhưng hiện tại thì chưa cần, nên cứ để đây cho tiện,vì dù sao bất kể modul j thì cũng cần request id.


# vai trò của hàm này Middleware gắn RequestId để định danh cho request,request đi vào controller nào đó thì controller có thể lấy ra request id này để log, debug, trace,...
class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response
    
 

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0") # Setting được sử dụng như 1 class lưu, chuẩn hóa các biến environment
# Sau khi khởi tạo App, ta đăng kí middleware, router, exception handler, CORS, ... vào app
app.add_middleware(RequestIdMiddleware)
app.add_middleware( 
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-ID", "X-CSRF-Token"],
)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(profile.router, prefix="/api/v1")
app.include_router(workspace.router, prefix="/api/v1")
app.include_router(department.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(announcements.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")


@app.get("/")
def root() -> dict[str, str]:
    return {"name": settings.app_name, "status": "ok"}
