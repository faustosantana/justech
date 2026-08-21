"""Identidad estable de proveedores e instituciones (histórico DGCP).

Prioridad de resolución (sin fusión agresiva):
1. RNC exacto verificado (si aparece en payload oficial)
2. RPE exacto
3. ID / código DGCP exacto
4. Nombre normalizado solo como clave de sugerencia (confidence menor)

Nombre similar sin ID oficial → POSSIBLE_DUPLICATE (nunca auto-merge).
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any, Literal

RncSource = Literal[
    "DGCP_CONTRACT",
    "DGCP_SUPPLIER",
    "DGCP_RPE",
    "OTHER_OFFICIAL",
    "NONE",
]

DuplicateStatus = Literal[
    "DUPLICATE_CONFIRMED",
    "NOT_DUPLICATE",
    "REVIEW_REQUIRED",
    "POSSIBLE_DUPLICATE",
    "IGNORED",
]


def normalize_party_name(name: str | None) -> str:
    if not name:
        return ""
    text = unicodedata.normalize("NFKD", name.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.replace(",", " ").replace(".", " ")
    text = re.sub(r"\bs\.?\s*r\.?\s*l\.?\b", "srl", text)
    text = re.sub(r"\be\.?\s*i\.?\s*r\.?\s*l\.?\b", "eirl", text)
    text = re.sub(r"\bs\.?\s*a\.?\s*s\.?\b", "sas", text)
    text = re.sub(r"\bs\.?\s*a\.?\b", "sa", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _digits(value: Any) -> str:
    return re.sub(r"\D", "", str(value)) if value is not None else ""


def extract_rnc_with_source(raw: dict[str, Any] | None) -> tuple[str | None, RncSource]:
    """Extrae RNC solo desde campos oficiales del payload DGCP (sin inventar)."""
    if not isinstance(raw, dict):
        return None, "NONE"

    contrato = raw.get("contrato") if isinstance(raw.get("contrato"), dict) else {}
    articulo = raw.get("contrato_articulo") if isinstance(raw.get("contrato_articulo"), dict) else {}
    extra_c = contrato.get("extra") if isinstance(contrato.get("extra"), dict) else {}
    extra_a = articulo.get("extra") if isinstance(articulo.get("extra"), dict) else {}
    extra_root = raw.get("extra") if isinstance(raw.get("extra"), dict) else {}

    contract_paths = [
        (contrato.get("rnc"), "DGCP_CONTRACT"),
        (contrato.get("RNC"), "DGCP_CONTRACT"),
        (contrato.get("cedula_rnc"), "DGCP_CONTRACT"),
        (extra_c.get("rnc"), "DGCP_CONTRACT"),
        (extra_c.get("RNC"), "DGCP_CONTRACT"),
        (extra_c.get("cedula_rnc"), "DGCP_CONTRACT"),
        (raw.get("rnc"), "DGCP_CONTRACT"),
        (raw.get("RNC"), "DGCP_CONTRACT"),
        (raw.get("cedula_rnc"), "DGCP_CONTRACT"),
        (extra_root.get("rnc"), "DGCP_CONTRACT"),
        (extra_a.get("rnc"), "DGCP_CONTRACT"),
    ]
    for value, source in contract_paths:
        digits = _digits(value)
        if len(digits) >= 9:
            return digits, source  # type: ignore[return-value]

    supplier_paths = [
        (raw.get("supplier_rnc"), "DGCP_SUPPLIER"),
        (contrato.get("rnc_proveedor"), "DGCP_SUPPLIER"),
        (extra_c.get("rnc_proveedor"), "DGCP_SUPPLIER"),
    ]
    for value, source in supplier_paths:
        digits = _digits(value)
        if len(digits) >= 9:
            return digits, source  # type: ignore[return-value]

    return None, "NONE"


def extract_rnc_from_payload(raw: dict[str, Any] | None) -> str | None:
    rnc, _ = extract_rnc_with_source(raw)
    return rnc


def supplier_stable_key(*, rpe: str | None, name: str | None, rnc: str | None = None) -> str:
    rnc_digits = _digits(rnc)
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
    if key.startswith("dgcp-supplier-"):
        return {"kind": "dgcp", "value": key[len("dgcp-supplier-") :], "name_norm": None}
    if key.startswith("name-"):
        rest = key[5:]
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
    if kind in ("rnc", "rpe", "code", "dgcp"):
        return "alta"
    if kind == "name":
        return "sugerida"
    return "baja"


def name_token_jaccard(a: str | None, b: str | None) -> float:
    ta = set(normalize_party_name(a).split())
    tb = set(normalize_party_name(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def can_auto_merge_suppliers(
    *,
    rnc_a: str | None,
    rnc_b: str | None,
    rpe_a: str | None,
    rpe_b: str | None,
    dgcp_id_a: str | None = None,
    dgcp_id_b: str | None = None,
) -> tuple[bool, str]:
    """Auto-merge solo con identificador oficial exacto."""
    ra, rb = _digits(rnc_a), _digits(rnc_b)
    if ra and rb and ra == rb and len(ra) >= 9:
        return True, "RNC_EXACT"
    pa = re.sub(r"[^0-9A-Za-z]", "", str(rpe_a or ""))
    pb = re.sub(r"[^0-9A-Za-z]", "", str(rpe_b or ""))
    if pa and pb and pa == pb:
        return True, "RPE_EXACT"
    if dgcp_id_a and dgcp_id_b and str(dgcp_id_a) == str(dgcp_id_b):
        return True, "DGCP_ID_EXACT"
    return False, "NO_OFFICIAL_ID"


def classify_name_pair(
    *,
    name_a: str | None,
    name_b: str | None,
    rpe_a: str | None = None,
    rpe_b: str | None = None,
    rnc_a: str | None = None,
    rnc_b: str | None = None,
) -> tuple[DuplicateStatus, float, str]:
    """Clasifica par de nombres. Nunca declara DUPLICATE_CONFIRMED solo por nombre."""
    auto, criterion = can_auto_merge_suppliers(rnc_a=rnc_a, rnc_b=rnc_b, rpe_a=rpe_a, rpe_b=rpe_b)
    if auto:
        return "DUPLICATE_CONFIRMED", 1.0, criterion

    na, nb = normalize_party_name(name_a), normalize_party_name(name_b)
    if not na or not nb:
        return "NOT_DUPLICATE", 0.0, "MISSING_NAME"
    if na == nb:
        # mismo nombre normalizado, IDs distintos → revisar, no merge automático
        if (rpe_a or rpe_b) and (rpe_a != rpe_b):
            return "POSSIBLE_DUPLICATE", 0.92, "SAME_NORMALIZED_NAME_DIFFERENT_RPE"
        return "POSSIBLE_DUPLICATE", 0.88, "SAME_NORMALIZED_NAME"

    score = name_token_jaccard(name_a, name_b)
    # Evitar fusionar ministerios/dependencias / agencias genéricas por prefijo corto
    generic = {"ministerio", "direccion", "instituto", "agencia", "estacion", "servicios", "de", "la", "del"}
    shared = set(na.split()) & set(nb.split())
    if shared and shared.issubset(generic) and score < 0.85:
        return "NOT_DUPLICATE", score, "GENERIC_PREFIX_ONLY"
    if score >= 0.85:
        return "POSSIBLE_DUPLICATE", score, "HIGH_NAME_SIMILARITY"
    if score >= 0.7:
        return "REVIEW_REQUIRED", score, "MODERATE_NAME_SIMILARITY"
    return "NOT_DUPLICATE", score, "LOW_NAME_SIMILARITY"


def can_auto_merge_institutions(
    *,
    code_a: str | None,
    code_b: str | None,
    rnc_a: str | None = None,
    rnc_b: str | None = None,
) -> tuple[bool, str]:
    ca = re.sub(r"[^0-9A-Za-z_-]", "", str(code_a or ""))
    cb = re.sub(r"[^0-9A-Za-z_-]", "", str(code_b or ""))
    if ca and cb and ca == cb:
        return True, "BUYER_CODE_EXACT"
    ra, rb = _digits(rnc_a), _digits(rnc_b)
    if ra and rb and ra == rb and len(ra) >= 9:
        return True, "INSTITUTION_RNC_EXACT"
    return False, "NO_OFFICIAL_ID"
