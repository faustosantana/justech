"""Constantes de identidad corporativa — firma, sellos y mapeo por empresa."""

from __future__ import annotations

DEFAULT_SIGNATURE_FILE = "firma_fausto.png"

COMPANY_STAMP_FILES: dict[str, str] = {
    "justech": "sello_justech.png",
    "just_office": "sello_justoffice.png",
    "justoffice": "sello_justoffice.png",
    "mf_plug_safe": "sello_plugsafe.png",
    "plugsafe": "sello_plugsafe.png",
    "omni_solutions": "sello_omni.png",
    "omni": "sello_omni.png",
}

COMPANY_LABELS: dict[str, str] = {
    "justech": "Justech SRL",
    "just_office": "Just Office SRL",
    "justoffice": "Just Office SRL",
    "mf_plug_safe": "MF Plug & Safe Services SRL",
    "plugsafe": "PlugSafe",
    "omni_solutions": "Omni Solutions SRL",
    "omni": "Omni Solutions SRL",
}

CANONICAL_COMPANY_KEYS = frozenset({"justech", "just_office", "mf_plug_safe", "omni_solutions"})

ASSET_STATUSES = frozenset({"disponible", "faltante", "invalido", "requiere_revision"})
