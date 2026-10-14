"""FastAPI lietotnes izveide. Testi izsauc `create_app` ar pagaidu datubāzi."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import auth, pages
from .db import Database
from .errors import register_error_handlers

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "users.db"


def create_app(
    db_path: Path | str | None = None, clock: Callable[[], float] = time.time
) -> FastAPI:
    app = FastAPI(title="Ezermalas pieteikumu sistēma", version="0.1.0")
    app.state.db = Database(db_path or os.environ.get("AUTH_DB_PATH", DEFAULT_DB_PATH))
    app.state.clock = clock
    register_error_handlers(app)
    app.include_router(auth.router)
    app.include_router(pages.router)
    app.mount("/static", StaticFiles(directory=pages.STATIC_DIR), name="static")
    return app
