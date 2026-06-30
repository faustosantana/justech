#!/usr/bin/env python3
"""Analyze DGII Excel templates and emit structural metadata (Fase 17.5)."""

from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import xlrd
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "data/localizations/do/templates"
EXTRACT_DIR = Path("/tmp/dgii-analysis")
OUTPUT_SUMMARY = EXTRACT_DIR / "all_templates_summary.json"

# Primary (vigente NG) source files per mapping code
PRIMARY_SOURCES = {
    "606": "Formato-de-Envio-606-(NG-07-2018-y-05-2019).zip",
    "607": "Formato-de-Envio-607-(NG-07-2018-y-05-2019).zip",
    "608": "Formato-de-Envio-608-(NG-07-2018-y-05-2019).zip",
    "609": "Formato609-NG-7-18.zip",
    "623": "FormatoenvioRetencionesEstado623.zip",
    "ITBIS": "FormatoExcelEnvioDatosITBIS.zip",
    "NORM-2-05": "FormatoExcelNORMA2-05RetencionesTerceros.zip",
}

HEADER_KEYWORDS = (
    "rnc", "ncf", "cedula", "cédula", "fecha", "monto", "itbis", "factura",
    "comprobante", "retencion", "retención", "tipo", "estatus", "no.",
    "número", "numero",
)


def unzip_all() -> None:
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    for zpath in sorted(TEMPLATES_DIR.glob("*.zip")):
        dest = EXTRACT_DIR / zpath.stem
        dest.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(zpath) as zf:
                zf.extractall(dest)
        except zipfile.BadZipFile:
            pass


def find_excel_files(folder: Path) -> list[Path]:
    exts = {".xls", ".xlsx", ".xlsm"}
    files = [p for p in folder.rglob("*") if p.suffix.lower() in exts]
    # Prefer non-duplicate encoding variants
    seen: dict[str, Path] = {}
    for f in sorted(files):
        key = re.sub(r"[^\w]", "", f.stem.lower())
        if key not in seen or len(f.name) < len(seen[key].name):
            seen[key] = f
    return list(seen.values())


def cell_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value).strip()


def score_header_row(cells: list[str]) -> int:
    text = " ".join(cells).lower()
    return sum(1 for kw in HEADER_KEYWORDS if kw in text)


def detect_header_row_xls(sheet, max_scan: int = 25) -> tuple[int, list[str]]:
    best_row, best_score, best_cells = 0, -1, []
    for r in range(min(max_scan, sheet.nrows)):
        cells = [cell_str(sheet.cell_value(r, c)) for c in range(sheet.ncols)]
        score = score_header_row(cells)
        non_empty = sum(1 for c in cells if c)
        if score > best_score and non_empty >= 3:
            best_score, best_row, best_cells = score, r, cells
    return best_row, best_cells


def detect_header_row_xlsx(ws, max_scan: int = 25) -> tuple[int, list[str]]:
    best_row, best_score, best_cells = 0, -1, []
    for r in range(1, min(max_scan, ws.max_row or 1) + 1):
        cells = []
        for c in range(1, (ws.max_column or 1) + 1):
            cells.append(cell_str(ws.cell(r, c).value))
        score = score_header_row(cells)
        non_empty = sum(1 for c in cells if c)
        if score > best_score and non_empty >= 3:
            best_score, best_row, best_cells = score, r, cells
    return best_row, best_cells


def infer_data_type(name: str, sample_values: list[str]) -> str:
    n = name.lower()
    if "fecha" in n:
        return "date"
    if any(k in n for k in ("monto", "itbis", "total", "valor", "importe", "retencion", "retención")):
        return "decimal"
    if "rnc" in n or "cedula" in n or "cédula" in n:
        return "identifier"
    if "ncf" in n or "comprobante" in n:
        return "ncf"
    if sample_values and all(v.isdigit() for v in sample_values if v):
        return "integer"
    return "string"


def infer_length(name: str, data_type: str) -> int | None:
    n = name.lower()
    if data_type == "identifier":
        if "cedula" in n or "cédula" in n:
            return 11
        return 9
    if data_type == "ncf":
        return 13
    if data_type == "date":
        return 8
    if data_type == "decimal":
        return 18
    return None


def infer_format(name: str, data_type: str) -> str | None:
    n = name.lower()
    if data_type == "date":
        if "aaaamm" in n or "periodo" in n:
            return "YYYYMM"
        return "YYYYMMDD"
    if data_type == "identifier":
        if "cedula" in n or "cédula" in n:
            return "###########"
        return "#########"
    if data_type == "ncf":
        return "B##NNNNNNNN"
    if data_type == "decimal":
        return "0.00"
    return None


def analyze_xls(path: Path) -> dict[str, Any]:
    book = xlrd.open_workbook(str(path), formatting_info=False)
    sheets_meta = []
    for si, name in enumerate(book.sheet_names()):
        sh = book.sheet_by_index(si)
        header_row, header_cells = detect_header_row_xls(sh)
        columns = []
        for ci, label in enumerate(header_cells):
            if not label:
                continue
            samples = []
            for r in range(header_row + 1, min(header_row + 6, sh.nrows)):
                samples.append(cell_str(sh.cell_value(r, ci)))
            dtype = infer_data_type(label, samples)
            columns.append({
                "orden": len(columns) + 1,
                "columna_excel": get_column_letter(ci + 1),
                "nombre_dgii": label,
                "tipo_dato": dtype,
                "longitud": infer_length(label, dtype),
                "formato": infer_format(label, dtype),
                "obligatorio": None,
                "muestra_valores": [s for s in samples if s][:3],
            })
        sheets_meta.append({
            "nombre": name,
            "filas": sh.nrows,
            "columnas": sh.ncols,
            "fila_encabezado": header_row + 1,
            "encabezados": [c["nombre_dgii"] for c in columns],
            "columnas_detalle": columns,
        })
    return {
        "archivo": path.name,
        "ruta": str(path),
        "formato": "xls",
        "hojas": sheets_meta,
        "macros": False,
        "formulas_detectadas": False,
    }


def analyze_xlsx(path: Path) -> dict[str, Any]:
    keep_vba = path.suffix.lower() == ".xlsm"
    wb = load_workbook(str(path), read_only=False, data_only=False, keep_vba=keep_vba)
    sheets_meta = []
    formula_count = 0
    for name in wb.sheetnames:
        ws = wb[name]
        header_row, header_cells = detect_header_row_xlsx(ws)
        columns = []
        for ci, label in enumerate(header_cells, start=1):
            if not label:
                continue
            samples = []
            for r in range(header_row + 1, min(header_row + 6, (ws.max_row or header_row) + 1)):
                samples.append(cell_str(ws.cell(r, ci).value))
            dtype = infer_data_type(label, samples)
            columns.append({
                "orden": len(columns) + 1,
                "columna_excel": get_column_letter(ci),
                "nombre_dgii": label,
                "tipo_dato": dtype,
                "longitud": infer_length(label, dtype),
                "formato": infer_format(label, dtype),
                "obligatorio": None,
                "muestra_valores": [s for s in samples if s][:3],
            })
        # Count formulas in first 50 rows
        for row in ws.iter_rows(min_row=1, max_row=min(50, ws.max_row or 1)):
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    formula_count += 1
        sheets_meta.append({
            "nombre": name,
            "filas": ws.max_row,
            "columnas": ws.max_column,
            "fila_encabezado": header_row,
            "encabezados": [c["nombre_dgii"] for c in columns],
            "columnas_detalle": columns,
        })
    return {
        "archivo": path.name,
        "ruta": str(path),
        "formato": path.suffix.lower().lstrip("."),
        "hojas": sheets_meta,
        "macros": keep_vba and bool(getattr(wb, "vba_archive", None)),
        "formulas_detectadas": formula_count > 0,
        "cantidad_formulas_muestra": formula_count,
    }


def analyze_excel(path: Path) -> dict[str, Any]:
    ext = path.suffix.lower()
    if ext == ".xls":
        return analyze_xls(path)
    return analyze_xlsx(path)


def pick_main_sheet(meta: dict[str, Any]) -> dict[str, Any]:
    sheets = meta["hojas"]
    if not sheets:
        return {}
    # Prefer sheet with most data columns and DGII keywords
    def score(s: dict) -> tuple[int, int]:
        hdr = " ".join(s.get("encabezados", [])).lower()
        kw = sum(1 for k in HEADER_KEYWORDS if k in hdr)
        return kw, len(s.get("columnas_detalle", []))
    return max(sheets, key=score)


def analyze_zip(zip_name: str) -> dict[str, Any]:
    folder = EXTRACT_DIR / Path(zip_name).stem
    excels = find_excel_files(folder)
    files_meta = [analyze_excel(p) for p in excels]
    main = None
    if files_meta:
        main = pick_main_sheet(files_meta[0])
        for fm in files_meta[1:]:
            candidate = pick_main_sheet(fm)
            if score_header_row(candidate.get("encabezados", [])) > score_header_row(main.get("encabezados", [])):
                main = candidate
                files_meta[0], fm = fm, files_meta[0]
    return {
        "zip": zip_name,
        "archivos_excel": len(excels),
        "analisis": files_meta,
        "hoja_principal": main.get("nombre") if main else None,
        "fila_encabezado": main.get("fila_encabezado") if main else None,
        "total_columnas_datos": len(main.get("columnas_detalle", [])) if main else 0,
    }


def main() -> None:
    unzip_all()
    templates_json = json.loads((TEMPLATES_DIR / "templates.json").read_text())
    plantillas = {p["archivo"]: p for p in templates_json["plantillas"]}

    summary: dict[str, Any] = {
        "fecha_analisis_utc": datetime.now(timezone.utc).isoformat(),
        "total_zips": len(list(TEMPLATES_DIR.glob("*.zip"))),
        "formatos": {},
    }

    for z in sorted(TEMPLATES_DIR.glob("*.zip")):
        info = analyze_zip(z.name)
        meta = plantillas.get(z.name, {})
        info["codigo_catalogo"] = meta.get("codigo")
        info["nombre_oficial"] = meta.get("nombre")
        info["version"] = meta.get("version")
        info["sha256"] = meta.get("sha256")
        summary["formatos"][z.name] = info

    OUTPUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Wrote {OUTPUT_SUMMARY}")
    print(f"Analyzed {len(summary['formatos'])} ZIP archives")


if __name__ == "__main__":
    main()
