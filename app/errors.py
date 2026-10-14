"""Kļūdu atbildes pēc līguma kopīgās `Error` shēmas."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.errors")

Detail = tuple[str, str]


class ApiError(Exception):
    def __init__(
        self, status: int, code: str, message: str, details: list[Detail] | None = None
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details or []


def validation_error(details: list[Detail]) -> ApiError:
    return ApiError(400, "VALIDATION_ERROR", "Request validation failed", details)


def error_response(status: int, code: str, message: str, details: list[Detail] | None = None):
    error: dict = {"code": code, "message": message}
    if details:
        error["details"] = [{"field": field, "issue": issue} for field, issue in details]
    return JSONResponse(status_code=status, content={"error": error})


def _field_name(loc: tuple) -> str:
    parts = [str(part) for part in loc[1:] if isinstance(part, str)]
    return ".".join(parts) or "body"


async def _api_error(_: Request, exc: ApiError):
    return error_response(exc.status, exc.code, exc.message, exc.details)


async def _request_validation_error(_: Request, exc: RequestValidationError):
    # Ievades vērtības (piem., paroles) atbildē neatkārto, tikai lauku un problēmu.
    details = [
        (_field_name(err["loc"]), "REQUIRED" if err["type"] == "missing" else "INVALID_FORMAT")
        for err in exc.errors()
    ]
    return error_response(400, "VALIDATION_ERROR", "Request validation failed", details)


def wants_html(request: Request) -> bool:
    """CR-5: pārlūks saņem HTML kļūdu lapu, citi klienti JSON `Error` (sk. līgumu)."""
    return "text/html" in request.headers.get("accept", "")


def _html_error(request: Request, status: int, message: str):
    from .crm.web import render  # CRM veidnes ielādē tikai HTML atbildēm

    return render(request, "error.html", {"status": status, "message": message}, status=status)


HTTP_CODES = {400: "VALIDATION_ERROR", 403: "FORBIDDEN", 404: "NOT_FOUND",
              405: "METHOD_NOT_ALLOWED"}


async def _http_error(request: Request, exc: StarletteHTTPException):
    message = exc.detail if isinstance(exc.detail, str) else "HTTP error"
    if wants_html(request):
        return _html_error(request, exc.status_code, message)
    return error_response(exc.status_code, HTTP_CODES.get(exc.status_code, "HTTP_ERROR"), message)


async def _needs_employee(_: Request, __: Exception):
    return RedirectResponse("/sakums", status_code=303)


async def _server_error(request: Request, exc: Exception):
    logger.error("Neapstrādāta kļūda: %s", type(exc).__name__)
    if wants_html(request):
        return _html_error(request, 500, "Servera kļūda. Mēģini vēlreiz vēlāk.")
    return error_response(500, "INTERNAL_ERROR", "Internal server error")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, _api_error)
    app.add_exception_handler(RequestValidationError, _request_validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    from .crm.web import NeedsEmployee

    app.add_exception_handler(NeedsEmployee, _needs_employee)
    app.add_exception_handler(Exception, _server_error)
