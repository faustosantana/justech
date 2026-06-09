"""Normalización de campos para Price Intelligence."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

RAM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(gb|mb|tb)?", re.IGNORECASE)
STORAGE_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(gb|tb|mb)?\s*(ssd|nvme|hdd|pcie|sata)?",
    re.IGNORECASE,
)
PRICE_RE = re.compile(r"[\d,]+\.?\d*")
CURRENCY_HINTS = {
    "US$": "USD",
    "USD": "USD",
    "RD$": "DOP",
    "DOP": "DOP",
}

RAM_MAX_GB = 512
STORAGE_MAX_GB = 8192

BRAND_KEYWORDS: dict[str, str] = {
    "dell": "Dell",
    "hp": "HP",
    "hewlett": "HP",
    "lenovo": "Lenovo",
    "asus": "Asus",
    "acer": "Acer",
    "fortinet": "Fortinet",
    "ubiquiti": "Ubiquiti",
    "microsoft": "Microsoft",
    "samsung": "Samsung",
}


def normalize_header(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower())


def parse_ram_gb(raw: object) -> int | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    m = RAM_RE.search(text.replace(",", ""))
    if not m:
        return None
    val = float(m.group(1))
    unit = (m.group(2) or "").lower()
    if not unit:
        if int(round(val)) not in {4, 8, 16, 32, 64, 128, 256, 512}:
            return None
        unit = "gb"
    if unit == "mb":
        val = val / 1024
    elif unit == "tb":
        val = val * 1024
    gb = int(round(val))
    if gb <= 0 or gb > RAM_MAX_GB:
        return None
    return gb


def parse_storage(raw: object) -> tuple[int | None, str | None]:
    if raw is None:
        return None, None
    text = str(raw).strip()
    if not text:
        return None, None
    cleaned = text.replace(",", "")
    matches = list(STORAGE_RE.finditer(cleaned))
    if not matches:
        return None, None

    candidates: list[tuple[int, str | None, int]] = []
    for m in matches:
        val = float(m.group(1))
        unit = (m.group(2) or "gb").lower()
        storage_type = (m.group(3) or "").upper() or None
        if unit == "tb":
            val *= 1024
        elif unit == "mb":
            val /= 1024
        gb = int(round(val))
        if storage_type in ("SSD", "NVME", "PCIE"):
            storage_type = "SSD"
        elif storage_type == "HDD":
            storage_type = "HDD"
        score = gb
        if storage_type:
            score += 10_000
        if unit == "tb" or gb >= 128:
            score += 5_000
        candidates.append((gb, storage_type, score))

    gb, storage_type, _ = max(candidates, key=lambda item: item[2])
    if gb <= 0 or gb > STORAGE_MAX_GB:
        return None, storage_type
    return gb, storage_type


PRICE_MAX = Decimal("99999999.99")
PRICE_MIN = Decimal("0.01")


def parse_price(raw: object, *, default_currency: str = "USD") -> tuple[Decimal | None, str]:
    if raw is None:
        return None, default_currency
    if isinstance(raw, (int, float, Decimal)):
        val = Decimal(str(round(float(raw), 2)))
        if val < PRICE_MIN or val > PRICE_MAX:
            return None, default_currency
        return val, default_currency
    text = str(raw).strip()
    if not text:
        return None, default_currency
    currency = default_currency
    upper = text.upper()
    for hint, code in CURRENCY_HINTS.items():
        if hint in upper:
            currency = code
            break
    cleaned = re.sub(r"[^\d.,]", "", text.replace(",", ""))
    if not cleaned:
        return None, currency
    try:
        val = Decimal(cleaned).quantize(Decimal("0.01"))
        if val < PRICE_MIN or val > PRICE_MAX:
            return None, currency
        return val, currency
    except InvalidOperation:
        return None, currency


def parse_int_quantity(raw: object) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    text = str(raw).strip()
    if not text or text.lower() in ("n/a", "-", "—"):
        return None
    m = re.search(r"-?\d+", text.replace(",", ""))
    return int(m.group()) if m else None


def detect_brand(*parts: object) -> str | None:
    blob = " ".join(str(p).lower() for p in parts if p)
    for key, label in BRAND_KEYWORDS.items():
        if key in blob:
            return label
    return None


def detect_supplier_from_path(relative_path: str, filename: str) -> str | None:
    parts = relative_path.replace("\\", "/").split("/")
    if len(parts) >= 2 and parts[0].startswith("03_"):
        sub = parts[1].replace("_", " ").title()
        if sub.upper() not in ("ENTRADAS", "PROCESADOS", "LISTAS PRECIOS"):
            return sub
    brand = detect_brand(filename)
    return brand


def infer_category(description: str, category_raw: str | None) -> str:
    from app.services.price_classification import infer_product_type

    return infer_product_type(description, category_raw)


LAPTOP_KEYWORDS = (
    "notebook", "laptop", "portátil", "portatil", "thinkpad", "thinkbook",
    "inspiron", "latitude", "vivobook", "ideapad",
)


def build_search_blob(*parts: object) -> str:
    return " ".join(str(p) for p in parts if p).lower()
