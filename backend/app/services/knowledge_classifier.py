"""Clasificación documental y detección de empresa — Corporate Knowledge (Fase 7.2)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

DATE_IN_FILENAME_RE = re.compile(
    r"(\d{1,2})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(\d{2,4})|(\d{4})[-/](\d{2})[-/](\d{2})"
)

COMPANY_PATH_MAP: dict[str, str] = {
    "justech": "justech",
    "just_office": "just_office",
    "just office": "just_office",
    "omni": "omni_solutions",
    "omni_solutions": "omni_solutions",
    "plug_safe": "mf_plug_safe",
    "plug safe": "mf_plug_safe",
    "mf_plug": "mf_plug_safe",
}

COMPANY_LABELS: dict[str, str] = {
    "justech": "Justech SRL",
    "just_office": "Just Office SRL",
    "omni_solutions": "Omni Solutions SRL",
    "mf_plug_safe": "MF Plug & Safe Services SRL",
}

DOCUMENT_TYPE_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("rpe", ("rpe", "registro de proveedores", "registro proveedores")),
    ("rnc", ("rnc", "registro nacional contribuyente")),
    ("registro_mercantil", ("registro mercantil", "registro_mercantil")),
    ("estatutos", ("estatutos", "estatutos sociales")),
    ("dgii", ("dgii", "certificacion dgii", "certificación dgii", "obligaciones al dia", "obligaciones al día")),
    ("tss", ("tss", "certificacion tss", "certificación tss", "seguro social")),
    ("certificacion_bancaria", ("certificacion bancaria", "certificación bancaria", "cuenta bancaria")),
    ("acta", ("acta", "asamblea")),
    ("poder", ("poder", "poderes")),
    ("cedula", ("cedula", "cédula")),
    ("carta", ("carta", "carta fabricante", "carta del fabricante")),
    ("contrato", ("contrato", "acuerdo")),
    ("sncc_f033", ("sncc f033", "f033", "f.033", "sncc_f033", "sncc.f033")),
    ("sncc_f034", ("sncc f034", "f034", "f.034", "sncc_f034", "sncc.f034", "sncc_f_034")),
    ("sncc_f042", ("sncc f042", "f042", "f.042", "sncc_f042", "sncc.f042")),
    ("sncc_f047", ("sncc f047", "f047", "f.047", "sncc_f047", "sncc.f047")),
    ("sncc_d040", ("sncc d040", "d040", "d.040", "sncc_d040", "sncc.d040", "sncc_d_040")),
    ("oferta_tecnica", ("oferta tecnica", "oferta técnica", "propuesta tecnica")),
    ("oferta_economica", ("oferta economica", "oferta económica", "cotizacion", "cotización")),
    ("lista_precios", ("lista de precios", "lista precios", "price list")),
    ("ficha_tecnica", ("ficha tecnica", "ficha técnica", "datasheet")),
    ("certificacion_fabricante", ("certificacion fabricante", "certificación fabricante", "autorizacion fabricante")),
    ("mipymes", ("mipymes", "mipyme")),
)

MANUFACTURER_KEYWORDS: dict[str, str] = {
    "dell": "Dell",
    "hp": "HP",
    "hewlett": "HP",
    "lenovo": "Lenovo",
    "microsoft": "Microsoft",
    "fortinet": "Fortinet",
    "canon": "Canon",
    "ingram": "Ingram Micro",
    "ingram micro": "Ingram Micro",
}

FOLDER_CATEGORY_MAP: dict[str, str] = {
    "00_DATOS_EMPRESAS": "datos_empresa",
    "01_DOCUMENTOS_LEGALES": "legal",
    "02_PLANTILLAS": "plantilla",
    "03_PROVEEDORES": "proveedor",
    "04_FICHAS_TECNICAS": "ficha_tecnica",
    "05_COTIZACIONES": "cotizacion",
}


@dataclass
class ClassificationResult:
    document_type: str
    company_key: str | None
    supplier_name: str | None
    manufacturer_name: str | None
    client_name: str | None
    folder_category: str
    tags: list[str]
    keywords: list[str]
    valid_from: str | None
    valid_until: str | None


class KnowledgeClassifier:
    def classify(
        self,
        *,
        relative_path: str,
        filename: str,
        text: str = "",
        folder_name: str = "",
    ) -> ClassificationResult:
        blob = f"{relative_path} {filename} {text}".lower()
        parts = PurePosixPath(relative_path).parts
        top_folder = parts[0] if parts else folder_name
        folder_category = FOLDER_CATEGORY_MAP.get(top_folder, "general")

        company_key = self._detect_company(parts, blob)
        document_type = self._detect_document_type(blob, folder_category)
        supplier = self._detect_supplier(parts, blob, folder_category)
        manufacturer = self._detect_manufacturer(blob)
        client = self._detect_client(blob)
        valid_from, valid_until = self._detect_dates(blob, filename)

        tags = [document_type]
        if company_key:
            tags.append(company_key)
        if supplier:
            tags.append("proveedor")
        if manufacturer:
            tags.append("fabricante")

        keywords = list(dict.fromkeys(
            [document_type, company_key or "", supplier or "", manufacturer or ""] + tags
        ))
        keywords = [k for k in keywords if k]

        return ClassificationResult(
            document_type=document_type,
            company_key=company_key,
            supplier_name=supplier,
            manufacturer_name=manufacturer,
            client_name=client,
            folder_category=folder_category,
            tags=tags,
            keywords=keywords,
            valid_from=valid_from,
            valid_until=valid_until,
        )

    @staticmethod
    def _detect_company(parts: tuple[str, ...], blob: str) -> str | None:
        for part in parts:
            key = part.lower().replace(" ", "_").replace("-", "_")
            if key in COMPANY_PATH_MAP:
                return COMPANY_PATH_MAP[key]
            for alias, mapped in COMPANY_PATH_MAP.items():
                if alias in part.lower():
                    return mapped
        for label_key, label in COMPANY_LABELS.items():
            if label.lower() in blob:
                return label_key
        return None

    @staticmethod
    def _detect_document_type(blob: str, folder_category: str) -> str:
        if folder_category == "plantilla" or folder_category == "plantilla_formulario":
            for doc_type, keywords in DOCUMENT_TYPE_RULES:
                if doc_type.startswith("sncc_") and any(k in blob for k in keywords):
                    return doc_type
            if "sncc" in blob:
                return "formulario_sncc"
            return "plantilla"
        if folder_category == "proveedor":
            if any(k in blob for k in ("precio", "stock", "inventario", "dell", "lenovo", "ingram")):
                return "lista_precios"
        if folder_category == "ficha_tecnica":
            return "ficha_tecnica"
        if folder_category == "cotizacion":
            return "lista_precios"
        if folder_category == "datos_empresa":
            return "datos_empresa"
        for doc_type, keywords in DOCUMENT_TYPE_RULES:
            if any(k in blob for k in keywords):
                return doc_type
        return "general"

    @staticmethod
    def _detect_supplier(parts: tuple[str, ...], blob: str, folder_category: str) -> str | None:
        if folder_category != "proveedor":
            return None
        if len(parts) >= 2:
            return parts[1].replace("_", " ").title()
        return None

    @staticmethod
    def _detect_manufacturer(blob: str) -> str | None:
        for key, label in MANUFACTURER_KEYWORDS.items():
            if key in blob:
                return label
        return None

    @staticmethod
    def _detect_client(blob: str) -> str | None:
        clients = ("banco ademi", "midas", "capital dbg", "banco popular", "banreservas")
        for c in clients:
            if c in blob:
                return c.title()
        return None

    @staticmethod
    def _detect_dates(blob: str, filename: str) -> tuple[str | None, str | None]:
        combined = f"{blob} {filename}"
        matches = DATE_IN_FILENAME_RE.findall(combined)
        if not matches:
            return None, None
        last = matches[-1]
        if last[3]:
            iso = f"{last[3]}-{last[4]}-{last[5]}"
            return None, iso
        day, month, year = last[0], last[1], last[2]
        if len(year) == 2:
            year = f"20{year}"
        iso = f"{year}-{int(month):02d}-{int(day):02d}"
        return None, iso
