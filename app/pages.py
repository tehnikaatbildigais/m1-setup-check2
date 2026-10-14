"""CR-4 · HTML lapas. Nav API līguma daļa (sk. CR-4 komentārus)."""

from __future__ import annotations

import html
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from .auth import session_user

STATIC_DIR = Path(__file__).parent / "static"
WELCOME_TEMPLATE = (STATIC_DIR / "welcome.html").read_text(encoding="utf-8")

router = APIRouter(include_in_schema=False)


def _page(name: str) -> FileResponse:
    return FileResponse(STATIC_DIR / name, media_type="text/html")


@router.get("/")
def index() -> RedirectResponse:
    # CR-5: galvenā lietotne ir CRM; CR-4 lapas paliek pieejamas pēc sava ceļa.
    return RedirectResponse("/sakums", status_code=303)


@router.get("/login")
def login_page() -> FileResponse:
    return _page("login.html")


@router.get("/register")
def register_page() -> FileResponse:
    return _page("register.html")


@router.get("/password-reset")
def password_reset_page() -> FileResponse:
    return _page("password-reset.html")


@router.get("/password-reset/confirm")
def password_reset_confirm_page() -> FileResponse:
    return _page("password-reset-confirm.html")


@router.get("/welcome", response_model=None)
def welcome_page(request: Request) -> HTMLResponse | RedirectResponse:
    user = session_user(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    body = WELCOME_TEMPLATE.replace("{{username}}", html.escape(user["username"]))
    return HTMLResponse(body, headers={"Cache-Control": "no-store"})
