"""Análisis de plantillas DOCX/PDF — detecta placeholders y campos."""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

PLACEHOLDER_RE = re.compile(
    r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}|"
    r"\[\[\s*([a-zA-Z0-9_]+)\s*\]\]|"
    r"\[\s*([A-Z0-9_]{2,})\s*\]",
)

FORM_TYPE_TO_SLUG: dict[str, str] = {
    "SNCC.F033": "sncc-f033",
    "SNCC.F034": "sncc-f034",
    "SNCC.F042": "sncc-f042",
    "SNCC.F047": "sncc-f047",
    "OFERTA.ECONOMICA": "oferta-economica",
    "CARTA.PRESENTACION": "carta-presentacion",
}

SLUG_TO_CATEGORY: dict[str, str] = {
    "sncc-f033": "dgcp",
    "sncc-f034": "dgcp",
    "sncc-f042": "dgcp",
    "sncc-f047": "dgcp",
    "oferta-economica": "commercial",
    "carta-presentacion": "commercial",
}


@dataclass
class TemplateField:
    key: str
    label: str
    placeholder: str
    source: str = "placeholder"


@dataclass
class TemplateAnalysis:
    form_type: str
    slug: str
    template_path: Path
    format: str
    fields: list[TemplateField] = field(default_factory=list)
    acroform_fields: list[str] = field(default_factory=list)
    template_version: str = ""


class TemplateAnalysisService:
    def __init__(self, templates_root: Path | None = None) -> None:
        self.templates_root = templates_root or (
            Path(__file__).resolve().parent.parent.parent / "templates"
        )

    def resolve_template_path(self, form_type: str) -> Path | None:
        slug = FORM_TYPE_TO_SLUG.get(form_type.upper().replace(" ", "."))
        if not slug:
            return None
        category = SLUG_TO_CATEGORY.get(slug, "dgcp")
        for ext in (".docx", ".pdf"):
            path = self.templates_root / category / f"{slug}{ext}"
            if path.is_file():
                return path
        return None

    def ensure_docx_templates(self) -> list[Path]:
        """Crea plantillas base con placeholders si no existen (no sobrescribe)."""
        from app.services.document_autofill.template_factory import ensure_all_templates

        return ensure_all_templates(self.templates_root)

    def analyze(self, form_type: str, *, skip_factory: bool = False) -> TemplateAnalysis:
        if not skip_factory:
            self.ensure_docx_templates()
        form_key = form_type.upper().replace(" ", ".")
        slug = FORM_TYPE_TO_SLUG.get(form_key, form_key.lower().replace(".", "-"))
        path = self.resolve_template_path(form_key)
        if not path:
            category = SLUG_TO_CATEGORY.get(slug, "dgcp")
            path = self.templates_root / category / f"{slug}.docx"

        if path.suffix.lower() == ".pdf":
            return self._analyze_pdf(form_key, slug, path)
        return self._analyze_docx(form_key, slug, path)

    def analyze_bytes(
        self,
        form_type: str,
        template_bytes: bytes,
        *,
        source_label: str,
        template_version: str,
        file_format: str = "docx",
    ) -> TemplateAnalysis:
        form_key = form_type.upper().replace(" ", ".")
        slug = FORM_TYPE_TO_SLUG.get(form_key, form_key.lower().replace(".", "-"))
        virtual_path = Path(source_label)
        if file_format == "pdf":
            return self._analyze_pdf_bytes(form_key, slug, template_bytes, virtual_path, template_version)
        return self._analyze_docx_bytes(form_key, slug, template_bytes, virtual_path, template_version)

    def _analyze_docx_bytes(
        self,
        form_type: str,
        slug: str,
        template_bytes: bytes,
        path: Path,
        version: str,
    ) -> TemplateAnalysis:
        keys = self._extract_docx_keys(template_bytes)
        fields = [
            TemplateField(key=k, label=k.replace("_", " ").title(), placeholder=f"{{{{ {k} }}}}")
            for k in sorted(keys)
        ]
        return TemplateAnalysis(
            form_type=form_type,
            slug=slug,
            template_path=path,
            format="docx",
            fields=fields,
            template_version=version,
        )

    def _analyze_pdf_bytes(
        self,
        form_type: str,
        slug: str,
        template_bytes: bytes,
        path: Path,
        version: str,
    ) -> TemplateAnalysis:
        acro: list[str] = []
        text_keys: set[str] = set()
        reader = PdfReader(BytesIO(template_bytes))
        if reader.get_fields():
            acro = [k for k in reader.get_fields().keys() if k]
        for page in reader.pages:
            content = page.extract_text() or ""
            for match in PLACEHOLDER_RE.finditer(content):
                key = next(g for g in match.groups() if g)
                text_keys.add(key.lower())
        fields = [
            TemplateField(
                key=k,
                label=k.replace("_", " ").title(),
                placeholder=k,
                source="acroform" if k in acro else "text",
            )
            for k in sorted(set(acro) | text_keys)
        ]
        return TemplateAnalysis(
            form_type=form_type,
            slug=slug,
            template_path=path,
            format="pdf",
            fields=fields,
            acroform_fields=acro,
            template_version=version,
        )

    @staticmethod
    def _extract_docx_keys(template_bytes: bytes) -> set[str]:
        keys: set[str] = set()
        with zipfile.ZipFile(BytesIO(template_bytes)) as zf:
            for name in zf.namelist():
                if not name.startswith("word/") or not name.endswith(".xml"):
                    continue
                text = zf.read(name).decode("utf-8", errors="ignore")
                for match in PLACEHOLDER_RE.finditer(text):
                    key = next(g for g in match.groups() if g)
                    keys.add(key.lower())
                for alias in re.findall(r'w:alias w:val="([^"]+)"', text):
                    keys.add(alias.lower().replace(" ", "_"))
        return keys

    def _analyze_docx(self, form_type: str, slug: str, path: Path) -> TemplateAnalysis:
        keys: set[str] = set()
        if path.is_file():
            keys = self._extract_docx_keys(path.read_bytes())

        fields = [
            TemplateField(
                key=k,
                label=k.replace("_", " ").title(),
                placeholder=f"{{{{ {k} }}}}",
            )
            for k in sorted(keys)
        ]
        version = str(path.stat().st_mtime_ns) if path.is_file() else "missing"
        return TemplateAnalysis(
            form_type=form_type,
            slug=slug,
            template_path=path,
            format="docx",
            fields=fields,
            template_version=version,
        )

    def _analyze_pdf(self, form_type: str, slug: str, path: Path) -> TemplateAnalysis:
        acro: list[str] = []
        text_keys: set[str] = set()
        if path.is_file():
            reader = PdfReader(str(path))
            if reader.get_fields():
                acro = [k for k in reader.get_fields().keys() if k]
            for page in reader.pages:
                content = page.extract_text() or ""
                for match in PLACEHOLDER_RE.finditer(content):
                    key = next(g for g in match.groups() if g)
                    text_keys.add(key.lower())

        fields = [
            TemplateField(key=k, label=k.replace("_", " ").title(), placeholder=k, source="acroform" if k in acro else "text")
            for k in sorted(set(acro) | text_keys)
        ]
        version = str(path.stat().st_mtime_ns)
        return TemplateAnalysis(
            form_type=form_type,
            slug=slug,
            template_path=path,
            format="pdf",
            fields=fields,
            acroform_fields=acro,
            template_version=version,
        )

    def read_template_bytes(self, form_type: str) -> tuple[bytes, TemplateAnalysis]:
        analysis = self.analyze(form_type)
        if not analysis.template_path.is_file():
            raise FileNotFoundError(f"Plantilla no encontrada: {analysis.template_path}")
        return analysis.template_path.read_bytes(), analysis
