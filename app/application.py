"""FastAPI lietotnes izveide. Testi izsauc `create_app` ar pagaidu datubāzi."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from datetime import date
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import auth, pages
from .crm import board, orgs, overview, schema, work
from .db import Database
from .errors import register_error_handlers

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEFAULT_DB_PATH = DATA_DIR / "users.db"
DEFAULT_CRM_DB_PATH = DATA_DIR / "crm.db"


def create_app(
    db_path: Path | str | None = None,
    clock: Callable[[], float] = time.time,
    crm_db_path: Path | str | None = None,
    today: Callable[[], date] = date.today,
) -> FastAPI:
    app = FastAPI(title="Ezermalas pieteikumu sistēma", version="0.1.0")
    app.state.db = Database(db_path or os.environ.get("AUTH_DB_PATH", DEFAULT_DB_PATH))
    app.state.clock = clock
    if crm_db_path is None:
        # Secība: arguments → CRM_DB_PATH → blakus norādītajai lietotāju DB (CR-4 testi)
        # → noklusējums.
        crm_db_path = os.environ.get("CRM_DB_PATH") or (
            Path(db_path).with_name("crm.db") if db_path else DEFAULT_CRM_DB_PATH
        )
    app.state.crm_db = Database(crm_db_path, schema.SCHEMA)
    app.state.today = today
    with app.state.crm_db.transaction() as conn:
        schema.seed(conn, today())
    register_error_handlers(app)
    app.include_router(auth.router)
    app.include_router(pages.router)
    # board pirms work, lai /uzdevumi/sadale nesajaucas ar citiem /uzdevumi/... maršrutiem.
    for router in (overview.router, orgs.router, board.router, work.router):
        app.include_router(router)
    app.mount("/static", StaticFiles(directory=pages.STATIC_DIR), name="static")
    return app
