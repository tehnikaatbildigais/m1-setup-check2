"""CR-5 · N1 pieejamības pārbaude galvenajā ceļā ar axe-core un Playwright.

Pārbauda: axe-core bez critical/serious pārkāpumiem (WCAG 2.2 A/AA), nav horizontālās
ritināšanas 320 px platumā un 200 % mērogā, pirmais Tab fokuss ir saite "Pāriet uz saturu".
Ja Playwright vai pārlūks nav uzstādīts, tests tiek izlaists (CI paliek zaļš).
Uzstādīšana: pip install -r requirements-dev.txt && playwright install chromium
"""

from __future__ import annotations

import socket
import threading
import time
from datetime import date
from pathlib import Path

import pytest

import os

# A11Y_REQUIRED=1 (piem., CI ar uzstādītu pārlūku): trūkstošs Playwright/Chromium ir kļūda,
# nevis klusa izlaišana, lai N1 pārbaude nepazustu nemanot.
REQUIRED = os.environ.get("A11Y_REQUIRED") == "1"
if REQUIRED:
    import playwright.sync_api as sync_api
else:
    sync_api = pytest.importorskip("playwright.sync_api")
uvicorn = pytest.importorskip("uvicorn")

from app.application import create_app  # noqa: E402

AXE = Path(__file__).parent / "vendor" / "axe.min.js"
AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]
TODAY = date(2026, 10, 14)

# Galvenais ceļš: darbinieka izvēle → kopsavilkums (F9) → uzdevumi → organizācijas → kartīte → formas → pārskats.
MAIN_PATH = [
    ("/sakums", None),
    ("/kopsavilkums", 1),
    ("/kopsavilkums", 23),
    ("/kopsavilkums", 25),
    ("/uzdevumi", 1),
    ("/organizacijas", 1),
    ("/organizacijas/1", 1),
    ("/organizacijas/1/kontakti/jauns", 1),
    ("/organizacijas/1/mijiedarbibas/jauna", 1),
    ("/pieprasijumi", 1),
    ("/pieprasijumi/1", 1),
    ("/uzdevumi/jauns", 1),
    ("/meklet?q=ezer", 1),
    ("/meklet?q=neesošs", 1),
    ("/parskats", 23),
    ("/uzdevumi/sadale", 23),
    ("/admin/lomas", 25),
    ("/admin/glabasana", 25),
    ("/admin/zurnals", 25),
    ("/pieklustamiba", None),
    ("/admin/atsauksmes", 25),
    ("/login", None),
    ("/register", None),
    ("/password-reset", None),
    ("/password-reset/confirm?token=nav", None),
]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def base_url(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("a11y")
    app = create_app(tmp / "users.db", crm_db_path=tmp / "crm.db", today=lambda: TODAY)
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(200):
        if server.started:
            break
        time.sleep(0.05)
    assert server.started, f"Testa serveris neieslēdzās uz porta {port}"
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as playwright:
        try:
            instance = playwright.chromium.launch()
        except Exception as exc:  # pārlūks nav lejupielādēts vai trūkst sistēmas bibliotēku
            if REQUIRED:
                pytest.fail(f"Chromium nav pieejams, bet A11Y_REQUIRED=1: {exc}")
            pytest.skip(f"Chromium nav pieejams: {exc}")
        yield instance
        instance.close()


def _page_as(browser, base_url, employee_id, **context):
    page = browser.new_page(**context)
    if employee_id is not None:
        page.context.add_cookies([{"name": "crm_darbinieks", "value": str(employee_id),
                                   "url": base_url}])
    return page


def _axe(page) -> list[dict]:
    page.add_script_tag(path=str(AXE))
    result = page.evaluate(
        "tags => axe.run(document, {runOnly: {type: 'tag', values: tags}})", AXE_TAGS
    )
    return [
        {"id": v["id"], "impact": v["impact"], "nodes": [n["target"] for n in v["nodes"]][:3]}
        for v in result["violations"]
    ]


@pytest.mark.parametrize("path,employee_id", MAIN_PATH)
@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_axe_no_critical_or_serious(browser, base_url, path, employee_id, scheme) -> None:
    page = _page_as(browser, base_url, employee_id, color_scheme=scheme)
    response = page.goto(base_url + path)
    # Kļūdas lapa arī var būt bez axe pārkāpumiem; pārbaudām, ka testēta īstā lapa.
    assert response.status == 200, (path, response.status)
    violations = _axe(page)
    page.close()
    blocking = [v for v in violations if v["impact"] in ("critical", "serious")]
    assert not blocking, blocking


def test_axe_on_form_with_errors(browser, base_url) -> None:
    page = _page_as(browser, base_url, 1)
    page.goto(base_url + "/organizacijas/jauna")
    page.fill("#f-reg_nr", "123")
    page.click("form.narrow button[type=submit]")
    page.wait_for_selector(".error-summary")
    assert page.evaluate("document.activeElement.className") == "error-summary"
    violations = [v for v in _axe(page) if v["impact"] in ("critical", "serious")]
    page.close()
    assert not violations, violations


@pytest.mark.parametrize("path,employee_id", MAIN_PATH)
@pytest.mark.parametrize("width", [320, 640])  # 640 px ≈ 1280 px logs 200 % mērogā
def test_no_horizontal_page_scroll(browser, base_url, path, employee_id, width) -> None:
    page = _page_as(browser, base_url, employee_id, viewport={"width": width, "height": 800})
    page.goto(base_url + path)
    scroll_width = page.evaluate("document.documentElement.scrollWidth")
    page.close()
    assert scroll_width <= width


def test_first_tab_reaches_skip_link_and_main(browser, base_url) -> None:
    page = _page_as(browser, base_url, 1)
    page.goto(base_url + "/organizacijas")
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.textContent") == "Pāriet uz saturu"
    page.keyboard.press("Enter")
    assert page.evaluate("document.activeElement.id") == "saturs"
    page.close()


def test_keyboard_only_main_path(browser, base_url) -> None:
    """Izvēlas darbinieku un atver organizāciju tikai ar tastatūru."""
    page = browser.new_page()
    page.goto(base_url + "/sakums")
    page.focus("#f-employee_id")
    page.keyboard.press("ArrowDown")  # pirmais darbinieks
    page.keyboard.press("Tab")
    page.keyboard.press("Enter")
    page.wait_for_url("**/kopsavilkums")
    page.goto(base_url + "/organizacijas")
    for _ in range(60):
        page.keyboard.press("Tab")
        if page.evaluate("document.activeElement.getAttribute('href')") == "/organizacijas/1":
            break
    else:
        pytest.fail("Saite /organizacijas/1 nav sasniedzama ar Tab 60 soļos")
    page.keyboard.press("Enter")
    page.wait_for_url("**/organizacijas/1")
    page.close()


# --- CR-6: ietvars un uzdevumu sadales tāfele ---------------------------------------------

def _other_shown_column(page, task_id) -> str:
    """Redzama kolonna, kas nav kartītes pašreizējā (testi nav atkarīgi no secības)."""
    return page.evaluate(
        """id => [...document.querySelectorAll('.board-column')].map(c => c.dataset.employee)
              .find(e => e !== document.getElementById('uzdevums-' + id)
                                 .closest('.board-column').dataset.employee)""",
        task_id,
    )


def _card_column(page, task_id: int) -> str:
    return page.evaluate(
        "id => document.getElementById('uzdevums-' + id).closest('.board-column').dataset.employee",
        task_id,
    )


def test_board_drag_and_drop_reassigns(browser, base_url) -> None:
    page = _page_as(browser, base_url, 23)
    page.goto(base_url + "/uzdevumi/sadale")
    # Blakus esošas kolonnas, lai vilkšana nav atkarīga no horizontālās ritināšanas.
    columns = page.evaluate("[...document.querySelectorAll('.board-column')].map(c => c.dataset.employee)")
    source = page.locator(f'.board-column[data-employee="{columns[0]}"] .task-card').first
    task_id = source.get_attribute("data-task")
    target = page.locator(f'.board-column[data-employee="{columns[1]}"]')
    # Nomet pie kolonnas galvenes: garām kolonnām centrs var būt zem redzamās daļas.
    source.drag_to(target, target_position={"x": 40, "y": 30})
    page.wait_for_function("document.getElementById('live').textContent.includes('Uzdevums nodots')")
    assert _card_column(page, task_id) == columns[1]
    page.reload()
    assert _card_column(page, task_id) == columns[1]  # saglabāts serverī
    page.close()


def test_board_failed_move_returns_card(browser, base_url) -> None:
    page = _page_as(browser, base_url, 23)
    page.route("**/izpilditajs", lambda route: route.fulfill(
        status=500, content_type="application/json",
        body='{"error": {"code": "INTERNAL_ERROR", "message": "x"}}'))
    page.goto(base_url + "/uzdevumi/sadale")
    before = _card_column(page, 9)
    # Tas pats atgriešanas ceļš kā vilkšanai (reassign()); forma neatkarīga no kolonnu novietojuma.
    page.select_option("#reassign-9", _other_shown_column(page, 9))
    page.locator("#uzdevums-9 form.reassign button").click()
    page.wait_for_function("document.getElementById('live').textContent.includes('Kartīte atgriezta')")
    assert _card_column(page, 9) == before
    assert page.input_value("#reassign-9") == before
    page.close()


def test_board_keyboard_reassign_keeps_focus(browser, base_url) -> None:
    page = _page_as(browser, base_url, 25)
    page.goto(base_url + "/uzdevumi/sadale")
    target = _other_shown_column(page, 10)
    page.focus("#reassign-10")
    page.select_option("#reassign-10", target)
    page.keyboard.press("Tab")
    page.keyboard.press("Enter")
    page.wait_for_function("document.getElementById('live').textContent.includes('Uzdevums nodots')")
    assert _card_column(page, 10) == target
    assert page.evaluate("document.activeElement.id") == "reassign-10"
    open_count = page.locator(f'.board-column[data-employee="{target}"] [data-open]').inner_text()
    assert int(open_count) == page.locator(f'.board-column[data-employee="{target}"] .task-card').count()
    page.close()


def test_add_menu_keyboard(browser, base_url) -> None:
    page = _page_as(browser, base_url, 1)
    page.goto(base_url + "/organizacijas")
    page.focus(".add-menu summary")
    page.keyboard.press("Enter")
    page.wait_for_function("document.activeElement.getAttribute('href') === '/organizacijas/jauna'")
    page.keyboard.press("ArrowDown")
    assert page.evaluate("document.activeElement.getAttribute('href')") == "/uzdevumi/jauns"
    page.keyboard.press("Escape")
    assert page.evaluate("document.querySelector('.add-menu').open") is False
    assert page.evaluate("document.activeElement.tagName") == "SUMMARY"
    page.close()


def test_mobile_menu_toggle(browser, base_url) -> None:
    page = _page_as(browser, base_url, 1, viewport={"width": 375, "height": 800})
    page.goto(base_url + "/organizacijas")
    assert not page.locator("#main-nav").is_visible()
    page.click(".menu-toggle")
    assert page.locator("#main-nav").is_visible()
    assert page.get_attribute(".menu-toggle", "aria-expanded") == "true"
    page.close()


def test_without_javascript_everything_still_works(browser, base_url) -> None:
    context = browser.new_context(java_script_enabled=False, viewport={"width": 375, "height": 800})
    context.add_cookies([{"name": "crm_darbinieks", "value": "23", "url": base_url}])
    page = context.new_page()
    page.goto(base_url + "/organizacijas")
    assert page.locator("#main-nav").is_visible()  # bez JS izvēlne vienkārši redzama
    page.click(".add-menu summary")
    page.click(".menu-list a[href='/organizacijas/jauna']")
    page.fill("#f-reg_nr", "123")
    page.click("form.narrow button[type=submit]")
    assert page.locator(".error-summary").is_visible()
    page.goto(base_url + "/uzdevumi/sadale")
    task_id = page.locator(".task-card").first.get_attribute("data-task")
    current = page.input_value(f"#reassign-{task_id}")
    page.select_option(f"#reassign-{task_id}", "1" if current != "1" else "2")
    page.locator(f"#uzdevums-{task_id} form.reassign button").click()
    page.wait_for_url(f"**/uzdevumi/sadale?nodots={task_id}*")
    assert "Uzdevums nodots:" in page.content()
    context.close()


# --- Audits 2026-10-14 ----------------------------------------------------------------

def test_mobile_nav_visible_when_crm_js_fails(browser, base_url) -> None:
    page = _page_as(browser, base_url, 1, viewport={"width": 375, "height": 800})
    page.route("**/static/crm.js", lambda route: route.abort())
    page.goto(base_url + "/organizacijas")
    assert page.locator("#main-nav").is_visible()
    assert not page.locator(".menu-toggle").is_visible()
    page.close()


def test_add_menu_closes_when_focus_leaves(browser, base_url) -> None:
    page = _page_as(browser, base_url, 1)
    page.goto(base_url + "/organizacijas")
    page.focus(".add-menu summary")
    page.keyboard.press("Enter")
    page.wait_for_function("document.activeElement.getAttribute('href') === '/organizacijas/jauna'")
    page.keyboard.press("Tab")
    page.keyboard.press("Tab")
    page.wait_for_function("!document.querySelector('.add-menu').open")
    page.close()


def test_add_menu_stays_on_screen_on_mobile(browser, base_url) -> None:
    page = _page_as(browser, base_url, 1, viewport={"width": 320, "height": 800})
    page.goto(base_url + "/organizacijas")
    page.click(".add-menu summary")
    box = page.locator(".menu-list").bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= 320
    page.close()


def test_board_removes_card_of_task_done_elsewhere(browser, base_url) -> None:
    page = _page_as(browser, base_url, 23)
    page.goto(base_url + "/uzdevumi/sadale")
    task_id = page.locator(".task-card").last.get_attribute("data-task")
    # Uzdevumu atzīmē kā izpildītu citā „cilnē” (tieši serverim).
    page.request.post(f"{base_url}/uzdevumi/{task_id}/izpildits")
    current = page.input_value(f"#reassign-{task_id}")
    other = "1" if current != "1" else "2"
    page.select_option(f"#reassign-{task_id}", other)
    page.locator(f"#uzdevums-{task_id} form.reassign button").click()
    page.wait_for_function("document.getElementById('live').textContent.includes('jau ir izpildīts')")
    assert page.locator(f"#uzdevums-{task_id}").count() == 0
    page.close()



# --- CR-7: atkārtota piekļūstamības pārbaude ------------------------------------------

@pytest.mark.parametrize("path,fill", [
    ("/register", {"#email": "x@"}),
    ("/login", {"#login": "neviens", "#password": "nepareiza"}),
])
def test_cr4_focus_moves_to_error(browser, base_url, path, fill) -> None:
    page = browser.new_page()
    page.goto(base_url + path)
    for selector, value in fill.items():
        page.fill(selector, value)
    page.click("button[type=submit]")
    page.wait_for_function("document.activeElement !== document.body && document.activeElement.tagName !== 'BUTTON'")
    focused = page.evaluate("document.activeElement.getAttribute('aria-invalid') || document.activeElement.className")
    assert focused in ("true", "form-error")
    page.close()


def test_text_spacing_does_not_clip(browser, base_url) -> None:
    """WCAG 1.4.12: palielinātas atstarpes nenogriež saturu un nerada horizontālu ritināšanu."""
    spacing = ("*{line-height:1.5!important;letter-spacing:.12em!important;"
               "word-spacing:.16em!important}p{margin-bottom:2em!important}")
    for path, employee_id in MAIN_PATH:
        page = _page_as(browser, base_url, employee_id)
        page.goto(base_url + path)
        page.add_style_tag(content=spacing)
        clipped = page.evaluate("""() => [...document.querySelectorAll('body *')].filter(e => {
            const cs = getComputedStyle(e);
            if (cs.display === 'none' || e.classList.contains('visually-hidden')) return false;
            return /(hidden|clip)/.test(cs.overflowX + cs.overflowY) && e.clientHeight > 0 &&
                   (e.scrollWidth > e.clientWidth + 1 || e.scrollHeight > e.clientHeight + 1);
        }).map(e => e.tagName + '.' + e.className)""")
        hscroll = page.evaluate("document.documentElement.scrollWidth > innerWidth")
        page.close()
        assert not clipped and not hscroll, (path, clipped)


def test_no_keyboard_trap(browser, base_url) -> None:
    for path, employee_id in [("/kopsavilkums", 23), ("/uzdevumi/sadale", 23), ("/login", None)]:
        page = _page_as(browser, base_url, employee_id)
        page.goto(base_url + path)
        for _ in range(400):
            page.keyboard.press("Tab")
            if page.evaluate("document.activeElement.getAttribute('href')") == "/pieklustamiba":
                break
        else:
            pytest.fail(f"{path}: kājenes saite nav sasniedzama ar Tab")
        page.close()


def test_feedback_form_without_javascript(browser, base_url) -> None:
    context = browser.new_context(java_script_enabled=False)
    page = context.new_page()
    page.goto(base_url + "/pieklustamiba")
    page.fill("#f-description", "Tests bez JS")
    page.click("form[action='/pieklustamiba'] button[type=submit]")
    page.wait_for_url("**/pieklustamiba?nosutits=1*")
    assert "Paldies, ziņojums nosūtīts" in page.content()
    context.close()
