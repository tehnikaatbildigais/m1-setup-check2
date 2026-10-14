"""CR-4 pieņemšanas kritēriji. Numuri komentāros atbilst tracker/CR-4.md tabulai."""

from __future__ import annotations

import logging
import re
import sqlite3
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from app.application import create_app
from tools.lint_contract import course_rule_errors

ROOT = Path(__file__).resolve().parents[1]
PASSWORD = "ezera-iela-12"
NEW_PASSWORD = "jauna-parole-34"


class FakeClock:
    def __init__(self) -> None:
        self.now = 1_800_000_000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "users.db"


@pytest.fixture
def client(db_path: Path, clock: FakeClock):
    with TestClient(create_app(db_path, clock=clock)) as test_client:
        yield test_client


def register(client, email="janis@example.com", username="janis", password=PASSWORD, confirm=None):
    return client.post(
        "/auth/register",
        json={
            "email": email,
            "username": username,
            "password": password,
            "passwordConfirm": password if confirm is None else confirm,
        },
    )


def login(client, login_value="janis", password=PASSWORD):
    return client.post("/auth/login", json={"login": login_value, "password": password})


def details(response) -> list[tuple[str, str]]:
    return [(d["field"], d["issue"]) for d in response.json()["error"]["details"]]


def request_reset_token(client, caplog, email="janis@example.com") -> str:
    with caplog.at_level(logging.INFO, logger="app.auth"):
        assert client.post("/auth/password-reset", json={"email": email}).status_code == 202
    match = re.search(r"/password-reset/confirm\?token=(\S+)", caplog.text)
    assert match, "žurnālā nav atjaunošanas saites"
    return match.group(1)


# 1
def test_register_creates_account(client) -> None:
    response = register(client)
    assert response.status_code == 201
    assert response.json() == {"email": "janis@example.com", "username": "janis"}


# 2
def test_register_rejects_short_password(client) -> None:
    response = register(client, password="1234567")
    assert response.status_code == 400
    assert ("password", "TOO_SHORT") in details(response)


def test_register_accepts_exactly_eight_characters(client) -> None:
    assert register(client, password="12345678").status_code == 201


# 3
def test_register_rejects_mismatched_confirmation(client) -> None:
    response = register(client, confirm=PASSWORD + "x")
    assert response.status_code == 400
    assert details(response) == [("passwordConfirm", "MISMATCH")]


# 4
def test_register_rejects_duplicate_email(client) -> None:
    register(client)
    response = register(client, username="cits")
    assert response.status_code == 409
    assert details(response) == [("email", "ALREADY_EXISTS")]


# 5
def test_register_rejects_duplicate_username(client) -> None:
    register(client)
    response = register(client, email="cits@example.com")
    assert response.status_code == 409
    assert details(response) == [("username", "ALREADY_EXISTS")]


def test_email_and_username_are_case_sensitive(client) -> None:
    assert register(client).status_code == 201
    assert register(client, email="Janis@example.com", username="Janis").status_code == 201
    assert login(client, "JANIS").status_code == 401


# 6
def test_register_rejects_invalid_email(client) -> None:
    response = register(client, email="janis@")
    assert response.status_code == 400
    assert details(response) == [("email", "INVALID_FORMAT")]


# 7
@pytest.mark.parametrize("username", ["", "   "])
def test_register_rejects_blank_username(client, username) -> None:
    response = register(client, username=username)
    assert response.status_code == 400
    assert details(response) == [("username", "REQUIRED")]


def test_register_rejects_at_sign_in_username(client) -> None:
    response = register(client, username="ja@nis")
    assert response.status_code == 400
    assert details(response) == [("username", "INVALID_FORMAT")]


@pytest.mark.parametrize("username", ["Jānis Bērziņš", "<b>x</b>", "😀_1.-"])
def test_register_accepts_any_other_symbols(client, username) -> None:
    assert register(client, username=username).status_code == 201


def test_register_missing_field_uses_error_schema(client) -> None:
    response = client.post("/auth/register", json={"email": "janis@example.com"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert ("password", "REQUIRED") in details(response)


# 8, 9
@pytest.mark.parametrize("login_value", ["janis@example.com", "janis"])
def test_login_with_email_or_username(client, login_value) -> None:
    register(client)
    response = login(client, login_value)
    assert response.status_code == 200
    assert response.json() == {"username": "janis"}
    set_cookie = response.headers["set-cookie"]
    assert "session=" in set_cookie and "HttpOnly" in set_cookie

    page = client.get("/welcome")
    assert page.status_code == 200
    assert "Sveiks, janis!" in page.text


# 10
def test_wrong_password_and_unknown_user_look_the_same(client) -> None:
    register(client)
    wrong_password = login(client, password="nepareiza-parole")
    unknown_user = login(client, "neviens")
    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json()
    assert "set-cookie" not in wrong_password.headers


# 11, 12
def test_three_failures_lock_account_for_five_minutes(client, clock) -> None:
    register(client)
    reference = login(client, password="nepareiza-1")
    login(client, password="nepareiza-2")
    login(client, password="nepareiza-3")

    locked = login(client)
    assert locked.status_code == 401
    assert locked.json() == reference.json()

    clock.advance(299)
    assert login(client).status_code == 401

    clock.advance(1)
    assert login(client).status_code == 200


def test_counter_is_reset_after_lock_expires(client, clock) -> None:
    register(client)
    for _ in range(3):
        login(client, password="nepareiza")
    clock.advance(300)
    login(client, password="nepareiza")
    login(client, password="nepareiza")
    assert login(client).status_code == 200


def test_attempts_during_lock_do_not_extend_it(client, clock) -> None:
    register(client)
    for _ in range(3):
        login(client, password="nepareiza")
    clock.advance(200)
    for _ in range(3):
        login(client, password="nepareiza")
    clock.advance(100)
    assert login(client).status_code == 200


# 13
def test_successful_login_resets_counter(client) -> None:
    register(client)
    login(client, password="nepareiza")
    login(client, password="nepareiza")
    assert login(client).status_code == 200
    login(client, password="nepareiza")
    login(client, password="nepareiza")
    assert login(client).status_code == 200


# 14
def test_logout_ends_session(client) -> None:
    register(client)
    login(client)
    assert client.get("/welcome").status_code == 200

    assert client.post("/auth/logout").status_code == 204
    response = client.get("/welcome", follow_redirects=False)
    assert response.status_code == 303


def test_logout_without_session_is_noop(client) -> None:
    assert client.post("/auth/logout").status_code == 204


def test_old_session_cookie_is_invalid_after_logout(client) -> None:
    register(client)
    login(client)
    token = client.cookies.get("session")
    client.post("/auth/logout")
    client.cookies.set("session", token)
    assert client.get("/welcome", follow_redirects=False).status_code == 303


# 15
def test_welcome_requires_login(client) -> None:
    response = client.get("/welcome", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_welcome_escapes_username(client) -> None:
    register(client, username="<script>alert(1)</script>")
    login(client, "janis@example.com")
    page = client.get("/welcome")
    assert "<script>alert(1)</script>" not in page.text
    assert "&lt;script&gt;" in page.text


# 16
def test_reset_link_for_registered_email_is_logged(client, caplog) -> None:
    register(client)
    token = request_reset_token(client, caplog)
    assert len(token) >= 32


# 17
def test_reset_for_unknown_email_has_same_response_and_no_link(client, caplog) -> None:
    register(client)
    known = client.post("/auth/password-reset", json={"email": "janis@example.com"})
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="app.auth"):
        unknown = client.post("/auth/password-reset", json={"email": "neviens@example.com"})
    assert unknown.status_code == known.status_code == 202
    assert unknown.json() == known.json()
    assert "token=" not in caplog.text


def test_reset_rejects_invalid_email(client) -> None:
    response = client.post("/auth/password-reset", json={"email": "janis@"})
    assert response.status_code == 400


# 18
def test_reset_changes_password_and_token_is_single_use(client, caplog) -> None:
    register(client)
    token = request_reset_token(client, caplog)
    body = {"token": token, "password": NEW_PASSWORD, "passwordConfirm": NEW_PASSWORD}

    assert client.post("/auth/password-reset/confirm", json=body).status_code == 200
    assert login(client, password=PASSWORD).status_code == 401
    assert login(client, password=NEW_PASSWORD).status_code == 200

    reused = client.post("/auth/password-reset/confirm", json=body)
    assert reused.status_code == 400
    assert details(reused) == [("token", "INVALID_OR_EXPIRED")]


def test_reset_removes_lock(client, caplog) -> None:
    register(client)
    for _ in range(3):
        login(client, password="nepareiza")
    token = request_reset_token(client, caplog)
    client.post(
        "/auth/password-reset/confirm",
        json={"token": token, "password": NEW_PASSWORD, "passwordConfirm": NEW_PASSWORD},
    )
    assert login(client, password=NEW_PASSWORD).status_code == 200


def test_reset_ends_existing_sessions(client, caplog) -> None:
    register(client)
    login(client)
    token = request_reset_token(client, caplog)
    client.post(
        "/auth/password-reset/confirm",
        json={"token": token, "password": NEW_PASSWORD, "passwordConfirm": NEW_PASSWORD},
    )
    assert client.get("/welcome", follow_redirects=False).status_code == 303


def test_reset_validates_new_password(client, caplog) -> None:
    register(client)
    token = request_reset_token(client, caplog)
    response = client.post(
        "/auth/password-reset/confirm",
        json={"token": token, "password": "short", "passwordConfirm": "short"},
    )
    assert response.status_code == 400
    assert details(response) == [("password", "TOO_SHORT")]


# 19
def test_expired_reset_token_is_rejected(client, caplog, clock) -> None:
    register(client)
    token = request_reset_token(client, caplog)
    clock.advance(30 * 60)
    response = client.post(
        "/auth/password-reset/confirm",
        json={"token": token, "password": NEW_PASSWORD, "passwordConfirm": NEW_PASSWORD},
    )
    assert response.status_code == 400
    assert details(response) == [("token", "INVALID_OR_EXPIRED")]


def test_unknown_reset_token_is_rejected(client) -> None:
    response = client.post(
        "/auth/password-reset/confirm",
        json={"token": "nav-tāda", "password": NEW_PASSWORD, "passwordConfirm": NEW_PASSWORD},
    )
    assert response.status_code == 400


# 20
def test_passwords_are_not_stored_in_plain_text(client, db_path) -> None:
    register(client)
    with sqlite3.connect(db_path) as conn:
        (stored,) = conn.execute("SELECT password_hash FROM users").fetchone()
    assert stored.startswith("scrypt$")
    assert PASSWORD not in stored
    assert PASSWORD.encode() not in db_path.read_bytes()


# 21
def test_logs_contain_no_passwords(client, caplog) -> None:
    with caplog.at_level(logging.DEBUG):
        register(client)
        login(client, password="nepareiza-parole")
        login(client)
        token = request_reset_token(client, caplog)
        client.post(
            "/auth/password-reset/confirm",
            json={"token": token, "password": NEW_PASSWORD, "passwordConfirm": NEW_PASSWORD},
        )
        client.post("/auth/password-reset", json={"email": "neviens@example.com"})
    for secret in (PASSWORD, NEW_PASSWORD, "nepareiza-parole"):
        assert secret not in caplog.text
    assert "neviens@example.com" not in caplog.text
    emails_logged = [r for r in caplog.records if "janis@example.com" in r.getMessage()]
    assert all("token=" in r.getMessage() for r in emails_logged)


def test_validation_errors_do_not_echo_input(client) -> None:
    response = client.post("/auth/login", json={"login": "janis", "password": 12345678})
    assert response.status_code == 400
    assert "12345678" not in response.text


# 22
def test_users_survive_restart(db_path, clock) -> None:
    with TestClient(create_app(db_path, clock=clock)) as first:
        register(first)
    with TestClient(create_app(db_path, clock=clock)) as second:
        assert login(second).status_code == 200


# 23
def test_auth_operations_follow_course_contract_rules() -> None:
    with (ROOT / "docs" / "openapi.yaml").open(encoding="utf-8") as stream:
        document = yaml.safe_load(stream)
    auth_paths = [path for path in document["paths"] if path.startswith("/auth/")]
    assert set(auth_paths) == {
        "/auth/register",
        "/auth/login",
        "/auth/logout",
        "/auth/password-reset",
        "/auth/password-reset/confirm",
    }
    errors = [e for e in course_rule_errors(document) if " /auth/" in e]
    assert errors == []


def test_unknown_route_uses_error_schema(client) -> None:
    response = client.post("/auth/nav")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize(
    "path", ["/login", "/register", "/password-reset", "/password-reset/confirm"]
)
def test_html_pages_are_served(client, path) -> None:
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_login_and_register_pages_link_to_each_other(client) -> None:
    assert 'href="/register"' in client.get("/login").text
    assert 'href="/login"' in client.get("/register").text


# --- Audits 2026-10-14 ----------------------------------------------------------------

def test_parallel_wrong_passwords_cannot_bypass_lockout(client) -> None:
    from concurrent.futures import ThreadPoolExecutor

    register(client)
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda i: login(client, password=f"nepareiza-{i}").status_code,
                                range(6)))
    assert results == [401] * 6
    # Neatkarīgi no secības konts ir bloķēts: arī pareizā parole atgriež 401.
    assert login(client).status_code == 401


def test_reset_link_ignores_host_header(client, caplog) -> None:
    import app.auth as auth_module

    register(client)
    with caplog.at_level(logging.INFO, logger="app.auth"):
        client.post("/auth/password-reset", json={"email": "janis@example.com"},
                    headers={"host": "evil.example"})
    assert "evil.example" not in caplog.text
    assert f"{auth_module.PUBLIC_BASE_URL}/password-reset/confirm?token=" in caplog.text


def test_overlong_password_is_rejected_without_hashing(client, monkeypatch) -> None:
    import app.auth as auth_module

    def no_hash(*_):
        raise AssertionError("scrypt nedrīkst izsaukt")

    register(client)  # esošs lietotājs „janis”, lai pārbaudītu arī šo pieteikšanās zaru
    long_password = "x" * 1025
    monkeypatch.setattr(auth_module, "hash_password", no_hash)
    monkeypatch.setattr(auth_module, "verify_password", no_hash)
    response = register(client, email="cits@example.com", username="cits", password=long_password)
    assert response.status_code == 400
    assert details(response) == [("password", "TOO_LONG")]
    assert login(client, "janis", password=long_password).status_code == 401
    assert login(client, "neviens", password=long_password).status_code == 401
    confirm = client.post("/auth/password-reset/confirm",
                          json={"token": "nav", "password": NEW_PASSWORD, "passwordConfirm": NEW_PASSWORD})
    assert confirm.status_code == 400  # nederīgs marķieris noraidīts pirms jaukšanas


def test_login_attempts_are_serialized(client, monkeypatch) -> None:
    """Deterministiski: ja paroles pārbaude notiktu ārpus rakstīšanas transakcijas,
    divi paralēli mēģinājumi pārklātos (lēnā pārbaude to garantē)."""
    import threading
    import time
    from concurrent.futures import ThreadPoolExecutor

    import app.auth as auth_module

    register(client)
    real_verify = auth_module.verify_password
    active, peak, lock = 0, 0, threading.Lock()

    def slow_verify(password, stored):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.2)
        try:
            return real_verify(password, stored)
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(auth_module, "verify_password", slow_verify)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda i: login(client, password=f"nepareiza-{i}"), range(4)))
    assert peak == 1


def test_invalid_credentials_error_is_not_shared() -> None:
    from app.auth import invalid_credentials

    assert invalid_credentials() is not invalid_credentials()
