"""F4 pieprasījumi un F5 uzdevumi."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from . import schema
from .web import (
    Form, can_edit_org, crm_db, current_employee, get_or_404, is_manager, log_access, render,
    require, today,
)

router = APIRouter(include_in_schema=False)


def is_overdue(request_row, day) -> bool:
    """Kavēts: termiņš pagājis un nav atbildēts (F4)."""
    return request_row["status"] != "atbildets" and request_row["deadline"] < day.isoformat()


# --- F4 · pieprasījumi -----------------------------------------------------------------

@router.get("/pieprasijumi")
def request_list(request: Request, statuss: str = "", kavetie: str = ""):
    employee = current_employee(request)
    with crm_db(request).connect() as conn:
        rows = conn.execute(
            "SELECT r.*, o.name AS org_name FROM requests r"
            " JOIN organizations o ON o.id = r.organization_id ORDER BY r.deadline"
        ).fetchall()
    day = today(request)
    if statuss in schema.STATUSES:
        rows = [r for r in rows if r["status"] == statuss]
    if kavetie:
        rows = [r for r in rows if is_overdue(r, day)]
    return render(request, "request_list.html", {
        "employee": employee, "rows": rows, "statuss": statuss, "kavetie": bool(kavetie),
        "overdue": {r["id"] for r in rows if is_overdue(r, day)},
    })


@router.get("/organizacijas/{org_id}/pieprasijumi/jauns")
def request_new(request: Request, org_id: int):
    employee = current_employee(request)
    with crm_db(request).connect() as conn:
        org = get_or_404(conn, "SELECT * FROM organizations WHERE id = ?", org_id)
        require(can_edit_org(employee, org))
    deadline = today(request) + timedelta(days=schema.REQUEST_DAYS)
    return render(request, "request_form.html", {
        "employee": employee, "org": org, "values": {}, "errors": {}, "deadline": deadline,
    })


@router.post("/organizacijas/{org_id}/pieprasijumi/jauns")
async def request_create(request: Request, org_id: int):
    employee = current_employee(request)
    form = Form(await request.form())
    form.text("title", "Temats")
    form.text("description", "Apraksts", required=False, max_len=4000)
    day = today(request)
    deadline = day + timedelta(days=schema.REQUEST_DAYS)
    with crm_db(request).transaction() as conn:
        org = get_or_404(conn, "SELECT * FROM organizations WHERE id = ?", org_id)
        require(can_edit_org(employee, org))
        if form.ok:
            # Termiņš ir fiksēts (CR-5 precizējums), ievadē to nevar mainīt.
            request_id = conn.execute(
                "INSERT INTO requests (organization_id, title, description, created_on, deadline,"
                " status) VALUES (?, ?, ?, ?, ?, 'jauns')",
                (org_id, form.values["title"], form.values["description"], day.isoformat(),
                 deadline.isoformat()),
            ).lastrowid
            log_access(conn, employee["id"], "izveidoja", "pieprasījums", request_id, org_id)
    if form.ok:
        return RedirectResponse(f"/pieprasijumi/{request_id}", status_code=303)
    return render(request, "request_form.html", {
        "employee": employee, "org": org, "values": form.values, "errors": form.errors,
        "deadline": deadline,
    }, status=400)


@router.get("/pieprasijumi/{request_id}")
def request_detail(request: Request, request_id: int):
    employee = current_employee(request)
    with crm_db(request).connect() as conn:
        row = get_or_404(conn, "SELECT r.*, o.name AS org_name, o.responsible_id FROM requests r"
                         " JOIN organizations o ON o.id = r.organization_id WHERE r.id = ?",
                         request_id)
        tasks = conn.execute(
            "SELECT t.*, e.name AS assignee FROM tasks t JOIN employees e ON e.id = t.assignee_id"
            " WHERE t.request_id = ? ORDER BY t.done_on IS NOT NULL, t.due", (request_id,)
        ).fetchall()
    return render(request, "request_detail.html", {
        "employee": employee, "row": row, "tasks": tasks,
        "overdue": is_overdue(row, today(request)),
        "next_status": schema.NEXT_STATUS.get(row["status"]),
        "can_edit": can_edit_org(employee, row),
    })


@router.post("/pieprasijumi/{request_id}/statuss")
async def request_status(request: Request, request_id: int):
    employee = current_employee(request)
    target = str((await request.form()).get("status", ""))
    with crm_db(request).transaction() as conn:
        row = get_or_404(conn, "SELECT r.*, o.responsible_id FROM requests r"
                         " JOIN organizations o ON o.id = r.organization_id WHERE r.id = ?",
                         request_id)
        require(can_edit_org(employee, row))
        if schema.NEXT_STATUS.get(row["status"]) != target:
            # Tikai Jauns → Darbā → Atbildēts (F4); citas pārejas ir kļūda.
            raise HTTPException(400, "Statusu var mainīt tikai uz nākamo: Jauns → Darbā → Atbildēts")
        answered = today(request).isoformat() if target == "atbildets" else None
        conn.execute(
            "UPDATE requests SET status = ?, answered_on = ? WHERE id = ?",
            (target, answered, request_id),
        )
        log_access(conn, employee["id"], "mainīja", "pieprasījums", request_id,
                   row["organization_id"])
    return RedirectResponse(f"/pieprasijumi/{request_id}", status_code=303)


# --- F5 · uzdevumi ---------------------------------------------------------------------

@router.get("/uzdevumi")
def my_tasks(request: Request):
    employee = current_employee(request)
    day = today(request).isoformat()
    with crm_db(request).connect() as conn:
        tasks = conn.execute(
            "SELECT t.*, o.name AS org_name, r.title AS request_title FROM tasks t"
            " LEFT JOIN organizations o ON o.id = t.organization_id"
            " LEFT JOIN requests r ON r.id = t.request_id"
            " WHERE t.assignee_id = ? AND t.done_on IS NULL AND t.due <= ?"
            " ORDER BY t.due, t.id",
            (employee["id"], day),
        ).fetchall()
        upcoming = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE assignee_id = ? AND done_on IS NULL AND due > ?",
            (employee["id"], day),
        ).fetchone()[0]
    return render(request, "tasks.html", {
        "employee": employee, "tasks": tasks, "upcoming": upcoming, "day": day,
    })


def _task_targets(conn):
    orgs = conn.execute("SELECT id, name FROM organizations ORDER BY name").fetchall()
    requests = conn.execute(
        "SELECT r.id, r.title, o.name AS org_name FROM requests r"
        " JOIN organizations o ON o.id = r.organization_id"
        " WHERE r.status != 'atbildets' ORDER BY o.name, r.title"
    ).fetchall()
    employees = conn.execute("SELECT id, name FROM employees ORDER BY name").fetchall()
    return orgs, requests, employees


@router.get("/uzdevumi/jauns")
def task_new(request: Request, organizacija: str = "", pieprasijums: str = ""):
    employee = current_employee(request)
    with crm_db(request).connect() as conn:
        orgs, requests, employees = _task_targets(conn)
    values = {
        "assignee_id": str(employee["id"]), "due": today(request).isoformat(),
        "organization_id": organizacija, "request_id": pieprasijums,
    }
    return render(request, "task_form.html", {
        "employee": employee, "orgs": orgs, "requests": requests, "employees": employees,
        "values": values, "errors": {},
    })


@router.post("/uzdevumi/jauns")
async def task_create(request: Request):
    employee = current_employee(request)
    form = Form(await request.form())
    form.text("title", "Uzdevums")
    with crm_db(request).connect() as conn:
        orgs, requests, employees = _task_targets(conn)
    form.choice("assignee_id", "Izpildītājs", {str(e["id"]) for e in employees})
    form.date("due", "Termiņš")
    org_id = str(form.data.get("organization_id", ""))
    request_id = str(form.data.get("request_id", ""))
    form.values.update(organization_id=org_id, request_id=request_id)
    if org_id and org_id not in {str(o["id"]) for o in orgs}:
        form.error("organization_id", "Izvēlies organizāciju no saraksta.")
    if request_id and request_id not in {str(r["id"]) for r in requests}:
        form.error("request_id", "Izvēlies pieprasījumu no saraksta.")
    if not org_id and not request_id:
        form.error("organization_id", "Uzdevumam jābūt saistītam ar organizāciju vai pieprasījumu.")
    if not form.ok:
        return render(request, "task_form.html", {
            "employee": employee, "orgs": orgs, "requests": requests, "employees": employees,
            "values": form.values, "errors": form.errors,
        }, status=400)
    with crm_db(request).transaction() as conn:
        log_org = int(org_id) if org_id else conn.execute(
            "SELECT organization_id FROM requests WHERE id = ?", (int(request_id),)
        ).fetchone()[0]
        task_id = conn.execute(
            "INSERT INTO tasks (title, assignee_id, due, organization_id, request_id)"
            " VALUES (?, ?, ?, ?, ?)",
            (form.values["title"], int(form.values["assignee_id"]), form.values["due"],
             int(org_id) if org_id else None, int(request_id) if request_id else None),
        ).lastrowid
        log_access(conn, employee["id"], "izveidoja", "uzdevums", task_id, log_org)
    return RedirectResponse("/uzdevumi?pievienots=1", status_code=303)


@router.post("/uzdevumi/{task_id}/izpildits")
def task_done(request: Request, task_id: int):
    employee = current_employee(request)
    with crm_db(request).transaction() as conn:
        task = get_or_404(conn, "SELECT * FROM tasks WHERE id = ?", task_id)
        require(task["assignee_id"] == employee["id"] or is_manager(employee))
        conn.execute("UPDATE tasks SET done_on = ? WHERE id = ?",
                     (today(request).isoformat(), task_id))
        log_access(conn, employee["id"], "mainīja", "uzdevums", task_id, task["organization_id"])
    return RedirectResponse("/uzdevumi?izpildits=1", status_code=303)
