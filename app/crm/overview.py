"""N3 sākumlapa, F6 meklēšana, F7 pārskats, N2 administrēšana, F8 piekļūstamība."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from . import chart, schema
from .web import (
    EMPLOYEE_COOKIE, Form, NeedsEmployee, crm_db, current_employee, is_admin, is_manager, render, require,
    today,
)
from .work import is_overdue

router = APIRouter(include_in_schema=False)

SEARCH_LIMIT = 50
TOP_ORGS = 5


# --- N3 · sākumlapa (mācību režīms) -----------------------------------------------------

@router.get("/sakums")
def home(request: Request):
    with crm_db(request).connect() as conn:
        employees = conn.execute("SELECT * FROM employees ORDER BY role, name").fetchall()
    selected = request.cookies.get(EMPLOYEE_COOKIE, "")
    return render(request, "home.html", {"employees": employees, "selected": selected,
                                         "errors": {}})


@router.post("/sakums")
async def choose_employee(request: Request):
    raw = str((await request.form()).get("employee_id", ""))
    with crm_db(request).connect() as conn:
        employees = conn.execute("SELECT * FROM employees ORDER BY role, name").fetchall()
    if raw not in {str(e["id"]) for e in employees}:
        return render(request, "home.html", {
            "employees": employees, "selected": raw,
            "errors": {"employee_id": "Izvēlies darbinieku no saraksta."},
        }, status=400)
    response = RedirectResponse("/uzdevumi", status_code=303)
    response.set_cookie(EMPLOYEE_COOKIE, raw, httponly=True, samesite="lax", path="/")
    return response


# --- F6 · meklēšana -------------------------------------------------------------------

@router.get("/meklet")
def search(request: Request, q: str = ""):
    employee = current_employee(request)
    query = q.strip()
    results: list[dict] = []
    if query:
        needle = query.casefold()
        with crm_db(request).connect() as conn:
            for o in conn.execute("SELECT * FROM organizations ORDER BY name"):
                if needle in o["name"].casefold() or needle in o["reg_nr"]:
                    results.append({"type": "Organizācija", "name": o["name"],
                                    "url": f"/organizacijas/{o['id']}", "org": o["name"]})
            for c in conn.execute(
                "SELECT c.*, o.name AS org_name FROM contacts c"
                " JOIN organizations o ON o.id = c.organization_id ORDER BY c.name"
            ):
                if needle in c["name"].casefold() or needle in c["email"].casefold():
                    results.append({"type": "Kontaktpersona", "name": c["name"],
                                    "url": f"/organizacijas/{c['organization_id']}#kontakti",
                                    "org": c["org_name"]})
            for r in conn.execute(
                "SELECT r.*, o.name AS org_name FROM requests r"
                " JOIN organizations o ON o.id = r.organization_id ORDER BY r.title"
            ):
                if needle in r["title"].casefold() or needle in r["description"].casefold():
                    results.append({"type": "Pieprasījums", "name": r["title"],
                                    "url": f"/pieprasijumi/{r['id']}", "org": r["org_name"]})
    return render(request, "search.html", {
        "employee": employee, "q": query, "results": results[:SEARCH_LIMIT],
        "total": len(results),
    })


# --- F7 · pārskats vadītājam ------------------------------------------------------------

@router.get("/parskats")
def report(request: Request, no: str = "", lidz: str = ""):
    employee = current_employee(request)
    require(is_manager(employee))
    day = today(request)
    form = Form({"no": no or (day - timedelta(days=30)).isoformat(), "lidz": lidz or day.isoformat()})
    start, end = form.date("no", "No"), form.date("lidz", "Līdz")
    if start and end and start > end:
        form.error("no", "Perioda sākumam jābūt agrākam par beigām vai vienādam ar tām.")
    if not form.ok:
        return render(request, "report.html", {
            "employee": employee, "values": form.values, "errors": form.errors,
        }, status=400)

    period = (start.isoformat(), end.isoformat())
    with crm_db(request).connect() as conn:
        activity = conn.execute(
            "SELECT e.name, COUNT(*) AS n FROM interactions i JOIN employees e ON e.id = i.author_id"
            " WHERE i.date BETWEEN ? AND ? GROUP BY e.id ORDER BY n DESC, e.name", period
        ).fetchall()
        top_orgs = conn.execute(
            "SELECT o.id, o.name, COUNT(*) AS n FROM interactions i"
            " JOIN organizations o ON o.id = i.organization_id WHERE i.date BETWEEN ? AND ?"
            " GROUP BY o.id ORDER BY n DESC, o.name LIMIT ?", (*period, TOP_ORGS)
        ).fetchall()
        candidates = conn.execute(
            "SELECT r.*, o.name AS org_name FROM requests r"
            " JOIN organizations o ON o.id = r.organization_id"
            " WHERE r.deadline BETWEEN ? AND ? ORDER BY r.deadline", period
        ).fetchall()
    # Kavēts periodā: termiņš periodā un atbildēts pēc termiņa vai vēl nav atbildēts.
    late = [r for r in candidates
            if is_overdue(r, day) or (r["answered_on"] and r["answered_on"] > r["deadline"])]
    rows = [(a["name"], a["n"]) for a in activity]
    svg = chart.bar_chart(
        rows,
        "Mijiedarbības pa darbiniekiem",
        f"Horizontāla stabiņu diagramma: mijiedarbību skaits pa darbiniekiem no "
        f"{start:%d.%m.%Y.} līdz {end:%d.%m.%Y.}. Tie paši dati ir tabulā zem diagrammas.",
    ) if rows else ""
    return render(request, "report.html", {
        "employee": employee, "values": form.values, "errors": {}, "start": start, "end": end,
        "activity": activity, "top_orgs": top_orgs, "late": late, "svg": svg,
        "total": sum(n for _, n in rows),
    })


# --- N2/N3 · administrēšana ----------------------------------------------------------------

def _admin(request: Request):
    employee = current_employee(request)
    require(is_admin(employee))
    return employee


@router.get("/admin/lomas")
def admin_roles(request: Request, saglabats: str = ""):
    employee = _admin(request)
    with crm_db(request).connect() as conn:
        employees = conn.execute("SELECT * FROM employees ORDER BY name").fetchall()
    return render(request, "admin_roles.html", {
        "employee": employee, "employees": employees, "saved": saglabats, "error": "",
    })


@router.post("/admin/lomas/{employee_id}")
async def admin_set_role(request: Request, employee_id: int):
    employee = _admin(request)
    role = str((await request.form()).get("role", ""))
    if role not in schema.ROLES:
        raise HTTPException(400, "Nezināma loma")
    with crm_db(request).transaction() as conn:
        target = conn.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()
        if target is None:
            raise HTTPException(404, "Darbinieks nav atrasts")
        admins = conn.execute(
            "SELECT COUNT(*) FROM employees WHERE role = 'administrators'"
        ).fetchone()[0]
        blocked = target["role"] == "administrators" and role != "administrators" and admins == 1
        if not blocked:
            conn.execute("UPDATE employees SET role = ? WHERE id = ?", (role, employee_id))
        employees = conn.execute("SELECT * FROM employees ORDER BY name").fetchall()
    if blocked:
        return render(request, "admin_roles.html", {
            "employee": employee, "employees": employees, "saved": "",
            "error": "Sistēmā jāpaliek vismaz vienam administratoram.",
        }, status=400)
    return RedirectResponse(f"/admin/lomas?saglabats={employee_id}", status_code=303)


@router.get("/admin/glabasana")
def admin_retention(request: Request):
    employee = _admin(request)
    cutoff = schema.retention_cutoff(today(request)).isoformat()
    with crm_db(request).connect() as conn:
        contacts = conn.execute(
            "SELECT c.id, c.name, c.organization_id, o.name AS org_name,"
            " max(c.basis_date, COALESCE((SELECT max(i.date) FROM interaction_participants ip"
            "   JOIN interactions i ON i.id = ip.interaction_id WHERE ip.contact_id = c.id), ''))"
            " AS last_contact"
            " FROM contacts c JOIN organizations o ON o.id = c.organization_id"
            " ORDER BY last_contact"
        ).fetchall()
    expired = [c for c in contacts if c["last_contact"] < cutoff]
    return render(request, "admin_retention.html", {
        "employee": employee, "expired": expired, "cutoff": cutoff,
    })


@router.get("/admin/zurnals")
def admin_log(request: Request, darbinieks: str = "", organizacija: str = ""):
    employee = _admin(request)
    where, params = [], []
    if darbinieks.isdigit():
        where.append("l.employee_id = ?")
        params.append(int(darbinieks))
    if organizacija.isdigit():
        where.append("l.organization_id = ?")
        params.append(int(organizacija))
    sql = ("SELECT l.*, e.name AS employee_name, o.name AS org_name FROM access_log l"
           " JOIN employees e ON e.id = l.employee_id"
           " LEFT JOIN organizations o ON o.id = l.organization_id")
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY l.id DESC LIMIT 200"
    with crm_db(request).connect() as conn:
        entries = conn.execute(sql, params).fetchall()
        employees = conn.execute("SELECT id, name FROM employees ORDER BY name").fetchall()
        orgs = conn.execute("SELECT id, name FROM organizations ORDER BY name").fetchall()
    return render(request, "admin_log.html", {
        "employee": employee, "entries": entries, "employees": employees, "orgs": orgs,
        "darbinieks": darbinieks, "organizacija": organizacija,
    })


# --- F8 · piekļūstamības paziņojums ----------------------------------------------------

@router.get("/pieklustamiba")
def accessibility(request: Request):
    try:
        employee = current_employee(request)
    except NeedsEmployee:
        employee = None
    return render(request, "accessibility.html", {"employee": employee})
