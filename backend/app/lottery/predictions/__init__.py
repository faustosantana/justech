"""Prediction motor registry — orchestration only; no new math."""

from __future__ import annotations

from typing import Any

# Canonical catalog. implementation_ref=None ⇒ NOT_IMPLEMENTED (cannot activate).
MOTOR_CATALOG: list[dict[str, Any]] = [
    {
        "key": "numeric_relations",
        "name": "Relaciones Numéricas",
        "description": (
            "Presenta compañeros fortalecidos por el Motor de Relaciones Numéricas "
            "sobre historial real (draw_id). No es una fórmula predictiva nueva."
        ),
        "status": "ACTIVO",
        "implemented": True,
        "implementation_ref": "app.lottery.numeric_relations",
        "version": "1.0.0",
        "priority": 10,
        "weight": 1.0,
        "docs": "docs/lottery/ADR_LOTTERY_NUMERIC_RELATIONS_MOTOR.md",
    },
    {
        "key": "frequencies",
        "name": "Frecuencias",
        "description": "Motor de frecuencias (no implementado en Control Center).",
        "status": "NO_IMPLEMENTADO",
        "implemented": False,
        "implementation_ref": None,
        "version": None,
        "priority": 20,
        "weight": None,
        "docs": None,
    },
    {
        "key": "absences",
        "name": "Ausencias",
        "description": "Motor de ausencias (no implementado).",
        "status": "NO_IMPLEMENTADO",
        "implemented": False,
        "implementation_ref": None,
        "version": None,
        "priority": 30,
        "weight": None,
        "docs": None,
    },
    {
        "key": "cycles",
        "name": "Ciclos",
        "description": "Motor de ciclos (no implementado).",
        "status": "NO_IMPLEMENTADO",
        "implemented": False,
        "implementation_ref": None,
        "version": None,
        "priority": 40,
        "weight": None,
        "docs": None,
    },
    {
        "key": "trends",
        "name": "Tendencias",
        "description": "Motor de tendencias (no implementado).",
        "status": "NO_IMPLEMENTADO",
        "implemented": False,
        "implementation_ref": None,
        "version": None,
        "priority": 50,
        "weight": None,
        "docs": None,
    },
    {
        "key": "simulation",
        "name": "Simulación",
        "description": "Simulación (no implementado).",
        "status": "NO_IMPLEMENTADO",
        "implemented": False,
        "implementation_ref": None,
        "version": None,
        "priority": 60,
        "weight": None,
        "docs": None,
    },
    {
        "key": "consensus",
        "name": "Consenso",
        "description": "Consenso multi-motor (no implementado).",
        "status": "NO_IMPLEMENTADO",
        "implemented": False,
        "implementation_ref": None,
        "version": None,
        "priority": 70,
        "weight": None,
        "docs": None,
    },
]

ALLOWED_STATUS = {
    "ACTIVO",
    "INACTIVO",
    "NO_IMPLEMENTADO",
    "ERROR",
    "EN_MANTENIMIENTO",
}

PREDICTION_DISCLAIMER = (
    "Este resultado es una señal histórica producida por el Motor de Relaciones "
    "Numéricas. No constituye garantía de resultado."
)


def catalog_by_key() -> dict[str, dict[str, Any]]:
    return {m["key"]: dict(m) for m in MOTOR_CATALOG}
