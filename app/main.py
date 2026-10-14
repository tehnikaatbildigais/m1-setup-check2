"""Palaišana: `make run` (uvicorn app.main:app)."""

import logging

from .application import create_app

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s · %(message)s")

app = create_app()
