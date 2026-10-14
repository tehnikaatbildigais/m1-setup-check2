"""CR-6 uzdevumu sadales tāfele. Numuri komentāros atbilst tracker/CR-6.md tabulām."""

from __future__ import annotations

import re
import sqlite3
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.application import create_app

TODAY = date(2026, 10, 14)
ANNA, JANIS, INESE, RUTA = 1, 2, 23, 25
JSON = {"accept": "application/json"}


@pytest.fixture
def crm_db(tmp_path: Path) -> Path:
    return tmp_path / "crm.db"


@pytest.fixture
def client(tmp_path: Path, crm_db: Path):
    app = create_app(tmp_path / "users.db", crm_db_path=crm_db, today=lambda: TODAY)
    with TestClient(app) as test_client:
        yield test_client


def act_as(client, employee_id: int) -> None:
    client.post("/sakums", data={"employee_id": str(employee_id)}, follow_redirects=False)


def query(db: Path, sql: str, *params):
    with sqlite3.connect(db) as conn:
        return conn.execute(sql, params).fetchall()


def column(page: str, employee_id: int) -> str:
    match = re.search(rf'<section class="board-column" data-employee="{employee_id}".*?</section>',
                      page, re.S)
    assert match, f"nav kolonnas {employee_id}"
    return match.group(0)


# 6, 7
def test_sidebar_items_by_role(client) -> None:
    act_as(client, ANNA)
    nav = client.get("/kopsavilkums").text.split('aria-label="Galvenā navigācija"')[1].split("</nav>")[0]
    assert "/uzdevumi/sadale" not in nav and "/parskats" not in nav
    assert "<span>Kopsavilkums</span>" in nav  # redzams teksts, ne tikai ikona
    act_as(client, INESE)
    nav = client.get("/uzdevumi/sadale").text.split('aria-label="Galvenā navigācija"')[1].split("</nav>")[0]
    assert 'href="/uzdevumi/sadale" aria-current="page"' in nav
    assert 'href="/uzdevumi" aria-current' not in nav  # tikai viena aktīvā sadaļa


# 8, 9
def test_topbar_search_and_add_menu(client) -> None:
    act_as(client, ANNA)
    page = client.get("/organizacijas").text
    assert '<p class="section-title">Organizācijas</p>' in page
    assert 'role="search"' in page and 'aria-label="Meklēt"' in page
    menu = page.split('<details class="add-menu">')[1].split("</details>")[0]
    assert 'href="/organizacijas/jauna"' in menu and 'href="/uzdevumi/jauns"' in menu


# 12, 13
def test_board_access(client) -> None:
    act_as(client, ANNA)
    assert client.get("/uzdevumi/sadale").status_code == 403
    act_as(client, INESE)
    assert client.get("/uzdevumi/sadale").status_code == 200
    act_as(client, RUTA)
    assert client.get("/uzdevumi/sadale").status_code == 200


# 14, 15, 16, 17, 18
def test_board_columns_and_cards(client, crm_db) -> None:
    act_as(client, INESE)
    page = client.get("/uzdevumi/sadale").text
    with_tasks = {r[0] for r in query(crm_db, "SELECT DISTINCT assignee_id FROM tasks WHERE done_on IS NULL")}
    shown = {int(e) for e in re.findall(r'class="board-column" data-employee="(\d+)"', page)}
    assert shown == with_tasks  # noklusējums (#18)
    anna = column(page, ANNA)
    assert "Atvērti: <span data-open>3</span>" in anna
    assert "kavēti: <span data-late>1</span>" in anna
    titles = re.findall(r"<h3>([^<]+)</h3>", anna)
    assert titles[0] == "Piezvanīt par līguma redakciju"  # kavētais augšā (#16)
    assert "Kavēts" in anna and 'href="/organizacijas/2"' in anna
    done = query(crm_db, "SELECT id FROM tasks WHERE done_on IS NOT NULL")
    assert done  # sākumdatos ir izpildīti uzdevumi
    for (task_id,) in done:
        assert f'id="uzdevums-{task_id}"' not in page  # #17


# 19
def test_column_choice_is_saved_per_manager(client) -> None:
    act_as(client, INESE)
    response = client.post("/uzdevumi/sadale", data={"action": "save", "employee_ids": ["1", "22"]},
                           follow_redirects=False)
    assert response.status_code == 303
    page = client.get("/uzdevumi/sadale").text
    shown = re.findall(r'class="board-column" data-employee="(\d+)"', page)
    assert shown == ["1", "22"]  # pēc vārda: Anna, Normunds
    assert "Atvērtu uzdevumu nav." in column(page, 22)  # #27
    act_as(client, RUTA)  # cits vadītājs redz noklusējumu
    assert len(re.findall(r'class="board-column"', client.get("/uzdevumi/sadale").text)) > 2
    act_as(client, INESE)
    client.post("/uzdevumi/sadale", data={"action": "reset"})
    assert len(re.findall(r'class="board-column"', client.get("/uzdevumi/sadale").text)) > 2


# 20, 24, 25, 28
def test_reassign_json(client, crm_db) -> None:
    act_as(client, INESE)
    response = client.post("/uzdevumi/1/izpilditajs", data={"assignee_id": str(JANIS)}, headers=JSON)
    assert response.status_code == 200
    assert response.json() == {"id": 1, "assignee_id": JANIS, "assignee_name": "Jānis Ozols"}
    assert query(crm_db, "SELECT assignee_id FROM tasks WHERE id = 1") == [(JANIS,)]
    log = query(crm_db, "SELECT employee_id, action, entity, entity_id, organization_id"
                        " FROM access_log WHERE entity = 'uzdevums'")
    assert log == [(INESE, "mainīja", "uzdevums", 1, 1)]
    act_as(client, JANIS)
    assert "Nosūtīt semināra programmu" in client.get("/kopsavilkums").text
    assert "Nosūtīt semināra programmu" in client.get("/uzdevumi").text


@pytest.mark.parametrize("assignee,status", [("999", 400), ("", 400), ("abc", 400)])
def test_reassign_invalid_employee(client, assignee, status) -> None:
    act_as(client, INESE)
    response = client.post("/uzdevumi/1/izpilditajs", data={"assignee_id": assignee}, headers=JSON)
    assert response.status_code == status
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_reassign_errors(client) -> None:
    act_as(client, ANNA)
    assert client.post("/uzdevumi/1/izpilditajs", data={"assignee_id": "2"}, headers=JSON).status_code == 403
    act_as(client, INESE)
    assert client.post("/uzdevumi/9999/izpilditajs", data={"assignee_id": "2"}, headers=JSON).status_code == 404
    client.post("/uzdevumi/7/izpildits", data={})  # Inese ir vadītāja, drīkst atzīmēt
    done = client.post("/uzdevumi/7/izpilditajs", data={"assignee_id": "2"}, headers=JSON)
    assert done.status_code == 400


# 23 (bez JS)
def test_reassign_form_redirects_back_to_board(client, crm_db) -> None:
    act_as(client, RUTA)
    response = client.post("/uzdevumi/2/izpilditajs", data={"assignee_id": "3"}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/uzdevumi/sadale?nodots=2#uzdevums-2"
    page = client.get(response.headers["location"]).text
    assert "Uzdevums nodots: Līga Bērziņa" in page
    assert query(crm_db, "SELECT assignee_id FROM tasks WHERE id = 2") == [(3,)]


def test_reassign_to_same_employee_is_noop(client, crm_db) -> None:
    act_as(client, INESE)
    client.post("/uzdevumi/1/izpilditajs", data={"assignee_id": str(ANNA)}, headers=JSON)
    assert query(crm_db, "SELECT COUNT(*) FROM access_log WHERE entity = 'uzdevums'") == [(0,)]


def test_every_card_has_labelled_reassign_control(client) -> None:
    act_as(client, INESE)
    page = client.get("/uzdevumi/sadale").text
    cards = re.findall(r'<li class="task-card[^"]*" id="uzdevums-(\d+)"', page)
    assert cards
    for task_id in cards:
        assert f'<label for="reassign-{task_id}" class="visually-hidden">Nodot citam darbiniekam:' in page
        assert f'action="/uzdevumi/{task_id}/izpilditajs"' in page


# 26
def test_board_is_scrollable_named_region(client) -> None:
    act_as(client, INESE)
    page = client.get("/uzdevumi/sadale").text
    assert '<div class="board" data-board role="region" aria-label="Darbinieku kolonnas" tabindex="0">' in page
    assert '<script src="/static/board.js" defer></script>' in page
