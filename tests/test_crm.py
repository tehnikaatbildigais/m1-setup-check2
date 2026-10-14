"""CR-5 pieņemšanas kritēriji. Numuri komentāros atbilst tracker/CR-5.md tabulām."""

from __future__ import annotations

import re
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.application import create_app
from app.crm import ai

TODAY = date(2026, 10, 14)
ANNA, JANIS, INESE, RUTA = 1, 2, 23, 25  # darbinieki 1, 2; vadītāja; administratore
ANNA_ORG, JANIS_ORG = 1, 3
HTML = {"accept": "text/html"}


@pytest.fixture
def crm_db(tmp_path: Path) -> Path:
    return tmp_path / "crm.db"


@pytest.fixture
def client(tmp_path: Path, crm_db: Path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    app = create_app(tmp_path / "users.db", crm_db_path=crm_db, today=lambda: TODAY)
    with TestClient(app) as test_client:
        yield test_client


def act_as(client, employee_id: int) -> None:
    response = client.post("/sakums", data={"employee_id": str(employee_id)}, follow_redirects=False)
    assert response.status_code == 303


def query(db: Path, sql: str, *params):
    with sqlite3.connect(db) as conn:
        return conn.execute(sql, params).fetchall()


ORG = {"name": 'SIA "Testa birojs"', "reg_nr": "12345678901", "type": "uznemums",
       "responsible_id": str(ANNA)}
CONTACT = {"name": "Testa Persona", "position": "vadītāja", "email": "testa@example.com",
           "phone": "+37120000099", "basis": "Līgums", "basis_date": "2026-10-01"}


# --- Lomas un sākumlapa (N3) ------------------------------------------------------------

# 1
def test_home_lists_employees_and_stores_choice(client) -> None:
    page = client.get("/sakums").text
    assert "Anna Kalniņa" in page and "Rūta Saulīte" in page
    assert 'label="Administratori"' in page
    response = client.post("/sakums", data={"employee_id": "1"}, follow_redirects=False)
    assert response.headers["location"] == "/kopsavilkums"
    assert "crm_darbinieks=1" in response.headers["set-cookie"]


def test_home_rejects_unknown_employee(client) -> None:
    response = client.post("/sakums", data={"employee_id": "999"})
    assert response.status_code == 400
    assert "Izvēlies darbinieku no saraksta." in response.text


def test_pages_require_chosen_employee(client) -> None:
    response = client.get("/organizacijas", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/sakums"


# 2
def test_employee_sees_all_orgs_with_own_marked(client) -> None:
    act_as(client, ANNA)
    page = client.get("/organizacijas").text
    assert page.count('href="/organizacijas/') >= 10
    assert page.count(">Mana</span>") == 2
    mine = client.get("/organizacijas?mans=1").text
    assert "Ezerkrasta koks" in mine and "Ezermalas ūdens" not in mine


# 3
def test_employee_reads_other_org_but_cannot_edit(client) -> None:
    act_as(client, ANNA)
    page = client.get(f"/organizacijas/{JANIS_ORG}").text
    assert "Ezermalas ūdens" in page
    assert "Labot organizāciju" not in page
    assert "Pievienot kontaktpersonu" not in page
    assert client.post(f"/organizacijas/{JANIS_ORG}/labot", data=ORG).status_code == 403
    assert client.post(f"/organizacijas/{JANIS_ORG}/kontakti/jauns", data=CONTACT).status_code == 403


def test_employee_edits_own_org(client) -> None:
    act_as(client, ANNA)
    data = dict(ORG, reg_nr="10000000001")
    response = client.post(f"/organizacijas/{ANNA_ORG}/labot", data=data, follow_redirects=False)
    assert response.status_code == 303


# 4
def test_manager_edits_any_org_and_sees_report(client) -> None:
    act_as(client, INESE)
    data = dict(ORG, reg_nr="10000000003", responsible_id=str(JANIS))
    response = client.post(f"/organizacijas/{JANIS_ORG}/labot", data=data, follow_redirects=False)
    assert response.status_code == 303
    assert client.get("/parskats").status_code == 200
    assert client.get("/admin/lomas").status_code == 403


# 5
def test_admin_changes_role(client, crm_db) -> None:
    act_as(client, RUTA)
    response = client.post(f"/admin/lomas/{ANNA}", data={"role": "vaditajs"}, follow_redirects=False)
    assert response.status_code == 303
    assert query(crm_db, "SELECT role FROM employees WHERE id = ?", ANNA) == [("vaditajs",)]


def test_last_admin_cannot_be_demoted(client) -> None:
    act_as(client, RUTA)
    response = client.post(f"/admin/lomas/{RUTA}", data={"role": "darbinieks"})
    assert response.status_code == 400
    assert "vismaz vienam administratoram" in response.text


# 6
@pytest.mark.parametrize("path", ["/parskats", "/admin/lomas", "/admin/glabasana",
                                  "/admin/zurnals", "/kontakti/1/dzest"])
def test_employee_gets_403_on_manager_and_admin_pages(client, path) -> None:
    act_as(client, ANNA)
    assert client.get(path).status_code == 403


def test_forbidden_is_html_for_browser_and_json_otherwise(client) -> None:
    act_as(client, ANNA)
    html = client.get("/parskats", headers=HTML)
    assert html.status_code == 403
    assert html.headers["content-type"].startswith("text/html")
    assert "Nav piekļuves" in html.text
    assert client.get("/parskats").json()["error"]["code"] == "FORBIDDEN"


# 7
def test_footer_marks_training_mode(client) -> None:
    act_as(client, ANNA)
    page = client.get("/uzdevumi").text
    assert "Mācību režīms, nav pieteikšanās" in page
    assert 'href="/pieklustamiba"' in page


# --- Organizācijas (F1) -----------------------------------------------------------------

# 8
def test_create_org_redirects_to_card(client) -> None:
    act_as(client, ANNA)
    response = client.post("/organizacijas/jauna", data=ORG, follow_redirects=False)
    assert response.status_code == 303
    card = client.get(response.headers["location"]).text
    assert "Testa birojs" in card


# 9
def test_invalid_reg_nr_rerenders_form_with_linked_error(client) -> None:
    act_as(client, ANNA)
    response = client.post("/organizacijas/jauna", data=dict(ORG, reg_nr="123"))
    assert response.status_code == 400
    page = response.text
    assert 'value="SIA &#34;Testa birojs&#34;"' in page or 'value="SIA &quot;Testa birojs&quot;"' in page
    assert 'aria-describedby="f-reg_nr-hint f-reg_nr-error"' in page
    assert 'aria-invalid="true"' in page
    assert re.search(r'class="error-summary"[^>]*autofocus', page)
    assert 'href="#f-reg_nr"' in page


# 10
def test_duplicate_reg_nr(client) -> None:
    act_as(client, ANNA)
    response = client.post("/organizacijas/jauna", data=dict(ORG, reg_nr="10000000001"))
    assert response.status_code == 400
    assert "Organizācija ar šo reģ. nr. jau ir reģistrēta." in response.text


# 11
def test_org_type_must_be_known(client) -> None:
    act_as(client, ANNA)
    response = client.post("/organizacijas/jauna", data=dict(ORG, type="cits"))
    assert response.status_code == 400
    assert "Izvēlies: veids." in response.text


# 12
def test_form_fields_have_labels_and_required_text(client) -> None:
    act_as(client, ANNA)
    page = client.get("/organizacijas/jauna").text
    for field in ("name", "reg_nr", "type", "responsible_id"):
        assert f'<label for="f-{field}">' in page
    assert page.count("(obligāts)") == 4


# --- Kontaktpersonas (F2, N2) -------------------------------------------------------------

# 13
def test_create_contact(client, crm_db) -> None:
    act_as(client, ANNA)
    response = client.post(f"/organizacijas/{ANNA_ORG}/kontakti/jauns", data=CONTACT,
                           follow_redirects=False)
    assert response.status_code == 303
    rows = query(crm_db, "SELECT name, basis FROM contacts WHERE email = ?", CONTACT["email"])
    assert rows == [("Testa Persona", "Līgums")]
    columns = [r[1] for r in query(crm_db, "PRAGMA table_info(contacts)")]
    assert columns == ["id", "organization_id", "name", "position", "email", "phone", "basis",
                       "basis_date"]


# 14
@pytest.mark.parametrize("phone,ok", [("+37120000000", True), ("20000000", True),
                                      ("2000000", False), ("+3712000000", False),
                                      ("+44 20 0000 0000", False)])
def test_phone_format(client, phone, ok) -> None:
    act_as(client, ANNA)
    response = client.post(f"/organizacijas/{ANNA_ORG}/kontakti/jauns",
                           data=dict(CONTACT, phone=phone), follow_redirects=False)
    assert response.status_code == (303 if ok else 400)


# 15
def test_contact_email_validated(client) -> None:
    act_as(client, ANNA)
    response = client.post(f"/organizacijas/{ANNA_ORG}/kontakti/jauns",
                           data=dict(CONTACT, email="testa@"))
    assert response.status_code == 400
    assert "Ievadi derīgu e-pastu" in response.text


# 16
def test_retention_lists_contacts_older_than_two_years(client) -> None:
    act_as(client, RUTA)
    page = client.get("/admin/glabasana").text
    assert "Aldis Smiltnieks" in page and "Ainārs Pļaviņš" in page
    assert "Termiņš beidzies" in page
    assert "Aija Mežule" not in page


# 17
def test_admin_deletes_contact_and_anonymizes(client, crm_db) -> None:
    act_as(client, ANNA)
    client.post(f"/organizacijas/{ANNA_ORG}/mijiedarbibas/jauna", data={
        "action": "save", "kind": "zvans", "date": "2026-10-13", "participants": "1",
        "summary": "Runāju ar Aija Mežule par semināru.", "next_step": "",
    })
    act_as(client, RUTA)
    response = client.post("/kontakti/1/dzest", follow_redirects=False)
    assert response.status_code == 303
    assert query(crm_db, "SELECT COUNT(*) FROM contacts WHERE id = 1") == [(0,)]
    card = client.get(f"/organizacijas/{ANNA_ORG}").text
    assert "Aija Mežule" not in card
    assert "Dzēsta kontaktpersona" in card
    log = query(crm_db, "SELECT action, entity, entity_id FROM access_log WHERE action = 'dzēsa'")
    assert log == [("dzēsa", "kontaktpersona", 1)]
    assert "Aija Mežule" not in client.get("/admin/zurnals").text


# --- Mijiedarbības (F3, MI-1) ------------------------------------------------------------

def interaction_count(db: Path) -> int:
    return query(db, "SELECT COUNT(*) FROM interactions")[0][0]


# 18
def test_create_interaction_shows_newest_first(client) -> None:
    act_as(client, ANNA)
    response = client.post(f"/organizacijas/{ANNA_ORG}/mijiedarbibas/jauna", data={
        "action": "save", "kind": "sanaksme", "date": TODAY.isoformat(),
        "summary": "Jaunākā tikšanās.", "next_step": "Nosūtīt protokolu.",
    }, follow_redirects=False)
    assert response.status_code == 303
    card = client.get(f"/organizacijas/{ANNA_ORG}").text
    timeline = card.split('class="timeline"')[1]
    assert timeline.index("Jaunākā tikšanās.") < timeline.index("Pārrunāta sadarbība")


def test_interaction_requires_summary(client) -> None:
    act_as(client, ANNA)
    response = client.post(f"/organizacijas/{ANNA_ORG}/mijiedarbibas/jauna", data={
        "action": "save", "kind": "zvans", "date": TODAY.isoformat(), "summary": "",
    })
    assert response.status_code == 400


NOTES = ("Zvanīju par semināru. Viņi vēlas divas tēmas. Programma jāsūta līdz piektdienai. "
         "Vēl runājām par telpām. Un par kafiju.")


# 19
def test_generate_returns_marked_suggestion_without_saving(client, crm_db) -> None:
    act_as(client, ANNA)
    before = interaction_count(crm_db)
    response = client.post(f"/organizacijas/{ANNA_ORG}/mijiedarbibas/jauna", data={
        "action": "generate", "kind": "zvans", "date": TODAY.isoformat(), "notes": NOTES,
    })
    assert response.status_code == 200
    assert "Ģenerēts ar MI" in response.text
    assert "Apstiprināt un saglabāt" in response.text
    summary = re.search(r'<textarea id="f-summary"[^>]*>([^<]*)</textarea>', response.text).group(1)
    assert 1 <= len(re.findall(r"[.!?](\s|$)", summary)) <= 3
    assert "Nosūtīt semināra programmu" in response.text
    assert interaction_count(crm_db) == before


def test_imitation_limits_to_three_sentences() -> None:
    suggestion = ai.imitation(NOTES)
    assert suggestion.summary.count(".") == 3
    assert suggestion.source == "imitācija"


# 20
def test_approved_ai_summary_is_marked_in_timeline(client, crm_db) -> None:
    act_as(client, ANNA)
    client.post(f"/organizacijas/{ANNA_ORG}/mijiedarbibas/jauna", data={
        "action": "save", "kind": "zvans", "date": TODAY.isoformat(), "ai_generated": "1",
        "summary": "Rediģēts MI kopsavilkums.", "next_step": "Nosūtīt programmu.",
    })
    row = query(crm_db, "SELECT ai_generated, approved_by FROM interactions"
                        " WHERE summary = 'Rediģēts MI kopsavilkums.'")
    assert row == [(1, ANNA)]
    assert "Ģenerēts ar MI, apstiprināja Anna Kalniņa" in client.get(f"/organizacijas/{ANNA_ORG}").text


def test_free_text_notes_are_not_stored(client, crm_db) -> None:
    act_as(client, ANNA)
    client.post(f"/organizacijas/{ANNA_ORG}/mijiedarbibas/jauna", data={
        "action": "save", "kind": "zvans", "date": TODAY.isoformat(), "notes": "SLEPENAS PIEZĪMES",
        "summary": "Īss kopsavilkums.",
    })
    assert b"SLEPENAS" not in crm_db.read_bytes()


# 21
def test_without_api_key_imitation_is_used(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(ai, "_claude", lambda text: pytest.fail("Claude nedrīkst izsaukt"))
    assert ai.kopsavilkums(NOTES).source == "imitācija"


# 22
def test_claude_failure_falls_back_with_notice(client, monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")

    def broken(text):
        raise TimeoutError

    monkeypatch.setattr(ai, "_claude", broken)
    act_as(client, ANNA)
    response = client.post(f"/organizacijas/{ANNA_ORG}/mijiedarbibas/jauna", data={
        "action": "generate", "kind": "zvans", "date": TODAY.isoformat(), "notes": NOTES,
    })
    assert "Claude šobrīd nav pieejams, tāpēc izmantota imitācija." in response.text


def test_claude_success_is_labelled(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(ai, "_claude", lambda text: ai.Suggestion("A. B.", "C.", "Claude"))
    assert ai.kopsavilkums(NOTES).source == "Claude"


# --- Pieprasījumi (F4) ----------------------------------------------------------------

# 23
def test_new_request_has_fixed_30_day_deadline(client, crm_db) -> None:
    act_as(client, ANNA)
    response = client.post(f"/organizacijas/{ANNA_ORG}/pieprasijumi/jauns", data={
        "title": "Jauns jautājums", "deadline": "2030-01-01",
    }, follow_redirects=False)
    assert response.status_code == 303
    rows = query(crm_db, "SELECT status, created_on, deadline FROM requests WHERE title = ?",
                 "Jauns jautājums")
    assert rows == [("jauns", TODAY.isoformat(), (TODAY + timedelta(days=30)).isoformat())]


# 24
def test_status_moves_only_forward_one_step(client, crm_db) -> None:
    act_as(client, ANNA)
    assert client.post("/pieprasijumi/1/statuss", data={"status": "atbildets"}).status_code == 400
    assert client.post("/pieprasijumi/1/statuss", data={"status": "darba"},
                       follow_redirects=False).status_code == 303
    assert client.post("/pieprasijumi/1/statuss", data={"status": "jauns"}).status_code == 400
    assert client.post("/pieprasijumi/1/statuss", data={"status": "atbildets"},
                       follow_redirects=False).status_code == 303
    assert query(crm_db, "SELECT status, answered_on FROM requests WHERE id = 1") == [
        ("atbildets", TODAY.isoformat())]


def test_other_employee_cannot_change_status(client) -> None:
    act_as(client, JANIS)
    assert client.post("/pieprasijumi/1/statuss", data={"status": "darba"}).status_code == 403


# 25
def test_overdue_requests_are_marked_with_text(client) -> None:
    act_as(client, ANNA)
    page = client.get("/pieprasijumi?kavetie=1").text
    assert "Konsultācija par ES fondu pieteikumu" in page
    assert '<span class="tag tag-late">Kavēts</span>' in page
    assert "Dalība reģionālajā forumā" not in page  # atbildēts
    assert "Kavēts" in client.get("/pieprasijumi/1").text


# --- Uzdevumi (F5) ----------------------------------------------------------------------

# 26
def test_task_must_be_linked(client) -> None:
    act_as(client, ANNA)
    data = {"title": "Uzdevums bez saites", "assignee_id": str(ANNA), "due": TODAY.isoformat()}
    response = client.post("/uzdevumi/jauns", data=data)
    assert response.status_code == 400
    assert "jābūt saistītam ar organizāciju vai pieprasījumu" in response.text
    ok = client.post("/uzdevumi/jauns", data=dict(data, request_id="1"), follow_redirects=False)
    assert ok.status_code == 303


# 27
def test_my_tasks_today_include_overdue_not_future(client) -> None:
    act_as(client, ANNA)
    page = client.get("/uzdevumi").text
    assert "Nosūtīt semināra programmu" in page  # šodien
    assert "Piezvanīt par līguma redakciju" in page  # kavēts
    assert "Kavēts" in page
    assert "Sagatavot atbildi par fondu pieteikumu" not in page  # pēc 3 dienām
    assert "Vēl 1 uzdevumi ar vēlāku termiņu." in page


# 28
def test_mark_task_done(client) -> None:
    act_as(client, ANNA)
    response = client.post("/uzdevumi/1/izpildits", follow_redirects=False)
    assert response.status_code == 303
    assert "Nosūtīt semināra programmu" not in client.get("/uzdevumi").text


def test_cannot_complete_someone_elses_task(client) -> None:
    act_as(client, JANIS)
    assert client.post("/uzdevumi/1/izpildits").status_code == 403


# --- Meklēšana (F6) -------------------------------------------------------------------

# 29
@pytest.mark.parametrize("q,expected,kind", [
    ("ŪDENS", 'AS "Ezermalas ūdens"', "Organizācija"),
    ("10000000004", 'SIA "Laivu darbnīca"', "Organizācija"),
    ("mežule", "Aija Mežule", "Kontaktpersona"),
    ("karlis2@", "Kārlis Dūmiņš", "Kontaktpersona"),
    ("forumā", "Dalība reģionālajā forumā", "Pieprasījums"),
])
def test_search_across_entities(client, q, expected, kind) -> None:
    act_as(client, ANNA)
    page = client.get("/meklet", params={"q": q}).text
    assert expected.replace('"', "&#34;") in page or expected in page
    assert f"<td>{kind}</td>" in page


# 30
def test_search_results_table_semantics(client) -> None:
    act_as(client, ANNA)
    page = client.get("/meklet?q=ezer").text
    assert "<caption" in page
    assert '<th scope="col">Tips</th>' in page
    assert '<th scope="row">' in page


# 31
def test_search_no_results(client) -> None:
    act_as(client, ANNA)
    page = client.get("/meklet?q=neesošs").text
    assert "Nekas netika atrasts vaicājumam „neesošs”" in page
    assert 'href="/organizacijas/jauna"' in page


# --- Pārskats (F7) ----------------------------------------------------------------------

# 32, 33
def test_report_has_chart_and_same_data_table(client) -> None:
    act_as(client, INESE)
    page = client.get("/parskats?no=2026-09-14&lidz=2026-10-14").text
    assert '<svg class="chart"' in page
    assert '<title id="chart-title">Mijiedarbības pa darbiniekiem</title>' in page
    assert '<desc id="chart-desc">' in page
    bars = re.findall(r"<path class=\"chart-bar\"[^>]*><title>([^<]+): (\d+)</title>", page)
    table = re.findall(r'<tr><th scope="row">([^<]+)</th><td>(\d+)</td></tr>', page)
    assert bars and bars == table[: len(bars)]
    assert "Kavētie pieprasījumi" in page and "Aktīvākās organizācijas" in page
    assert "Konsultācija par ES fondu pieteikumu" in page


# 34
def test_report_rejects_inverted_period(client) -> None:
    act_as(client, INESE)
    response = client.get("/parskats?no=2026-10-14&lidz=2026-09-01")
    assert response.status_code == 400
    assert "Perioda sākumam jābūt agrākam" in response.text


# --- Piekļūstamība (F8, N1) --------------------------------------------------------------

# 35
def test_layout_landmarks_and_skip_link(client) -> None:
    act_as(client, ANNA)
    page = client.get("/organizacijas").text
    assert '<a class="skip-link" href="#saturs">' in page
    for tag in ("<header", "<nav", '<main id="saturs"', "<footer"):
        assert tag in page
    # CR-6: JS ir uzlabojums; lapa sākas kā „no-js”, skripti nebloķē renderēšanu.
    assert page.startswith("<!doctype html>")
    assert '<html lang="lv" class="no-js">' in page
    assert '<script src="/static/crm.js" defer></script>' in page


# 38
def test_accessibility_statement_without_employee(client) -> None:
    response = client.get("/pieklustamiba")
    assert response.status_code == 200
    assert "Piekļūstamības paziņojums" in response.text


# --- Piekļuves žurnāls (N2) ------------------------------------------------------------

# 39
def test_viewing_and_editing_is_logged(client, crm_db) -> None:
    act_as(client, JANIS)
    client.get(f"/organizacijas/{ANNA_ORG}")
    act_as(client, ANNA)
    client.post(f"/organizacijas/{ANNA_ORG}/labot", data=dict(ORG, reg_nr="10000000001"))
    rows = query(crm_db, "SELECT employee_id, action, entity, organization_id FROM access_log")
    assert (JANIS, "skatīja", "organizācija", ANNA_ORG) in rows
    assert (ANNA, "mainīja", "organizācija", ANNA_ORG) in rows
    assert all(re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d", r[0])
               for r in query(crm_db, "SELECT at FROM access_log"))


# 40
def test_admin_filters_log(client) -> None:
    act_as(client, JANIS)
    client.get(f"/organizacijas/{ANNA_ORG}")
    act_as(client, ANNA)
    client.get(f"/organizacijas/{JANIS_ORG}")
    act_as(client, RUTA)
    page = client.get(f"/admin/zurnals?darbinieks={JANIS}").text
    rows = page.split("<tbody>")[1]
    assert "Jānis Ozols" in rows and "Anna Kalniņa" not in rows


# --- Tehniskie (N4) ----------------------------------------------------------------

# 42
def test_seed_data_counts(client, crm_db) -> None:
    counts = {t: query(crm_db, f"SELECT COUNT(*) FROM {t}")[0][0]
              for t in ("employees", "organizations", "contacts", "interactions")}
    assert counts == {"employees": 25, "organizations": 10, "contacts": 20, "interactions": 95}
    assert query(crm_db, "SELECT COUNT(*) FROM requests")[0][0] >= 39  # ≥ 3 × 13
    assert query(crm_db, "SELECT COUNT(*) FROM tasks")[0][0] >= 30  # ≥ 3 × 10
    roles = dict(query(crm_db, "SELECT role, COUNT(*) FROM employees GROUP BY role"))
    assert roles["vaditajs"] >= 1 and roles["administrators"] >= 1


def test_seed_runs_once(tmp_path) -> None:
    for _ in range(2):
        create_app(tmp_path / "u.db", crm_db_path=tmp_path / "c.db", today=lambda: TODAY)
    assert query(tmp_path / "c.db", "SELECT COUNT(*) FROM employees") == [(25,)]


def test_user_content_is_escaped(client) -> None:
    act_as(client, ANNA)
    response = client.post("/organizacijas/jauna", data=dict(ORG, name="<script>x</script>"),
                           follow_redirects=False)
    page = client.get(response.headers["location"]).text
    assert "<script>x</script>" not in page
    assert "&lt;script&gt;" in page


def test_root_redirects_to_crm(client) -> None:
    response = client.get("/", follow_redirects=False)
    assert response.headers["location"] == "/sakums"


# 43
def test_contract_describes_exactly_the_crm_routes(tmp_path) -> None:
    import yaml
    from fastapi.routing import APIRoute

    from app.crm import board, orgs, overview, work
    from tools.lint_contract import course_rule_errors

    def normalize(path: str) -> str:
        return re.sub(r"\{[^}]+\}", "{}", path)

    with (Path(__file__).resolve().parents[1] / "docs" / "openapi.yaml").open(encoding="utf-8") as f:
        document = yaml.safe_load(f)
    contract = {
        (method.upper(), normalize(path))
        for path, item in document["paths"].items()
        for method, op in item.items()
        if isinstance(op, dict) and "CRM" in op.get("tags", [])
    }
    routes = {("GET", "/")}
    for router in (overview.router, orgs.router, board.router, work.router):
        for route in router.routes:
            if isinstance(route, APIRoute):
                routes |= {(m, normalize(route.path)) for m in route.methods}
    assert contract == routes
    crm_errors = [e for e in course_rule_errors(document)
                  if not e.startswith(("GET /health", "POST /submissions", "GET /submissions"))]
    assert crm_errors == []


# --- Kopsavilkums (F9) ---------------------------------------------------------------

# 45
def test_dashboard_is_first_nav_item_and_tasks_page_remains(client) -> None:
    act_as(client, ANNA)
    page = client.get("/kopsavilkums").text
    nav = page.split('aria-label="Galvenā navigācija"')[1].split("</nav>")[0]
    links = re.findall(r'href="([^"]+)"', nav)
    assert links[:2] == ["/kopsavilkums", "/uzdevumi"]
    assert 'href="/kopsavilkums" aria-current="page"' in nav
    assert client.get("/uzdevumi").status_code == 200


# 46
def test_dashboard_tasks_block_and_done_returns_to_dashboard(client) -> None:
    act_as(client, ANNA)
    page = client.get("/kopsavilkums").text
    assert "Nosūtīt semināra programmu" in page
    assert "Piezvanīt par līguma redakciju" in page and "Kavēts" in page
    assert "Sagatavot atbildi par fondu pieteikumu" not in page
    response = client.post("/uzdevumi/1/izpildits", data={"return_to": "/kopsavilkums"},
                           follow_redirects=False)
    assert response.headers["location"] == "/kopsavilkums?izpildits=1"
    assert "Nosūtīt semināra programmu" not in client.get("/kopsavilkums").text


def test_done_ignores_foreign_return_target(client) -> None:
    act_as(client, ANNA)
    response = client.post("/uzdevumi/1/izpildits", data={"return_to": "https://example.com"},
                           follow_redirects=False)
    assert response.headers["location"] == "/uzdevumi?izpildits=1"


# 47
def test_dashboard_requests_overdue_first_then_upcoming(client) -> None:
    act_as(client, ANNA)
    page = client.get("/kopsavilkums").text
    block = page.split('id="requests-title"')[1].split("</section>")[0]
    overdue = block.index("Konsultācija par ES fondu pieteikumu")  # termiņš −10 d.
    upcoming = block.index("Prezentācijas materiāli konferencei")  # termiņš +4 d.
    assert overdue < upcoming
    assert "Kavēts" in block and "Drīz" in block
    assert "Pieredzes apmaiņas vizīte" not in block  # atbildēts
    assert "Datu apmaiņas vienošanās" not in block  # citas organizācijas


# 48
def test_dashboard_interactions_own_orgs_and_authored(client) -> None:
    act_as(client, INESE)
    client.post(f"/organizacijas/{JANIS_ORG}/mijiedarbibas/jauna", data={
        "action": "save", "kind": "zvans", "date": TODAY.isoformat(),
        "summary": "Vadītājas zvans.",
    })
    act_as(client, ANNA)
    client.post(f"/organizacijas/{ANNA_ORG}/mijiedarbibas/jauna", data={
        "action": "save", "kind": "zvans", "date": TODAY.isoformat(), "summary": "Annas zvans.",
    })
    old = (TODAY - timedelta(days=8)).isoformat()
    client.post(f"/organizacijas/{ANNA_ORG}/mijiedarbibas/jauna", data={
        "action": "save", "kind": "zvans", "date": old, "summary": "Sens zvans.",
    })
    block = client.get("/kopsavilkums").text.split('id="recent-title"')[1]
    assert "Annas zvans." in block
    assert "Sens zvans." not in block
    assert "Vadītājas zvans." not in block  # cita organizācija, cits autors
    assert "Pārrunāta sadarbība pavasara semināru ciklā" in block  # seed, Annas org., −1 d.


# 49
def test_manager_dashboard_shows_institution(client, crm_db) -> None:
    act_as(client, INESE)
    page = client.get("/kopsavilkums").text
    assert 'id="institution-title"' in page
    late = query(crm_db, "SELECT COUNT(*) FROM requests WHERE status != 'atbildets'"
                         " AND deadline < ?", TODAY.isoformat())[0][0]
    assert late >= 3
    assert re.search(rf"<dt>Kavēti pieprasījumi</dt><dd>{late}</dd>", page)
    assert "Visi kavētie pieprasījumi iestādē" in page
    assert "Semināra materiālu pieprasījums" in page  # Annas organizācija
    assert "Pēdējās mijiedarbības iestādē" in page
    assert "glabāšanas termiņu" not in page  # tikai administratoram


# 50
def test_admin_dashboard_shows_retention(client) -> None:
    act_as(client, RUTA)
    page = client.get("/kopsavilkums").text
    assert re.search(r"beigušos glabāšanas termiņu</dt><dd>2 <a href=\"/admin/glabasana\">", page)


# 51
def test_dashboard_empty_states(client) -> None:
    act_as(client, 22)  # Normunds Lapiņš: nav organizāciju, uzdevumu, mijiedarbību
    page = client.get("/kopsavilkums").text
    assert "Šodienai uzdevumu nav." in page
    assert "Tu neesi atbildīgais nevienā organizācijā." in page
    assert "Pēdējās 7 dienās mijiedarbību nav." in page


def test_dashboard_no_due_requests_in_own_orgs(client, crm_db) -> None:
    # Edgars Zariņš ir atbildīgais org. 9; visus tās pieprasījumus atzīmē kā atbildētus.
    with sqlite3.connect(crm_db) as conn:
        conn.execute("UPDATE requests SET status = 'atbildets' WHERE organization_id = 9")
    act_as(client, 6)
    page = client.get("/kopsavilkums").text
    assert "Manās organizācijās nav kavētu pieprasījumu" in page


# 52
def test_employee_dashboard_hides_institution_blocks(client) -> None:
    act_as(client, ANNA)
    page = client.get("/kopsavilkums").text
    assert 'id="institution-title"' not in page
    assert "Visi kavētie pieprasījumi iestādē" not in page
    assert "glabāšanas termiņu" not in page
    assert "Datu apmaiņas vienošanās" not in page


def test_dashboard_requires_employee(client) -> None:
    response = client.get("/kopsavilkums", follow_redirects=False)
    assert response.headers["location"] == "/sakums"
