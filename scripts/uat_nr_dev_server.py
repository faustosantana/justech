"""Servidor UAT DEV — Motor Relaciones Numéricas (solo lectura histórica).

Monta auth + numeric-relations (+ lottery list/defaults mínimos) contra jaios_lottery_dev.
No despliega a Producción. No toca sync.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure lottery module on
os.environ.setdefault("LOTTERY_MODULE_ENABLED", "true")

from app.api.v1 import auth, lottery, lottery_numeric_relations  # noqa: E402
from app.api.v1 import lottery_ai_admin  # noqa: E402
from app.api.v1 import company_context  # noqa: E402

app = FastAPI(title="JAIOS Lottery NR UAT DEV", version="phase-f")
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


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "service": "jaios-nr-uat-dev", "phase": "F"}
