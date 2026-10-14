"""F1 organizācijas, F2 kontaktpersonas, F3 mijiedarbības ar MI-1, N2 dzēšana."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from . import ai, schema
from .web import (
    EMAIL_RE, PHONE_RE, REG_NR_RE, Form, can_edit_org, crm_db, current_employee, get_or_404,
    is_admin, log_access, render, require, today,
)

router = APIRouter(include_in_schema=False)

ANONYMOUS = "Dzēsta kontaktpersona"


def _see_other(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)


def _employees(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM employees ORDER BY name").fetchall()


# --- F1 · organizācijas ---------------------------------------------------------------

@router.get("/organizacijas")
def org_list(request: Request, mans: str = ""):
    employee = current_employee(request)
    with crm_db(request).connect() as conn:
        orgs = conn.execute(
            "SELECT o.*, e.name AS responsible FROM organizations o"
            " JOIN employees e ON e.id = o.responsible_id ORDER BY o.name"
        ).fetchall()
    if mans:
        orgs = [o for o in orgs if o["responsible_id"] == employee["id"]]
    return render(request, "org_list.html", {"employee": employee, "orgs": orgs, "mans": bool(mans)})


def _org_form(form: Form, conn: sqlite3.Connection, org_id: int | None) -> None:
    form.text("name", "Nosaukums")
    reg_nr = form.pattern(
        "reg_nr", "Reģistrācijas numurs", REG_NR_RE,
        "Reģistrācijas numuram jābūt 11 cipariem, piemēram, 40003012345.",
    )
    form.choice("type", "Veids", schema.ORG_TYPES)
    responsible = form.text("responsible_id", "Atbildīgais darbinieks")
    if responsible and not (
        responsible.isdigit()
        and conn.execute("SELECT 1 FROM employees WHERE id = ?", (int(responsible),)).fetchone()
    ):
        form.error("responsible_id", "Izvēlies atbildīgo darbinieku no saraksta.")
    if "reg_nr" not in form.errors:
        duplicate = conn.execute(
            "SELECT id FROM organizations WHERE reg_nr = ? AND id IS NOT ?", (reg_nr, org_id)
        ).fetchone()
        if duplicate:
            form.error("reg_nr", "Organizācija ar šo reģ. nr. jau ir reģistrēta.")


@router.get("/organizacijas/jauna")
def org_new(request: Request):
    employee = current_employee(request)
    with crm_db(request).connect() as conn:
        employees = _employees(conn)
    values = {"responsible_id": str(employee["id"])}
    return render(request, "org_form.html", {
        "employee": employee, "employees": employees, "values": values, "errors": {},
        "org": None,
    })


@router.post("/organizacijas/jauna")
async def org_create(request: Request):
    employee = current_employee(request)
    form = Form(await request.form())
    with crm_db(request).transaction() as conn:
        _org_form(form, conn, None)
        if form.ok:
            v = form.values
            org_id = conn.execute(
                "INSERT INTO organizations (name, reg_nr, type, responsible_id) VALUES (?, ?, ?, ?)",
                (v["name"], v["reg_nr"], v["type"], int(v["responsible_id"])),
            ).lastrowid
            log_access(conn, employee["id"], "izveidoja", "organizācija", org_id, org_id)
        employees = _employees(conn)
    if form.ok:
        return _see_other(f"/organizacijas/{org_id}")
    return render(request, "org_form.html", {
        "employee": employee, "employees": employees, "values": form.values,
        "errors": form.errors, "org": None,
    }, status=400)


@router.get("/organizacijas/{org_id}")
def org_detail(request: Request, org_id: int):
    employee = current_employee(request)
    with crm_db(request).transaction() as conn:
        org = get_or_404(conn, "SELECT o.*, e.name AS responsible FROM organizations o"
                         " JOIN employees e ON e.id = o.responsible_id WHERE o.id = ?", org_id)
        contacts = conn.execute(
            "SELECT * FROM contacts WHERE organization_id = ? ORDER BY name", (org_id,)
        ).fetchall()
        interactions = conn.execute(
            "SELECT i.*, a.name AS author, p.name AS approver FROM interactions i"
            " JOIN employees a ON a.id = i.author_id"
            " LEFT JOIN employees p ON p.id = i.approved_by"
            " WHERE i.organization_id = ? ORDER BY i.date DESC, i.id DESC", (org_id,)
        ).fetchall()
        participants: dict[int, list[str]] = {}
        for row in conn.execute(
            "SELECT ip.interaction_id, c.name FROM interaction_participants ip"
            " JOIN interactions i ON i.id = ip.interaction_id"
            " LEFT JOIN contacts c ON c.id = ip.contact_id WHERE i.organization_id = ?",
            (org_id,),
        ):
            participants.setdefault(row["interaction_id"], []).append(row["name"] or ANONYMOUS)
        requests = conn.execute(
            "SELECT * FROM requests WHERE organization_id = ? ORDER BY created_on DESC", (org_id,)
        ).fetchall()
        tasks = conn.execute(
            "SELECT t.*, e.name AS assignee FROM tasks t JOIN employees e ON e.id = t.assignee_id"
            " WHERE t.organization_id = ? AND t.done_on IS NULL ORDER BY t.due", (org_id,)
        ).fetchall()
        log_access(conn, employee["id"], "skatīja", "organizācija", org_id, org_id)
    return render(request, "org_detail.html", {
        "employee": employee, "org": org, "contacts": contacts, "interactions": interactions,
        "participants": participants, "requests": requests, "tasks": tasks,
        "can_edit": can_edit_org(employee, org),
    })


@router.get("/organizacijas/{org_id}/labot")
def org_edit(request: Request, org_id: int):
    employee = current_employee(request)
    with crm_db(request).connect() as conn:
        org = get_or_404(conn, "SELECT * FROM organizations WHERE id = ?", org_id)
        require(can_edit_org(employee, org))
        employees = _employees(conn)
    values = {k: str(org[k]) for k in ("name", "reg_nr", "type", "responsible_id")}
    return render(request, "org_form.html", {
        "employee": employee, "employees": employees, "values": values, "errors": {}, "org": org,
    })


@router.post("/organizacijas/{org_id}/labot")
async def org_update(request: Request, org_id: int):
    employee = current_employee(request)
    form = Form(await request.form())
    with crm_db(request).transaction() as conn:
        org = get_or_404(conn, "SELECT * FROM organizations WHERE id = ?", org_id)
        require(can_edit_org(employee, org))
        _org_form(form, conn, org_id)
        if form.ok:
            v = form.values
            conn.execute(
                "UPDATE organizations SET name = ?, reg_nr = ?, type = ?, responsible_id = ?"
                " WHERE id = ?",
                (v["name"], v["reg_nr"], v["type"], int(v["responsible_id"]), org_id),
            )
            log_access(conn, employee["id"], "mainīja", "organizācija", org_id, org_id)
        employees = _employees(conn)
    if form.ok:
        return _see_other(f"/organizacijas/{org_id}")
    return render(request, "org_form.html", {
        "employee": employee, "employees": employees, "values": form.values,
        "errors": form.errors, "org": org,
    }, status=400)


# --- F2 · kontaktpersonas --------------------------------------------------------------

def _contact_form(form: Form) -> None:
    form.text("name", "Vārds, uzvārds")
    form.text("position", "Amats")
    form.pattern("email", "E-pasts", EMAIL_RE, "Ievadi derīgu e-pastu, piemēram, vards@example.com.")
    form.pattern(
        "phone", "Tālrunis", PHONE_RE,
        "Tālrunim jābūt 8 cipariem, var sākt ar +371, piemēram, +37120000000.",
    )
    form.choice("basis", "Saziņas pamats", schema.BASES)
    form.date("basis_date", "Saziņas pamata datums")


def _editable_org(conn, employee, org_id: int) -> sqlite3.Row:
    org = get_or_404(conn, "SELECT * FROM organizations WHERE id = ?", org_id)
    require(can_edit_org(employee, org))
    return org


@router.get("/organizacijas/{org_id}/kontakti/jauns")
def contact_new(request: Request, org_id: int):
    employee = current_employee(request)
    with crm_db(request).connect() as conn:
        org = _editable_org(conn, employee, org_id)
    return render(request, "contact_form.html", {
        "employee": employee, "org": org, "contact": None, "errors": {},
        "values": {"basis_date": today(request).isoformat()}, "bases": schema.BASES,
    })


@router.post("/organizacijas/{org_id}/kontakti/jauns")
async def contact_create(request: Request, org_id: int):
    employee = current_employee(request)
    form = Form(await request.form())
    _contact_form(form)
    with crm_db(request).transaction() as conn:
        org = _editable_org(conn, employee, org_id)
        if form.ok:
            v = form.values
            contact_id = conn.execute(
                "INSERT INTO contacts (organization_id, name, position, email, phone, basis,"
                " basis_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (org_id, v["name"], v["position"], v["email"], v["phone"], v["basis"],
                 v["basis_date"]),
            ).lastrowid
            log_access(conn, employee["id"], "izveidoja", "kontaktpersona", contact_id, org_id)
    if form.ok:
        return _see_other(f"/organizacijas/{org_id}#kontakti")
    return render(request, "contact_form.html", {
        "employee": employee, "org": org, "contact": None, "errors": form.errors,
        "values": form.values, "bases": schema.BASES,
    }, status=400)


def _contact_with_org(conn, contact_id: int):
    contact = get_or_404(conn, "SELECT * FROM contacts WHERE id = ?", contact_id)
    org = get_or_404(conn, "SELECT * FROM organizations WHERE id = ?", contact["organization_id"])
    return contact, org


@router.get("/kontakti/{contact_id}/labot")
def contact_edit(request: Request, contact_id: int):
    employee = current_employee(request)
    with crm_db(request).connect() as conn:
        contact, org = _contact_with_org(conn, contact_id)
        require(can_edit_org(employee, org))
    values = {k: contact[k] for k in ("name", "position", "email", "phone", "basis", "basis_date")}
    return render(request, "contact_form.html", {
        "employee": employee, "org": org, "contact": contact, "errors": {}, "values": values,
        "bases": schema.BASES,
    })


@router.post("/kontakti/{contact_id}/labot")
async def contact_update(request: Request, contact_id: int):
    employee = current_employee(request)
    form = Form(await request.form())
    _contact_form(form)
    with crm_db(request).transaction() as conn:
        contact, org = _contact_with_org(conn, contact_id)
        require(can_edit_org(employee, org))
        if form.ok:
            v = form.values
            conn.execute(
                "UPDATE contacts SET name = ?, position = ?, email = ?, phone = ?, basis = ?,"
                " basis_date = ? WHERE id = ?",
                (v["name"], v["position"], v["email"], v["phone"], v["basis"], v["basis_date"],
                 contact_id),
            )
            log_access(conn, employee["id"], "mainīja", "kontaktpersona", contact_id, org["id"])
    if form.ok:
        return _see_other(f"/organizacijas/{org['id']}#kontakti")
    return render(request, "contact_form.html", {
        "employee": employee, "org": org, "contact": contact, "errors": form.errors,
        "values": form.values, "bases": schema.BASES,
    }, status=400)


@router.get("/kontakti/{contact_id}/dzest")
def contact_delete_confirm(request: Request, contact_id: int):
    employee = current_employee(request)
    require(is_admin(employee))
    with crm_db(request).connect() as conn:
        contact, org = _contact_with_org(conn, contact_id)
    return render(request, "contact_delete.html", {
        "employee": employee, "contact": contact, "org": org,
    })


@router.post("/kontakti/{contact_id}/dzest")
def contact_delete(request: Request, contact_id: int):
    employee = current_employee(request)
    require(is_admin(employee))
    with crm_db(request).transaction() as conn:
        contact, org = _contact_with_org(conn, contact_id)
        # Vārds var būt minēts arī brīvajā tekstā; to aizstāj ar anonīmu apzīmējumu.
        for column in ("summary", "next_step"):
            conn.execute(
                f"UPDATE interactions SET {column} = replace({column}, ?, ?)"
                " WHERE organization_id = ?",
                (contact["name"], ANONYMOUS, org["id"]),
            )
        conn.execute(
            "UPDATE interaction_participants SET contact_id = NULL WHERE contact_id = ?",
            (contact_id,),
        )
        conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
        log_access(conn, employee["id"], "dzēsa", "kontaktpersona", contact_id, org["id"])
    return _see_other(f"/organizacijas/{org['id']}?dzests=1#kontakti")


# --- F3 · mijiedarbības ar MI-1 --------------------------------------------------------

def _interaction_context(request, employee, org, contacts, values, errors, suggestion=None):
    return {
        "employee": employee, "org": org, "contacts": contacts, "values": values,
        "errors": errors, "suggestion": suggestion,
        "selected": set(values.get("participants", [])),
    }


@router.get("/organizacijas/{org_id}/mijiedarbibas/jauna")
def interaction_new(request: Request, org_id: int):
    employee = current_employee(request)
    with crm_db(request).connect() as conn:
        org = _editable_org(conn, employee, org_id)
        contacts = conn.execute(
            "SELECT id, name FROM contacts WHERE organization_id = ? ORDER BY name", (org_id,)
        ).fetchall()
    values = {"date": today(request).isoformat(), "kind": "zvans", "participants": []}
    return render(request, "interaction_form.html",
                  _interaction_context(request, employee, org, contacts, values, {}))


@router.post("/organizacijas/{org_id}/mijiedarbibas/jauna")
async def interaction_create(request: Request, org_id: int):
    employee = current_employee(request)
    data = await request.form()
    with crm_db(request).connect() as conn:
        org = _editable_org(conn, employee, org_id)
        contacts = conn.execute(
            "SELECT id, name FROM contacts WHERE organization_id = ? ORDER BY name", (org_id,)
        ).fetchall()
    contact_ids = {str(c["id"]) for c in contacts}
    form = Form(data)
    form.choice("kind", "Veids", schema.KINDS)
    form.date("date", "Datums")
    notes = form.text("notes", "Piezīmes", required=False, max_len=8000)
    participants = [p for p in data.getlist("participants") if p in contact_ids]
    form.values["participants"] = participants
    ai_generated = data.get("ai_generated") == "1"
    form.values["ai_generated"] = "1" if ai_generated else ""

    if data.get("action") == "generate":
        form.values["summary"] = str(data.get("summary", ""))
        form.values["next_step"] = str(data.get("next_step", ""))
        form.errors.pop("kind", None)
        form.errors.pop("date", None)
        if not notes:
            form.error("notes", "Ievadi piezīmes, no kurām veidot kopsavilkumu.")
            return render(request, "interaction_form.html", _interaction_context(
                request, employee, org, contacts, form.values, form.errors), status=400)
        suggestion = ai.kopsavilkums(notes)
        form.values.update(summary=suggestion.summary, next_step=suggestion.next_step,
                           ai_generated="1")
        return render(request, "interaction_form.html", _interaction_context(
            request, employee, org, contacts, form.values, {}, suggestion))

    summary = form.text("summary", "Kopsavilkums", max_len=2000)
    next_step = form.text("next_step", "Nākamais solis", required=False, max_len=500)
    if not form.ok:
        return render(request, "interaction_form.html", _interaction_context(
            request, employee, org, contacts, form.values, form.errors), status=400)
    with crm_db(request).transaction() as conn:
        interaction_id = conn.execute(
            "INSERT INTO interactions (organization_id, author_id, kind, date, summary, next_step,"
            " ai_generated, approved_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (org_id, employee["id"], form.values["kind"], form.values["date"], summary, next_step,
             int(ai_generated), employee["id"] if ai_generated else None),
        ).lastrowid
        conn.executemany(
            "INSERT INTO interaction_participants (interaction_id, contact_id) VALUES (?, ?)",
            [(interaction_id, int(p)) for p in participants],
        )
        log_access(conn, employee["id"], "izveidoja", "mijiedarbība", interaction_id, org_id)
    return _see_other(f"/organizacijas/{org_id}#mijiedarbibas")
