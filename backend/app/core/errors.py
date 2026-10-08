from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def api_error(status_code: int, code: str, message: str, details: object | None = None) -> StarletteHTTPException:
    return StarletteHTTPException(
        status_code=status_code,
        detail={"code": code, "message": message, "details": details},
    )


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and {"code", "message"} <= exc.detail.keys():
        error = {
            "code": exc.detail["code"],
            "message": exc.detail["message"],
            "details": exc.detail.get("details"),
        }
    else:
        error = {"code": "HTTP_ERROR", "message": str(exc.detail), "details": None}
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": error,
            "request_id": _request_id(request),
        },
        headers=exc.headers,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {"code": "VALIDATION_ERROR", "message": "Request validation failed", "details": exc.errors()},
            "request_id": _request_id(request),
        },
    )
