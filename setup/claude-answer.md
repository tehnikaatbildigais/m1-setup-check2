# Explain what make test does

*Answer from Claude Code (Opus 5.5) running in this repository's GitHub Codespace, 2026-10-14.*

`make test` runs the project's full automated test suite. In the `Makefile` the target is a single command:

```make
test:
	pytest -q
```

## What happens when you run it

1. **pytest starts in quiet mode** (`-q`): one character per test (`.` = passed, `s` = skipped, `F` = failed), then a summary line such as `282 passed`.
2. **`pytest.ini` configures discovery:**
   - `pythonpath = .` puts the repository root on the import path, so tests can `import app...` and `tools...`.
   - `python_files = test_*.py a11y_check.py` collects the usual `test_*.py` files and also the browser accessibility check, whose name doesn't start with `test_`.
3. **`tests/conftest.py` isolates the environment.** Before every test it removes `AUTH_DB_PATH`, `CRM_DB_PATH`, `PUBLIC_BASE_URL` and `ANTHROPIC_API_KEY`. Tests therefore never write to the real `data/` databases or call the Claude API; each test creates its own temporary SQLite databases.
4. **The test files run:**

| File | What it checks |
|---|---|
| `tests/test_smoke.py` | `docs/openapi.yaml` loads and required project files exist |
| `tests/test_auth.py` | User accounts (CR-4): registration, login, lockout after 3 failures, password reset |
| `tests/test_crm.py` | CRM (CR-5, CR-7): organizations, contacts, interactions, requests, tasks, search, report, roles, GDPR deletion, accessibility statement, and that `docs/openapi.yaml` matches the real routes |
| `tests/test_board.py` | Task allocation board (CR-6) |
| `tests/a11y_check.py` | Accessibility in a real Chromium browser: axe-core on every page, keyboard use, 320 px layout, text spacing, working without JavaScript |

5. **The accessibility check is skipped if Playwright or Chromium is missing.** This is the case in CI and in a fresh Codespace, which shows as `1 skipped`. To run it, use `make install-dev`. With `A11Y_REQUIRED=1`, a missing browser makes the run fail instead of skipping.

## Result

- The exit code is `0` if everything passes and non-zero if any test fails, so CI (`.github/workflows/ci.yml`) marks the run red on any failure.
- `make test` does **not** validate the API contract against the course rules. That is `make lint-contract`.
- It does **not** check the Codespace setup. That is `make verify-setup`, which also needs this file.
