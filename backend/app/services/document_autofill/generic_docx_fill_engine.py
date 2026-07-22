"""Motor genérico de autollenado DOCX — preserva formato original."""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from io import BytesIO

from app.services.document_autofill.field_alias_registry import (
    normalize_alias,
    suggest_canonical,
)

MISSING_MARKER = "[[PENDIENTE]]"

WT_RE = re.compile(r"(<w:t(?:\s[^>]*)?>)(.*?)(</w:t>)")
TABLE_ROW_RE = re.compile(r"<w:tr\b[^>]*>.*?</w:tr>", re.DOTALL)
SDT_BLOCK_RE = re.compile(
    r"(<w:sdt\b[^>]*>.*?<w:alias w:val=\"([^\"]*)\"[^>]*/>.*?<w:sdtContent>)(.*?)(</w:sdtContent>.*?</w:sdt>)",
    re.DOTALL,
)
BRACKET_HINT_RE = re.compile(r"\[([^\]]{4,120})\]")
MERGEFIELD_RE = re.compile(
    r"(<w:fldSimple[^>]*w:instr=\"[^\"]*MERGEFIELD\s+([^\"\s\\]+)[^\"]*\"[^>]*>)(.*?)(</w:fldSimple>)",
    re.DOTALL | re.I,
)
INSTR_MERGE_RE = re.compile(r"MERGEFIELD\s+([^\s\\]+)", re.I)
BOOKMARK_RE = re.compile(r'<w:bookmarkStart w:name="([^"]+)"[^/]*/>')
UNDERLINE_BLANK_RE = re.compile(r"_{3,}")

# Etiquetas de fila SNCC/DGCP → campo canónico (texto plano de fila)
ROW_LABEL_CANONICAL: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"3\.\s*RNC|RNC\s*/\s*Cédula|Pasaporte del Oferente", re.I), "rnc"),
    (re.compile(r"5\.\s*Domicilio legal|domicilio legal del oferente", re.I), "direccion"),
    (re.compile(r"raz[oó]n social del oferente", re.I), "razon_social"),
    (re.compile(r"representante autorizado.*nombre", re.I), "representante_autorizado"),
    (re.compile(r"representante autorizado.*direcci[oó]n", re.I), "direccion"),
    (re.compile(r"tel[eé]fono.*fax.*representante", re.I), "telefono"),
    (re.compile(r"correo electr[oó]nico.*representante", re.I), "correo"),
    (re.compile(r"RPE del Oferente", re.I), "rpe"),
    (re.compile(r"fecha\s*:", re.I), "fecha"),
    (re.compile(r"expediente de compras|no\.\s*del expediente", re.I), "proceso_dgcp"),
    (re.compile(r"entidad contratante|nombre de la instituci[oó]n", re.I), "entidad_contratante"),
    (re.compile(r"monto de la oferta|precio total", re.I), "monto"),
    (re.compile(r"objeto del (contrato|proceso)", re.I), "objeto_proceso"),
    (re.compile(r"plazo de entrega", re.I), "plazo_entrega"),
    (re.compile(r"garant[ií]a", re.I), "garantia"),
    (re.compile(r"fabricante", re.I), "fabricante"),
)


@dataclass
class DetectedDocxField:
    key: str
    source: str
    label: str = ""
    raw: str = ""


@dataclass
class DocxFillStats:
    detected: list[DetectedDocxField] = field(default_factory=list)
    filled_keys: set[str] = field(default_factory=set)
    unmapped_brackets: list[str] = field(default_factory=list)


def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _value_for(values: dict[str, str], key: str) -> str | None:
    if not key:
        return None
    val = values.get(key) or values.get(key.lower())
    if val is None or not str(val).strip():
        return None
    return str(val).strip()


def _merged_lookup(values: dict[str, str], alias_values: dict[str, str]) -> dict[str, str]:
    merged = {k: str(v) for k, v in values.items() if v is not None and str(v).strip()}
    for alias, val in alias_values.items():
        if val is not None and str(val).strip():
            merged[alias] = str(val).strip()
            merged[normalize_alias(alias)] = str(val).strip()
    return merged


def _canonical_for_hint(hint: str) -> str | None:
    low = hint.strip().lower()
    if low.startswith("indicar "):
        low = low[8:].strip()
    suggestion = suggest_canonical(hint)
    if suggestion.canonical:
        return suggestion.canonical
    suggestion = suggest_canonical(low)
    return suggestion.canonical


def _row_plain_text(row_xml: str) -> str:
    return "".join(m.group(2) for m in WT_RE.finditer(row_xml))


def _replace_first_wt(content: str, new_text: str) -> str:
    safe = _xml_escape(new_text)

    def repl(m: re.Match[str]) -> str:
        return m.group(1) + safe + m.group(3)

    if WT_RE.search(content):
        return WT_RE.sub(repl, content, count=1)
    return content


def _append_to_last_wt(row_xml: str, suffix: str) -> str:
    safe = _xml_escape(suffix)
    matches = list(WT_RE.finditer(row_xml))
    if not matches:
        return row_xml
    last = matches[-1]

    def last_repl(m: re.Match[str]) -> str:
        return m.group(1) + m.group(2) + safe + m.group(3)

    return row_xml[: last.start()] + WT_RE.sub(last_repl, row_xml[last.start() : last.end()], count=1) + row_xml[last.end() :]


def detect_fields_in_xml(xml: str) -> list[DetectedDocxField]:
    found: list[DetectedDocxField] = []
    seen: set[str] = set()

    def add(key: str, source: str, label: str = "", raw: str = "") -> None:
        norm = normalize_alias(key)
        token = f"{source}:{norm}"
        if token in seen:
            return
        seen.add(token)
        found.append(DetectedDocxField(key=norm, source=source, label=label or key, raw=raw))

    for alias in re.findall(r'w:alias w:val="([^"]+)"', xml):
        add(alias, "content_control", alias, alias)
    for key in re.findall(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", xml):
        add(key, "mustache", key)
    for key in re.findall(r"\[\[\s*([a-zA-Z0-9_]+)\s*\]\]", xml):
        add(key, "bracket_key", key)
    for hint in BRACKET_HINT_RE.findall(xml):
        canon = _canonical_for_hint(hint)
        add(canon or hint, "bracket_hint", hint, hint)
    for m in MERGEFIELD_RE.finditer(xml):
        add(m.group(2), "mergefield", m.group(2))
    for m in INSTR_MERGE_RE.finditer(xml):
        add(m.group(1), "mergefield", m.group(1))
    for bm in BOOKMARK_RE.findall(xml):
        add(bm, "bookmark", bm)
    return found


def detect_docx_fields(template_bytes: bytes) -> list[DetectedDocxField]:
    all_fields: list[DetectedDocxField] = []
    seen: set[str] = set()
    with zipfile.ZipFile(BytesIO(template_bytes)) as zf:
        for name in zf.namelist():
            if not name.startswith("word/") or not name.endswith(".xml"):
                continue
            xml = zf.read(name).decode("utf-8", errors="ignore")
            for f in detect_fields_in_xml(xml):
                token = f"{f.source}:{f.key}"
                if token not in seen:
                    seen.add(token)
                    all_fields.append(f)
    return all_fields


def _fill_sdt_blocks(xml: str, lookup: dict[str, str], stats: DocxFillStats) -> str:
    def block_repl(m: re.Match[str]) -> str:
        prefix, alias_raw, inner, suffix = m.group(1), m.group(2), m.group(3), m.group(4)
        norm = normalize_alias(alias_raw)
        val = lookup.get(alias_raw) or lookup.get(norm)
        if val is None:
            suggestion = suggest_canonical(alias_raw)
            if suggestion.canonical:
                val = lookup.get(suggestion.canonical)
        if val is None:
            return m.group(0)
        stats.filled_keys.add(norm)
        new_inner = _replace_first_wt(inner, val)
        return prefix + new_inner + suffix

    return SDT_BLOCK_RE.sub(block_repl, xml)


def _fill_merge_fields(xml: str, lookup: dict[str, str], stats: DocxFillStats) -> str:
    def repl(m: re.Match[str]) -> str:
        prefix, field_name, inner, suffix = m.group(1), m.group(2), m.group(3), m.group(4)
        norm = normalize_alias(field_name)
        val = lookup.get(field_name) or lookup.get(norm)
        if val is None:
            suggestion = suggest_canonical(field_name)
            val = lookup.get(suggestion.canonical) if suggestion.canonical else None
        if val is None:
            return m.group(0)
        stats.filled_keys.add(norm)
        new_inner = _replace_first_wt(inner, val) if inner.strip() else f"<w:r><w:t>{_xml_escape(val)}</w:t></w:r>"
        return prefix + new_inner + suffix

    xml = MERGEFIELD_RE.sub(repl, xml)
    return xml


def _fill_bracket_hints(xml: str, lookup: dict[str, str], stats: DocxFillStats) -> str:
    for hint in set(BRACKET_HINT_RE.findall(xml)):
        canon = _canonical_for_hint(hint)
        val = None
        if canon:
            val = lookup.get(canon)
            if canon == "representante_autorizado" and val is None:
                val = lookup.get("representante_legal")
        if val is None:
            stats.unmapped_brackets.append(hint)
            continue
        stats.filled_keys.add(canon or hint)
        xml = xml.replace(f"[{hint}]", _xml_escape(val))
    return xml


def _fill_row_labels(xml: str, lookup: dict[str, str], stats: DocxFillStats) -> str:
    def row_repl(m: re.Match[str]) -> str:
        row_xml = m.group(0)
        plain = _row_plain_text(row_xml)
        if "[" in plain and "]" in plain:
            return row_xml
        for pattern, key in ROW_LABEL_CANONICAL:
            if not pattern.search(plain):
                continue
            val = lookup.get(key)
            if val is None:
                return row_xml
            if val in plain:
                return row_xml
            stats.filled_keys.add(key)
            if UNDERLINE_BLANK_RE.search(plain):
                return UNDERLINE_BLANK_RE.sub(_xml_escape(val), row_xml, count=1)
            return _append_to_last_wt(row_xml, " " + val)
        return row_xml

    return TABLE_ROW_RE.sub(row_repl, xml)


def _fill_underline_blanks(xml: str, lookup: dict[str, str], stats: DocxFillStats) -> str:
    """Rellena líneas con subrayados (____) cuando la etiqueta precedente es reconocible."""
    if not UNDERLINE_BLANK_RE.search(xml):
        return xml

    def para_repl(m: re.Match[str]) -> str:
        para = m.group(0)
        plain = _row_plain_text(para)
        if not UNDERLINE_BLANK_RE.search(plain):
            return para
        for pattern, key in ROW_LABEL_CANONICAL:
            if not pattern.search(plain):
                continue
            val = lookup.get(key)
            if val is None or val in plain:
                return para
            stats.filled_keys.add(key)
            return UNDERLINE_BLANK_RE.sub(_xml_escape(val), para, count=1)
        return para

    return re.sub(r"<w:p\b[^>]*>.*?</w:p>", para_repl, xml, flags=re.DOTALL)


def fill_xml_part(xml: str, lookup: dict[str, str], stats: DocxFillStats) -> str:
    for key in set(re.findall(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", xml)):
        val = _value_for(lookup, key)
        if val:
            stats.filled_keys.add(key)
            xml = re.sub(
                r"\{\{\s*" + re.escape(key) + r"\s*\}\}",
                _xml_escape(val),
                xml,
                flags=re.IGNORECASE,
            )
    for key in set(re.findall(r"\[\[\s*([a-zA-Z0-9_]+)\s*\]\]", xml)):
        val = _value_for(lookup, key)
        if val:
            stats.filled_keys.add(key)
            xml = re.sub(
                r"\[\[\s*" + re.escape(key) + r"\s*\]\]",
                _xml_escape(val),
                xml,
                flags=re.IGNORECASE,
            )
    xml = _fill_sdt_blocks(xml, lookup, stats)
    xml = _fill_merge_fields(xml, lookup, stats)
    xml = _fill_bracket_hints(xml, lookup, stats)
    xml = _fill_row_labels(xml, lookup, stats)
    xml = _fill_underline_blanks(xml, lookup, stats)
    return xml


def fill_docx_bytes_generic(
    template_bytes: bytes,
    values: dict[str, str],
    *,
    alias_values: dict[str, str] | None = None,
) -> tuple[bytes, DocxFillStats]:
    """Rellena plantilla DOCX preservando estructura ZIP/XML."""
    alias_values = alias_values or {}
    lookup = _merged_lookup(values, alias_values)
    stats = DocxFillStats(detected=detect_docx_fields(template_bytes))
    out = BytesIO()
    with zipfile.ZipFile(BytesIO(template_bytes), "r") as zin:
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename.startswith("word/") and item.filename.endswith(".xml"):
                    text = data.decode("utf-8")
                    text = fill_xml_part(text, lookup, stats)
                    data = text.encode("utf-8")
                zout.writestr(item, data)
    out.seek(0)
    return out.read(), stats
