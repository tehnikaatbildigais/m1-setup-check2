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
    ("/admin/lomas", 25),
    ("/admin/glabasana", 25),
    ("/admin/zurnals", 25),
    ("/pieklustamiba", None),
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
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as playwright:
        try:
            instance = playwright.chromium.launch()
        except Exception as exc:  # pārlūks nav lejupielādēts
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
    page.goto(base_url + path)
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
    for _ in range(40):
        page.keyboard.press("Tab")
        if page.evaluate("document.activeElement.getAttribute('href')") == "/organizacijas/1":
            break
    page.keyboard.press("Enter")
    page.wait_for_url("**/organizacijas/1")
    page.close()
