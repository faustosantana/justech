"""Identidad estable de proveedores e instituciones (histórico DGCP).

Prioridad de resolución (sin fusión agresiva):
1. RNC exacto (si aparece en payload)
2. RPE exacto
3. Código unidad de compra (institución)
4. Nombre normalizado solo como clave de sugerencia (confidence menor)
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any


def normalize_party_name(name: str | None) -> str:
    if not name:
        return ""
    text = unicodedata.normalize("NFKD", name.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.replace(",", " ").replace(".", " ")
    text = re.sub(r"\bs\.?\s*r\.?\s*l\.?\b", "srl", text)
    text = re.sub(r"\bs\.?\s*a\.?\b", "sa", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_rnc_from_payload(raw: dict[str, Any] | None) -> str | None:
    if not isinstance(raw, dict):
        return None
    candidates = [
        raw.get("rnc"),
        raw.get("RNC"),
        raw.get("cedula_rnc"),
        (raw.get("extra") or {}).get("rnc") if isinstance(raw.get("extra"), dict) else None,
        (raw.get("extra") or {}).get("RNC") if isinstance(raw.get("extra"), dict) else None,
    ]
    for c in candidates:
        if c is None:
            continue
        digits = re.sub(r"\D", "", str(c))
        if len(digits) >= 9:
            return digits
    return None


def supplier_stable_key(*, rpe: str | None, name: str | None, rnc: str | None = None) -> str:
    rnc_digits = re.sub(r"\D", "", str(rnc)) if rnc else ""
    if len(rnc_digits) >= 9:
        return f"rnc-{rnc_digits}"
    rpe_clean = re.sub(r"[^0-9A-Za-z]", "", str(rpe or ""))
    if rpe_clean:
        return f"rpe-{rpe_clean}"
    norm = normalize_party_name(name)
    if not norm:
        return "unknown"
    digest = hashlib.sha1(norm.encode("utf-8")).hexdigest()[:10]
    slug = re.sub(r"[^a-z0-9]+", "-", norm)[:48].strip("-") or "x"
    return f"name-{slug}-{digest}"


def institution_stable_key(*, code: str | int | None, name: str | None) -> str:
    if code is not None and str(code).strip():
        code_clean = re.sub(r"[^0-9A-Za-z_-]", "", str(code).strip())
        if code_clean:
            return f"code-{code_clean}"
    norm = normalize_party_name(name)
    if not norm:
        return "unknown"
    digest = hashlib.sha1(norm.encode("utf-8")).hexdigest()[:10]
    slug = re.sub(r"[^a-z0-9]+", "-", norm)[:48].strip("-") or "x"
    return f"name-{slug}-{digest}"


def parse_supplier_key(key: str) -> dict[str, str | None]:
    key = (key or "").strip()
    if key.startswith("rnc-"):
        return {"kind": "rnc", "value": key[4:], "name_norm": None}
    if key.startswith("rpe-"):
        return {"kind": "rpe", "value": key[4:], "name_norm": None}
    if key.startswith("name-"):
        rest = key[5:]
        # last -digest
        if "-" in rest:
            parts = rest.rsplit("-", 1)
            if len(parts[1]) == 10 and re.fullmatch(r"[0-9a-f]+", parts[1]):
                slug = parts[0].replace("-", " ")
                return {"kind": "name", "value": None, "name_norm": normalize_party_name(slug)}
        return {"kind": "name", "value": None, "name_norm": normalize_party_name(rest.replace("-", " "))}
    return {"kind": "name", "value": None, "name_norm": normalize_party_name(key)}


def parse_institution_key(key: str) -> dict[str, str | None]:
    key = (key or "").strip()
    if key.startswith("code-"):
        return {"kind": "code", "value": key[5:], "name_norm": None}
    if key.startswith("name-"):
        rest = key[5:]
        if "-" in rest:
            parts = rest.rsplit("-", 1)
            if len(parts[1]) == 10 and re.fullmatch(r"[0-9a-f]+", parts[1]):
                return {"kind": "name", "value": None, "name_norm": normalize_party_name(parts[0].replace("-", " "))}
        return {"kind": "name", "value": None, "name_norm": normalize_party_name(rest.replace("-", " "))}
    return {"kind": "name", "value": None, "name_norm": normalize_party_name(key)}


def identity_confidence(kind: str) -> str:
    if kind in ("rnc", "rpe", "code"):
        return "alta"
    if kind == "name":
        return "sugerida"
    return "baja"
