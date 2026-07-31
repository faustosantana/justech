#!/usr/bin/env python3
"""Build Routing200 suite — local/workspace/deterministic routes (NOT Shadow denominator)."""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "ROUTING200.json"

cases = []
# greetings / social
for i, u in enumerate(
    [
        "Hola",
        "Buenos días",
        "Gracias",
        "Ok",
        "Perfecto",
        "Entendido",
        "Dale",
        "Listo",
        "Sí",
        "No",
    ],
    1,
):
    cases.append({"id": f"R{i:03d}", "category": "social", "user": u, "setup": [], "expect": {"huawei": False}})

# workspace / table page commands
for i in range(11, 61):
    cases.append(
        {
            "id": f"R{i:03d}",
            "category": "workspace_table",
            "user": "muéstrame la tabla" if i % 2 == 0 else "página 1 de la tabla",
            "setup": ["¿Han coincidido el 07 y el 38 el mismo día?"],
            "expect": {"huawei": False, "workspace": True},
        }
    )

# exports
for i in range(61, 81):
    cases.append(
        {
            "id": f"R{i:03d}",
            "category": "export",
            "user": "exporta a excel" if i % 2 else "descargar csv",
            "setup": ["¿Han coincidido el 12 y el 50 el mismo día?"],
            "expect": {"huawei": False},
        }
    )

# pure attribute (local skip)
for i, u in enumerate(
    [
        "¿Cuántas veces?",
        "¿Cuándo fue?",
        "¿Última vez?",
        "¿En qué posición?",
        "¿En qué lotería?",
        "¿Cuáles fueron esas fechas?",
        "las tres anteriores",
        "¿Cuándo salió?",
        "última",
        "¿Cuántas?",
    ],
    81,
):
    cases.append(
        {
            "id": f"R{i:03d}",
            "category": "attribute_local",
            "user": u,
            "setup": ["¿Han coincidido el 14 y el 54 el mismo día? Interpreta."],
            "expect": {"huawei": False},
        }
    )

# pad to 200 with more social/deterministic
while len(cases) < 200:
    n = len(cases) + 1
    cases.append(
        {
            "id": f"R{n:03d}",
            "category": "social_pad",
            "user": "gracias" if n % 2 else "ok",
            "setup": [],
            "expect": {"huawei": False},
        }
    )

assert len(cases) == 200
OUT.write_text(
    json.dumps(
        {
            "suite": "ROUTING200",
            "version": "1.0",
            "purpose": "Verify Studio does not intervene on non-Huawei routes",
            "n": 200,
            "cases": cases,
        },
        indent=2,
        ensure_ascii=False,
    )
    + "\n"
)
print("wrote", OUT, "n", len(cases))
