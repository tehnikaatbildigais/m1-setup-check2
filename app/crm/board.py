"""CR-6 · uzdevumu sadales tāfele: kolonnas ir darbinieki, kartītes ir atvērtie uzdevumi."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from ..errors import ApiError, wants_json
from .web import crm_db, current_employee, get_or_404, is_manager, log_access, render, require, today

router = APIRouter(include_in_schema=False)


def _manager(request: Request):
    employee = current_employee(request)
    require(is_manager(employee))
    return employee


@router.get("/uzdevumi/sadale")
def board(request: Request, nodots: str = "", saglabats: str = ""):
    employee = _manager(request)
    day = today(request).isoformat()
    with crm_db(request).connect() as conn:
        employees = conn.execute("SELECT id, name, role FROM employees ORDER BY name").fetchall()
        tasks = conn.execute(
            "SELECT t.*, o.name AS org_name, r.title AS request_title FROM tasks t"
            " LEFT JOIN organizations o ON o.id = t.organization_id"
            " LEFT JOIN requests r ON r.id = t.request_id"
            " WHERE t.done_on IS NULL ORDER BY t.due, t.id"
        ).fetchall()
        saved = {r[0] for r in conn.execute(
            "SELECT employee_id FROM board_columns WHERE manager_id = ?", (employee["id"],)
        )}
        moved = None
        if nodots.isdigit():
            moved = conn.execute(
                "SELECT t.title, e.name FROM tasks t JOIN employees e ON e.id = t.assignee_id"
                " WHERE t.id = ?", (int(nodots),)
            ).fetchone()

    by_employee: dict[int, list] = {}
    for task in tasks:
        by_employee.setdefault(task["assignee_id"], []).append(task)
    if saved:
        shown = [e for e in employees if e["id"] in saved]
    else:
        shown = [e for e in employees if e["id"] in by_employee]

    columns = []
    for person in shown:
        # SQL kārto pēc termiņa, tāpēc kavētie (termiņš < šodiena) jau ir augšā.
        cards = by_employee.get(person["id"], [])
        late = sum(1 for t in cards if t["due"] < day)
        columns.append({"employee": person, "cards": cards, "late": late})
    busiest = max((len(c["cards"]) for c in columns), default=0) or 1
    return render(request, "board.html", {
        "employee": employee, "employees": employees, "columns": columns, "day": day,
        "busiest": busiest, "custom": bool(saved), "shown_ids": {e["id"] for e in shown},
        "total_open": sum(len(c["cards"]) for c in columns),
        "total_late": sum(c["late"] for c in columns),
        "moved": moved, "saved": bool(saglabats),
    })


@router.post("/uzdevumi/sadale")
async def save_columns(request: Request):
    employee = _manager(request)
    data = await request.form()
    with crm_db(request).transaction() as conn:
        valid = {str(r[0]) for r in conn.execute("SELECT id FROM employees")}
        chosen = [int(e) for e in data.getlist("employee_ids") if e in valid]
        conn.execute("DELETE FROM board_columns WHERE manager_id = ?", (employee["id"],))
        if data.get("action") != "reset":
            conn.executemany(
                "INSERT INTO board_columns (manager_id, employee_id) VALUES (?, ?)",
                [(employee["id"], e) for e in chosen],
            )
    return RedirectResponse("/uzdevumi/sadale?saglabats=1", status_code=303)


@router.post("/uzdevumi/{task_id}/izpilditajs")
async def reassign(request: Request, task_id: int):
    employee = _manager(request)
    raw = str((await request.form()).get("assignee_id", ""))
    with crm_db(request).transaction() as conn:
        task = get_or_404(conn, "SELECT * FROM tasks WHERE id = ?", task_id)
        target = conn.execute(
            "SELECT id, name FROM employees WHERE id = ?", (int(raw) if raw.isdigit() else -1,)
        ).fetchone()
        if target is None:
            raise HTTPException(400, "Izvēlies darbinieku no saraksta")
        if task["done_on"] is not None:
            # JSON klientam atsevišķs kods, lai tāfele var noņemt novecojušo kartīti.
            if wants_json(request):
                raise ApiError(400, "TASK_DONE", "Uzdevums jau ir izpildīts")
            raise HTTPException(400, "Uzdevums jau ir izpildīts")
        changed = task["assignee_id"] != target["id"]
        if changed:
            conn.execute("UPDATE tasks SET assignee_id = ? WHERE id = ?", (target["id"], task_id))
            organization = task["organization_id"] or conn.execute(
                "SELECT organization_id FROM requests WHERE id = ?", (task["request_id"],)
            ).fetchone()[0]
            log_access(conn, employee["id"], "mainīja", "uzdevums", task_id, organization)
    if wants_json(request):
        return JSONResponse({"id": task_id, "assignee_id": target["id"],
                             "assignee_name": target["name"]})
    # Paziņojums „Uzdevums nodots” tikai tad, ja izpildītājs tiešām mainījās.
    query = f"?nodots={task_id}" if changed else ""
    return RedirectResponse(f"/uzdevumi/sadale{query}#uzdevums-{task_id}", status_code=303)
