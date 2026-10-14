"""CRM tīmekļa slāņa kopīgās daļas: veidnes, mācību režīma darbinieks, tiesības (N3),
piekļuves žurnāls (N2) un servera puses formu validācija."""

from __future__ import annotations

import re
import sqlite3
from datetime import date, datetime
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.templating import Jinja2Templates

from . import schema

TEMPLATES = Jinja2Templates(directory=Path(__file__).parent / "templates")
EMPLOYEE_COOKIE = "crm_darbinieks"

REG_NR_RE = re.compile(r"\d{11}")
PHONE_RE = re.compile(r"(\+371)?\d{8}")
EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def lv_date(value: str | date | None) -> str:
    if not value:
        return ""
    day = value if isinstance(value, date) else date.fromisoformat(value)
    return day.strftime("%d.%m.%Y.")


TEMPLATES.env.filters["lvdate"] = lv_date
TEMPLATES.env.globals.update(
    ROLES=schema.ROLES,
    ORG_TYPES=schema.ORG_TYPES,
    KINDS=schema.KINDS,
    STATUSES=schema.STATUSES,
)


class NeedsEmployee(Exception):
    """Mācību režīmā darbinieks vēl nav izvēlēts: jāpāradresē uz sākumlapu."""


def crm_db(request: Request):
    return request.app.state.crm_db


def today(request: Request) -> date:
    return request.app.state.today()


def current_employee(request: Request) -> sqlite3.Row:
    raw = request.cookies.get(EMPLOYEE_COOKIE, "")
    if raw.isdigit():
        with crm_db(request).connect() as conn:
            employee = conn.execute("SELECT * FROM employees WHERE id = ?", (int(raw),)).fetchone()
        if employee is not None:
            return employee
    raise NeedsEmployee()


def is_manager(employee: sqlite3.Row) -> bool:
    return employee["role"] in ("vaditajs", "administrators")


def is_admin(employee: sqlite3.Row) -> bool:
    return employee["role"] == "administrators"


def can_edit_org(employee: sqlite3.Row, org: sqlite3.Row) -> bool:
    return is_manager(employee) or org["responsible_id"] == employee["id"]


def require(allowed: bool) -> None:
    if not allowed:
        raise HTTPException(403, "Nav tiesību veikt šo darbību")


def get_or_404(conn: sqlite3.Connection, sql: str, *params) -> sqlite3.Row:
    row = conn.execute(sql, params).fetchone()
    if row is None:
        raise HTTPException(404, "Ieraksts nav atrasts")
    return row


def log_access(
    conn: sqlite3.Connection,
    employee_id: int,
    action: str,
    entity: str,
    entity_id: int,
    organization_id: int | None,
) -> None:
    """N2: kas, ko, kad. Bez personas datiem, tikai ieraksta tips un ID."""
    conn.execute(
        "INSERT INTO access_log (at, employee_id, action, entity, entity_id, organization_id)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.now().isoformat(timespec="seconds"), employee_id, action, entity, entity_id,
         organization_id),
    )


def render(request: Request, template: str, context: dict | None = None, status: int = 200):
    context = dict(context or {})
    context.setdefault("employee", None)
    employee = context["employee"]
    context.setdefault("is_manager", bool(employee) and is_manager(employee))
    context.setdefault("is_admin", bool(employee) and is_admin(employee))
    context.setdefault("path", request.url.path)
    context.setdefault("today", today(request))
    return TEMPLATES.TemplateResponse(request, template, context, status_code=status)


class Form:
    """Savāc vērtības un kļūdas; kļūdu secība atbilst lauku secībai formā."""

    def __init__(self, data) -> None:
        self.data = data
        self.values: dict[str, str] = {}
        self.errors: dict[str, str] = {}

    def text(self, name: str, label: str, required: bool = True, max_len: int = 200) -> str:
        value = str(self.data.get(name, "")).strip()
        self.values[name] = value
        if required and not value:
            self.errors[name] = f"Ievadi: {label.lower()}."
        elif len(value) > max_len:
            self.errors[name] = f"{label}: ne vairāk kā {max_len} rakstzīmes."
        return value

    def choice(self, name: str, label: str, options) -> str:
        value = str(self.data.get(name, "")).strip()
        self.values[name] = value
        if value not in options:
            self.errors[name] = f"Izvēlies: {label.lower()}."
        return value

    def date(self, name: str, label: str) -> date | None:
        value = str(self.data.get(name, "")).strip()
        self.values[name] = value
        if not value:
            self.errors[name] = f"Ievadi: {label.lower()}."
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            self.errors[name] = f"{label}: datums formātā GGGG-MM-DD."
            return None

    def pattern(self, name: str, label: str, regex: re.Pattern, message: str) -> str:
        value = self.text(name, label)
        if value and name not in self.errors and not regex.fullmatch(value):
            self.errors[name] = message
        return value

    def error(self, name: str, message: str) -> None:
        self.errors.setdefault(name, message)

    @property
    def ok(self) -> bool:
        return not self.errors
