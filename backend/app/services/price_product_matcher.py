"""Product Matching Engine — listas indexadas (sin conectores live)."""

from __future__ import annotations

import re

from app.services.price_intelligence_service import PriceSearchFilters
from app.services.price_normalizer import parse_ram_gb, parse_storage

MODEL_PATTERNS = (
    re.compile(r"\blatitude\s*(\d{3,5})\b", re.I),
    re.compile(r"\boptiplex\s*(\d{3,5})\b", re.I),
    re.compile(r"\bthink(?:pad|book)\s*(\w+)?\s*(\d{3,5})?\b", re.I),
    re.compile(r"\belitebook\s*(\d{3,5})?\b", re.I),
    re.compile(r"\bpro\s*(\d{1,2})\b", re.I),
    re.compile(r"\bpoweredge\s*(\w+)\b", re.I),
)

DISPLAY_RE = re.compile(r'\b(\d{1,2}(?:\.\d)?)\s*["\']?\s*(?:pulg|inch|")\b', re.I)
QTY_RE = re.compile(
    r"\b(\d{1,5})\s*(?:und|unid|unidades|equipos|pcs|piezas|laptops?|notebooks?|portátiles?|portatiles?|monitores?)\b",
    re.I,
)

LAPTOP_SYNONYMS = frozenset({"laptop", "laptops", "notebook", "notebooks", "portatil", "portátil", "portátiles"})

ALTERNATIVE_BRANDS: dict[str, list[str]] = {
    "dell": ["lenovo", "hp", "acer", "asus"],
    "lenovo": ["dell", "hp", "acer"],
    "hp": ["dell", "lenovo", "acer"],
}


def extract_model_keys(text: str) -> list[str]:
    keys: list[str] = []
    lower = text.lower()
    for pat in MODEL_PATTERNS:
        for m in pat.finditer(lower):
            parts = [p for p in m.groups() if p]
            if parts:
                keys.append(f"{pat.pattern.split(chr(92))[0].strip('(')}:{':'.join(parts)}".lower())
    nums = re.findall(r"\b(\d{4,5})\b", lower)
    for n in nums:
        if n not in {k.split(":")[-1] for k in keys}:
            keys.append(f"model:{n}")
    return list(dict.fromkeys(keys))


def normalize_search_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def parse_requirement_line(text: str) -> dict:
    """Extrae cantidad y specs desde texto de licitación o consulta."""
    lower = text.lower()
    qty = 1
    m = QTY_RE.search(lower)
    if m:
        qty = int(m.group(1))

    ram = parse_ram_gb(text)
    storage, _ = parse_storage(text)

    display = None
    dm = DISPLAY_RE.search(text)
    if dm:
        display = f'{dm.group(1)}"'

    product_type = None
    if any(w in lower for w in LAPTOP_SYNONYMS):
        product_type = "laptop"
    elif "monitor" in lower:
        product_type = "monitor"
    elif "servidor" in lower or "poweredge" in lower:
        product_type = "server"

    brand = None
    for b in ("dell", "lenovo", "hp", "hpe", "cisco", "microsoft", "samsung"):
        if b in lower:
            brand = b.title() if b != "hp" else "HP"
            break

    return {
        "quantity": qty,
        "ram_gb": ram,
        "storage_gb": storage,
        "display": display,
        "product_type": product_type,
        "brand": brand,
        "model_keys": extract_model_keys(text),
        "raw": text.strip(),
    }


def filters_from_requirement(text: str, *, limit: int = 50) -> PriceSearchFilters:
    parsed = parse_requirement_line(text)
    q = parsed["raw"]
    if parsed["model_keys"] and not parsed["product_type"]:
        q = parsed["model_keys"][0].split(":")[-1]

    return PriceSearchFilters(
        q=q if not parsed["product_type"] else (parsed["product_type"] if parsed["product_type"] == "laptop" else q),
        brand=parsed["brand"],
        product_type=parsed["product_type"],
        ram_gb=parsed["ram_gb"],
        storage_gb=parsed["storage_gb"],
        display=parsed["display"],
        commercial_only=True,
        limit=limit,
    )


def extract_dgcp_line_items(*texts: str) -> list[dict]:
    """Detecta líneas de producto en título/descripción DGCP."""
    combined = "\n".join(t for t in texts if t)
    items: list[dict] = []
    seen: set[str] = set()

    patterns = [
        QTY_RE,
        re.compile(
            r"\b(\d{1,5})\s+(?:laptops?|notebooks?|equipos\s+port[aá]tiles?|computadoras?)\b",
            re.I,
        ),
        re.compile(r"\b(\d{1,5})\s+monitores?\b", re.I),
    ]
    for line in combined.splitlines():
        line = line.strip()
        if len(line) < 8:
            continue
        for pat in patterns:
            m = pat.search(line)
            if m:
                key = normalize_search_text(line)
                if key in seen:
                    break
                seen.add(key)
                parsed = parse_requirement_line(line)
                items.append({"label": line[:200], **parsed})
                break

    if not items:
        parsed = parse_requirement_line(combined[:2000])
        if parsed["product_type"] or parsed["ram_gb"] or parsed["model_keys"]:
            items.append({"label": combined[:120].strip(), **parsed})

    return items[:8]
