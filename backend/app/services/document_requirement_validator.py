"""Validación estricta requirement ↔ documento (Empresas, DGCP, Hub)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Aliases document_type aceptados por requirement
TYPE_ALIASES: dict[str, frozenset[str]] = {
    "tss": frozenset({"tss", "certificacion_tss"}),
    "certificacion_tss": frozenset({"tss", "certificacion_tss"}),
    "dgii": frozenset({"dgii", "certificacion_dgii"}),
    "certificacion_dgii": frozenset({"dgii", "certificacion_dgii"}),
    "mipyme": frozenset({"mipyme", "certificacion_mipyme"}),
    "certificacion_mipyme": frozenset({"mipyme", "certificacion_mipyme"}),
    "registro_mercantil": frozenset({"registro_mercantil"}),
    "rpe": frozenset({"rpe", "proveedor_estado", "certificacion_proveedor_estado"}),
    "proveedor_estado": frozenset({"rpe", "proveedor_estado", "certificacion_proveedor_estado"}),
    "oferta_tecnica": frozenset({"oferta_tecnica", "propuesta_tecnica"}),
    "oferta_economica": frozenset({"oferta_economica", "cotizacion", "propuesta_economica"}),
    "sncc_f033": frozenset({"sncc", "sncc_f033", "general", "formulario"}),
    "sncc_f034": frozenset({"sncc", "sncc_f034", "general", "formulario"}),
    "sncc_f042": frozenset({"sncc", "sncc_f042", "general"}),
    "sncc_f047": frozenset({"sncc", "sncc_f047", "general", "formulario"}),
    "cedula_representante": frozenset({"cedula_representante", "cedula"}),
}

# Keywords mínimas en filename/title (normalizado)
REQUIREMENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "tss": ("tss", "tesoreria", "seguro social", "certificacion tss"),
    "certificacion_tss": ("tss", "tesoreria", "seguro social", "certificacion tss"),
    "dgii": ("dgii", "certificacion fiscal", "obligaciones", "impuestos"),
    "certificacion_dgii": ("dgii", "certificacion fiscal", "obligaciones", "impuestos"),
    "mipyme": ("mipyme", "mipymes", "micro", "pequena", "pequeña"),
    "certificacion_mipyme": ("mipyme", "mipymes"),
    "registro_mercantil": ("registro mercantil", "camara de comercio", "camara comercio"),
    "rpe": ("rpe", "registro proveedor del estado", "proveedor del estado", "proveedor estado"),
    "proveedor_estado": ("rpe", "registro proveedor del estado", "proveedor del estado", "proveedor estado"),
    "oferta_tecnica": ("oferta tecnica", "oferta técnica", "propuesta tecnica", "propuesta técnica", "tecnica"),
    "oferta_economica": ("oferta economica", "oferta económica", "cotizacion", "cotización", "precio", "propuesta economica"),
    "sncc_f033": ("f033", "f.033", "sncc", "oferta economica", "033"),
    "sncc_f034": ("f034", "f.034", "sncc", "034"),
    "sncc_f042": ("f042", "f.042", "sncc", "oferente", "informacion oferente"),
    "sncc_f047": ("f047", "f.047", "sncc", "fabricante", "047"),
    "cedula_representante": ("cedula", "cédula", "identidad"),
    "certificacion_bancaria": ("banc", "certificacion bancaria", "certificación bancaria"),
    "acta_asamblea": ("acta", "asamblea"),
    "estatutos": ("estatuto",),
    "poderes": ("poder",),
    "poder_autorizacion": ("poder", "autorizacion", "autorización", "notarial"),
}

# Tipos/keywords que invalidan un match (oferta técnica no puede ser certificación legal)
FORBIDDEN_FOR_REQUIREMENT: dict[str, dict[str, tuple[str, ...]]] = {
    "oferta_tecnica": {
        "types": ("dgii", "rnc", "tss", "registro_mercantil", "proveedor_estado", "mipyme", "acta_asamblea", "certificacion_dgii", "certificacion_tss"),
        "keywords": ("dgii", "rnc", "tss", "registro mercantil", "proveedor", "mipyme", "acta asamblea", "certificacion fiscal"),
    },
    "registro_mercantil": {
        "types": ("rnc", "acta_asamblea", "dgii", "tss", "rpe", "proveedor_estado"),
        "keywords": (
            "acta rnc",
            "rnc justech",
            "certificacion dgii",
            "certificacion tss",
            "rpe",
            "proveedor del estado",
            "proveedor estado",
        ),
    },
    "certificacion_tss": {
        "types": ("acta_asamblea", "dgii", "rnc", "registro_mercantil"),
        "keywords": ("acta de la asamblea", "acta asamblea", "rnc", "registro mercantil", "dgii"),
    },
    "rpe": {
        "types": ("dgii", "tss", "acta_asamblea", "registro_mercantil"),
        "keywords": ("dgii", "tss", "acta", "registro mercantil"),
    },
}

OFFICIAL_KNOWLEDGE_FOLDER_PREFIXES = (
    "00_",
    "01_",
    "02_",
    "03_",
    "04_",
    "05_",
    "legal_documents",
    "identity",
)


def _norm(s: str | None) -> str:
    if not s:
        return ""
    return (
        s.lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
    )


def _blob(filename: str | None, title: str | None = None, document_type: str | None = None) -> str:
    parts = [_norm(filename), _norm(title), _norm(document_type)]
    return " ".join(p for p in parts if p)


@dataclass
class ValidationResult:
    ok: bool
    reason: str | None = None


def type_matches_requirement(requirement_key: str, document_type: str | None) -> bool:
    if not document_type:
        return False
    expected = TYPE_ALIASES.get(requirement_key, frozenset({requirement_key.replace("-", "_")}))
    actual = _norm(document_type)
    return actual in expected or any(a in actual for a in expected)


def keywords_match_requirement(requirement_key: str, filename: str | None, title: str | None = None) -> bool:
    keywords = REQUIREMENT_KEYWORDS.get(requirement_key)
    if not keywords:
        return True
    blob = _blob(filename, title)
    return any(_norm(k) in blob for k in keywords)


def has_forbidden_signals(requirement_key: str, filename: str | None, title: str | None, document_type: str | None) -> bool:
    rules = FORBIDDEN_FOR_REQUIREMENT.get(requirement_key)
    if not rules:
        return False
    blob = _blob(filename, title, document_type)
    dt = _norm(document_type)
    if any(_norm(t) in dt for t in rules.get("types", ())):
        return True
    return any(_norm(k) in blob for k in rules.get("keywords", ()))


def is_accessible_asset(asset: Any) -> bool:
    if asset is None:
        return False
    folder = _norm(getattr(asset, "folder_category", "") or "")
    in_official = any(
        folder.startswith(_norm(p)) or folder == _norm(p) for p in OFFICIAL_KNOWLEDGE_FOLDER_PREFIXES
    )
    if hasattr(asset, "is_active") and not asset.is_active and not in_official:
        return False
    path = getattr(asset, "relative_path", None) or ""
    if path.strip():
        return True
    meta = getattr(asset, "metadata_", None) or {}
    if isinstance(meta, dict) and (meta.get("web_url") or meta.get("graph_item_id")):
        return True
    return in_official


def is_valid_source_asset(asset: Any) -> bool:
    if not is_accessible_asset(asset):
        return False
    folder = _norm(getattr(asset, "folder_category", "") or "")
    if any(folder.startswith(_norm(p)) or folder == _norm(p) for p in OFFICIAL_KNOWLEDGE_FOLDER_PREFIXES):
        return True
    path = _norm(getattr(asset, "relative_path", "") or "")
    return "documentos_legales" in path or "01_documentos" in path or path.startswith("jaios/")


def rank_knowledge_asset_for_requirement(requirement_key: str, asset: Any) -> tuple[Any, ...]:
    """Ranking determinista compartido entre checklist y perfil empresarial."""
    path = _norm(getattr(asset, "relative_path", "") or "")
    filename = _norm(getattr(asset, "filename", "") or "")
    title = _norm(getattr(asset, "title", "") or "")
    rank = 0

    if requirement_key == "registro_mercantil":
        if "01_documentos_legales" in path and "justech" in path:
            rank += 100
        if path.startswith("onedrive//") or path.count("/") <= 2:
            rank -= 100
        if any(k in title for k in ("rpe", "proveedor del estado", "proveedor estado")):
            rank -= 100
        if "registro mercantil" in filename:
            rank += 20
        if title == filename:
            rank += 10

    ts = getattr(asset, "analyzed_at", None) or getattr(asset, "synced_at", None) or ""
    return (rank, ts, str(getattr(asset, "id", "")))


def is_not_expired_asset(asset: Any, *, check_vigency: bool = True) -> bool:
    if not check_vigency:
        return True
    vigency = _norm(getattr(asset, "vigency_status", "") or "")
    if vigency == "vencido":
        return False
    return True


def validate_asset_for_requirement(
    requirement_key: str,
    *,
    filename: str | None,
    title: str | None = None,
    document_type: str | None = None,
    asset: Any = None,
    check_vigency: bool = True,
    require_keywords: bool = True,
) -> ValidationResult:
    """Validación estricta para marcar un requirement como cumplido."""
    if asset is not None and not is_accessible_asset(asset):
        return ValidationResult(False, "asset_inaccesible")
    if asset is not None and not is_valid_source_asset(asset):
        return ValidationResult(False, "fuente_invalida")
    if asset is not None and not is_not_expired_asset(asset, check_vigency=check_vigency):
        return ValidationResult(False, "vencido")

    fn = filename or (getattr(asset, "filename", None) if asset else None)
    tit = title or (getattr(asset, "title", None) if asset else None)
    dt = document_type or (getattr(asset, "document_type", None) if asset else None)

    if has_forbidden_signals(requirement_key, fn, tit, dt):
        return ValidationResult(False, "categoria_prohibida")

    if not type_matches_requirement(requirement_key, dt):
        return ValidationResult(False, "document_type_incorrecto")

    if require_keywords and not keywords_match_requirement(requirement_key, fn, tit):
        return ValidationResult(False, "keywords_insuficientes")

    # Registro mercantil: el filename debe identificar el documento (metadata/título puede estar mal)
    if requirement_key == "registro_mercantil":
        fn_blob = _norm(fn)
        if "registro mercantil" not in fn_blob and "camara" not in fn_blob:
            return ValidationResult(False, "filename_sin_registro_mercantil")
        blob = _blob(fn, tit)
        if ("acta" in blob or "rnc" in blob) and "registro mercantil" not in blob and "camara" not in blob:
            return ValidationResult(False, "no_es_registro_mercantil")

    return ValidationResult(True)


def validate_sncc_compliance(
    *,
    filename: str | None,
    status: str | None,
    completable: bool = False,
) -> ValidationResult:
    """SNCC no cuenta como completo hasta autollenado/carga válida."""
    blob = _blob(filename)
    if not any(k in blob for k in ("f042", "f.042", "sncc", "oferente")):
        return ValidationResult(False, "sncc_sin_documento_valido")
    if status in ("encontrado_vigente", "validado_manual", "finalizado", "pdf_final_generado"):
        if not completable:
            return ValidationResult(False, "sncc_requiere_completado")
    return ValidationResult(True)


def empresa_field_key_for_doc_type(doc_type: str) -> str | None:
    mapping = {
        "tss": "tss",
        "dgii": "dgii",
        "mipyme": "mipyme",
        "registro_mercantil": "registro_mercantil",
        "proveedor_estado": "proveedor_estado",
        "rpe": "proveedor_estado",
        "certificacion_bancaria": "certificacion_bancaria",
        "cedula_representante": "cedula_representante",
        "acta_asamblea": "acta_asamblea",
        "estatutos": "estatutos",
        "poderes": "poderes",
    }
    return mapping.get(doc_type)
