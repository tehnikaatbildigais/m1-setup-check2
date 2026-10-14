"""Kopīgā testu vide: testi nekad neizmanto izstrādātāja vides mainīgos."""

import pytest

ISOLATED_ENV = ("AUTH_DB_PATH", "CRM_DB_PATH", "PUBLIC_BASE_URL", "ANTHROPIC_API_KEY")


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch):
    # Citādi, piem., eksportēts CRM_DB_PATH liktu testiem rakstīt īstajā data/crm.db.
    for name in ISOLATED_ENV:
        monkeypatch.delenv(name, raising=False)
