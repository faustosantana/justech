"""Servidor DEV J-9 — Historial del Número + APIs históricas.

Apunta exclusivamente a jaios_lottery_dev. No toca Producción ni sync.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

os.environ.setdefault("LOTTERY_MODULE_ENABLED", "true")
os.environ.setdefault("LOTTERY_SYNC_ENABLED", "false")
os.environ.setdefault("LOTTERY_SYNC_WRITE_ENABLED", "false")
os.environ.setdefault("APP_ENV", "development")

from app.api.v1 import auth, company_context, lottery, lottery_ai_admin  # noqa: E402
from app.api.v1 import lottery_numeric_relations, lottery_nr_historical  # noqa: E402

app = FastAPI(title="JAIOS Lottery NR J-9 DEV", version="j9-historial-numero")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3011",
        "http://127.0.0.1:3011",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(company_context.router, prefix="/api/v1")
app.include_router(lottery.router, prefix="/api/v1")
app.include_router(lottery_numeric_relations.router, prefix="/api/v1")
app.include_router(lottery_ai_admin.router, prefix="/api/v1")
app.include_router(lottery_nr_historical.router, prefix="/api/v1")


@app.get("/api/v1/health")
async def health():
    db = os.environ.get("DATABASE_URL", "")
    safe_db = "jaios_lottery_dev" if "jaios_lottery_dev" in db else "UNSET_OR_NON_DEV"
    return {
        "status": "ok",
        "service": "jaios-nr-j9-dev",
        "phase": "J-9",
        "module": "lottery.numeric_relations.historial",
        "database_target": safe_db,
        "production_forbidden": True,
    }
