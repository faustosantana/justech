"""Servidor Release Candidate DEV — Motor Relaciones Numéricas.

Misma superficie que UAT Fase F + fix multi-lotería Fase G.
Apunta a jaios_lottery_dev. No toca Producción ni sync.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

os.environ.setdefault("LOTTERY_MODULE_ENABLED", "true")
os.environ.setdefault("LOTTERY_SYNC_ENABLED", "false")
os.environ.setdefault("LOTTERY_SYNC_WRITE_ENABLED", "false")

from app.api.v1 import auth, lottery, lottery_numeric_relations  # noqa: E402
from app.api.v1 import lottery_ai_admin  # noqa: E402
from app.api.v1 import company_context  # noqa: E402

app = FastAPI(title="JAIOS Lottery NR RC DEV", version="phase-g-rc")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3011",
        "http://127.0.0.1:3011",
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


@app.get("/api/v1/health")
async def health():
    return {
        "status": "ok",
        "service": "jaios-nr-rc-dev",
        "phase": "G",
        "module": "lottery.numeric_relations",
    }
