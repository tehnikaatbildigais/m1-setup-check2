"""CR-4 · reģistrācija, pieteikšanās, iziešana un paroles atjaunošana."""

from __future__ import annotations

import logging
import re
import sqlite3

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .errors import ApiError, Detail, validation_error
from .security import DUMMY_HASH, hash_password, new_token, token_hash, verify_password

logger = logging.getLogger("app.auth")

router = APIRouter(prefix="/auth", tags=["Lietotāji"])

SESSION_COOKIE = "session"
MIN_PASSWORD_LENGTH = 8
MAX_FAILED_ATTEMPTS = 3
LOCK_SECONDS = 5 * 60
RESET_TOKEN_SECONDS = 30 * 60

EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")

INVALID_CREDENTIALS = ApiError(401, "INVALID_CREDENTIALS", "Invalid login or password")


class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str
    passwordConfirm: str


class LoginRequest(BaseModel):
    login: str
    password: str


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    token: str
    password: str
    passwordConfirm: str


def _check_email(email: str, details: list[Detail]) -> None:
    if not email.strip():
        details.append(("email", "REQUIRED"))
    elif not EMAIL_RE.fullmatch(email):
        details.append(("email", "INVALID_FORMAT"))


def _check_password(password: str, confirm: str, details: list[Detail]) -> None:
    if not password:
        details.append(("password", "REQUIRED"))
    elif len(password) < MIN_PASSWORD_LENGTH:
        details.append(("password", "TOO_SHORT"))
    if password and confirm != password:
        details.append(("passwordConfirm", "MISMATCH"))


def session_user(request: Request) -> sqlite3.Row | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    with request.app.state.db.connect() as conn:
        return conn.execute(
            "SELECT users.id, users.username FROM sessions"
            " JOIN users ON users.id = sessions.user_id WHERE sessions.token_hash = ?",
            (token_hash(token),),
        ).fetchone()


@router.post("/register", status_code=201)
def register(body: RegisterRequest, request: Request) -> dict:
    details: list[Detail] = []
    _check_email(body.email, details)
    if not body.username.strip():
        details.append(("username", "REQUIRED"))
    elif "@" in body.username:
        details.append(("username", "INVALID_FORMAT"))
    _check_password(body.password, body.passwordConfirm, details)
    if details:
        raise validation_error(details)

    password_hash = hash_password(body.password)
    db, now = request.app.state.db, request.app.state.clock()
    conflicts: list[Detail] = []
    with db.transaction() as conn:
        if conn.execute("SELECT 1 FROM users WHERE email = ?", (body.email,)).fetchone():
            conflicts.append(("email", "ALREADY_EXISTS"))
        if conn.execute("SELECT 1 FROM users WHERE username = ?", (body.username,)).fetchone():
            conflicts.append(("username", "ALREADY_EXISTS"))
        if not conflicts:
            conn.execute(
                "INSERT INTO users (email, username, password_hash, created_at)"
                " VALUES (?, ?, ?, ?)",
                (body.email, body.username, password_hash, now),
            )
    if conflicts:
        raise ApiError(409, "CONFLICT", "User already exists", conflicts)
    return {"email": body.email, "username": body.username}


@router.post("/login")
def login(body: LoginRequest, request: Request, response: Response) -> dict:
    details: list[Detail] = []
    if not body.login.strip():
        details.append(("login", "REQUIRED"))
    if not body.password:
        details.append(("password", "REQUIRED"))
    if details:
        raise validation_error(details)

    db, now = request.app.state.db, request.app.state.clock()
    # Lietotājvārds nedrīkst saturēt `@`, tāpēc ievade ar `@` vienmēr ir e-pasts.
    column = "email" if "@" in body.login else "username"
    with db.connect() as conn:
        user = conn.execute(
            f"SELECT id, username, password_hash, locked_until FROM users WHERE {column} = ?",
            (body.login,),
        ).fetchone()
    if user is None:
        verify_password(body.password, DUMMY_HASH)
        raise INVALID_CREDENTIALS

    password_ok = verify_password(body.password, user["password_hash"])
    locked = user["locked_until"] is not None and user["locked_until"] > now
    session_token = new_token()
    with db.transaction() as conn:
        if locked:
            pass  # Bloķēšanas laikā mēģinājumi netiek skaitīti un bloķēšana netiek pagarināta.
        elif not password_ok:
            conn.execute(
                "UPDATE users SET failed_attempts = failed_attempts + 1 WHERE id = ?",
                (user["id"],),
            )
            conn.execute(
                "UPDATE users SET failed_attempts = 0, locked_until = ?"
                " WHERE id = ? AND failed_attempts >= ?",
                (now + LOCK_SECONDS, user["id"], MAX_FAILED_ATTEMPTS),
            )
        else:
            conn.execute(
                "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = ?",
                (user["id"],),
            )
            conn.execute(
                "INSERT INTO sessions (token_hash, user_id, created_at) VALUES (?, ?, ?)",
                (token_hash(session_token), user["id"], now),
            )
    if locked or not password_ok:
        raise INVALID_CREDENTIALS

    response.set_cookie(SESSION_COOKIE, session_token, httponly=True, samesite="lax", path="/")
    return {"username": user["username"]}


@router.post("/logout", status_code=204)
def logout(request: Request) -> Response:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        with request.app.state.db.connect() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash(token),))
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax")
    return response


@router.post("/password-reset", status_code=202)
def request_password_reset(body: PasswordResetRequest, request: Request) -> JSONResponse:
    details: list[Detail] = []
    _check_email(body.email, details)
    if details:
        raise validation_error(details)

    db, now = request.app.state.db, request.app.state.clock()
    with db.connect() as conn:
        user = conn.execute("SELECT id FROM users WHERE email = ?", (body.email,)).fetchone()
        if user is not None:
            token = new_token()
            conn.execute(
                "INSERT INTO password_resets (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                (token_hash(token), user["id"], now + RESET_TOKEN_SECONDS),
            )
            link = f"{str(request.base_url).rstrip('/')}/password-reset/confirm?token={token}"
            # Tikai lokālajam prototipam: e-pasts netiek sūtīts (CR-4 komentāri).
            logger.info("Paroles atjaunošanas saite lietotājam %s: %s", body.email, link)
    # Vienāda atbilde neatkarīgi no tā, vai e-pasts ir reģistrēts.
    return JSONResponse(
        status_code=202,
        content={"message": "If the e-mail is registered, a reset link has been issued"},
    )


@router.post("/password-reset/confirm")
def confirm_password_reset(body: PasswordResetConfirm, request: Request) -> dict:
    details: list[Detail] = []
    _check_password(body.password, body.passwordConfirm, details)
    if details:
        raise validation_error(details)

    password_hash = hash_password(body.password)
    db, now = request.app.state.db, request.app.state.clock()
    with db.transaction() as conn:
        reset = conn.execute(
            "SELECT user_id FROM password_resets"
            " WHERE token_hash = ? AND used_at IS NULL AND expires_at > ?",
            (token_hash(body.token), now),
        ).fetchone()
        if reset is not None:
            user_id = reset["user_id"]
            conn.execute(
                "UPDATE password_resets SET used_at = ? WHERE user_id = ? AND used_at IS NULL",
                (now, user_id),
            )
            conn.execute(
                "UPDATE users SET password_hash = ?, failed_attempts = 0, locked_until = NULL"
                " WHERE id = ?",
                (password_hash, user_id),
            )
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    if reset is None:
        raise validation_error([("token", "INVALID_OR_EXPIRED")])
    return {"message": "Password has been changed"}
