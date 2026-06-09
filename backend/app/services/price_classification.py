"""Clasificación comercial estricta para Price Intelligence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from app.services.price_normalizer import normalize_header, parse_ram_gb, parse_storage

NON_LAPTOP_KEYWORDS = (
    "warranty",
    "warranties",
    "garantia",
    "garantía",
    "keep your hard drive",
    "keep your hd",
    "support",
    "service",
    "servicio",
    "licencia",
    "license",
    "renewal",
    "renewals",
    "cable",
    "adapter",
    "adaptador",
    "mouse",
    "keyboard",
    "teclado",
    "dock",
    "bag",
    "sleeve",
    "backpack",
    "mochila",
    "stand",
    "monitor",
    "montitor",
    "docking",
    "premier support",
    "care pack",
    "extended warranty",
    "prosupport",
    "accidental damage",
    "hard drive retention",
)

EXPLICIT_LAPTOP_KEYWORDS = (
    "laptop",
    "notebook",
    "portátil",
    "portatil",
    "pc portátil",
    "computadora portátil",
)

LAPTOP_MODEL_KEYWORDS = (
    "thinkpad",
    "thinkbook",
    "inspiron",
    "latitude",
    "vivobook",
    "ideapad",
    "pro 14",
    "pro 15",
    "pro 16",
    "v14",
    "v15",
    "x1 carbon",
    "alienware",
    "hp 15",
    "dell pro",
)

NON_LAPTOP_SHEET_PATTERN = re.compile(
    r"(?i)(warrant|garant|support|services?|accesor|accessor|parts?|cables?|licen|software|"
    r"renewal|monitor|montitor|desktop|loc\.?id|alloc|openpurchaseorder|summary|notes?|config|totals?|pivot)"
)

COTIZABLE_TYPES = frozenset({"laptop", "desktop", "monitor", "server", "general"})
NON_COTIZABLE_TYPES = frozenset({"warranty", "service", "license", "accessory"})


@dataclass(frozen=True)
class ProductClassification:
    product_type: str
    excluded_from_laptop: bool
    is_cotizable: bool
    price_review_status: str
    classification_label: str


def is_non_laptop_sheet(sheet_name: str | None) -> bool:
    if not sheet_name:
        return False
    return bool(NON_LAPTOP_SHEET_PATTERN.search(sheet_name.strip()))


def sheet_product_type_override(sheet_name: str | None) -> str | None:
    if not sheet_name:
        return None
    name = sheet_name.strip().lower()
    if "warrant" in name or "garant" in name:
        return "warranty"
    if "accesor" in name or "accessor" in name:
        return "accessory"
    if "monitor" in name or "montitor" in name:
        return "monitor"
    if "desktop" in name:
        return "desktop"
    if any(k in name for k in ("support", "service", "servicio")):
        return "service"
    if any(k in name for k in ("licen", "software")):
        return "license"
    return None


def contains_non_laptop_keyword(text: str) -> bool:
    blob = text.lower()
    return any(k in blob for k in NON_LAPTOP_KEYWORDS)


def _non_laptop_type_from_text(blob: str) -> str:
    if any(k in blob for k in ("license", "licencia", "software")):
        return "license"
    if any(k in blob for k in ("warranty", "garant", "keep your", "support", "service", "renewal", "care pack")):
        return "warranty"
    if any(k in blob for k in ("adapter", "dock", "mouse", "keyboard", "cable", "bag", "sleeve", "accesorio", "backpack", "mochila", "stand", "monitor", "montitor")):
        return "accessory"
    return "service"


def infer_product_type(
    description: str,
    category_raw: str | None = None,
    *,
    sheet_name: str | None = None,
) -> str:
    blob = f"{description} {category_raw or ''}".lower()

    sheet_type = sheet_product_type_override(sheet_name)
    if sheet_type:
        return sheet_type

    if contains_non_laptop_keyword(blob):
        return _non_laptop_type_from_text(blob)

    cat = normalize_header(category_raw or "")
    if any(k in cat for k in ("notebook", "laptop", "portatil", "portátil", "pc portatil")):
        return "laptop"

    if "monitor" in blob or "monitors" in blob or "montitor" in blob:
        return "monitor"
    if any(k in blob for k in ("desktop", "escritorio", "thinkcentre", "optiplex", "tower", "desktops")):
        return "desktop"
    if any(k in blob for k in ("server", "servidor", "poweredge")):
        return "server"

    if any(k in blob for k in EXPLICIT_LAPTOP_KEYWORDS) or "notebooks" in blob:
        return "laptop"

    if any(k in blob for k in LAPTOP_MODEL_KEYWORDS):
        if parse_ram_gb(description) or parse_storage(description)[0]:
            return "laptop"
        if re.search(r"\b\d+\s*gb\b", blob):
            return "laptop"

    if category_raw:
        raw = normalize_header(category_raw).replace(" ", "_")[:64]
        if "notebook" in raw:
            return "laptop"
        return raw
    return "general"


def is_laptop_product(
    description: str | None,
    category: str | None = None,
    product_type: str | None = None,
    *,
    source_sheet: str | None = None,
    excluded_from_laptop: bool | None = None,
    ram_gb: int | None = None,
    storage_gb: int | None = None,
) -> bool:
    if excluded_from_laptop:
        return False
    if is_non_laptop_sheet(source_sheet):
        return False
    if product_type and product_type not in ("laptop",):
        return False
    blob = " ".join(str(p).lower() for p in (description, category) if p)
    if contains_non_laptop_keyword(blob):
        return False
    if product_type == "laptop":
        return True
    return infer_product_type(description or "", category, sheet_name=source_sheet) == "laptop"


def classify_product(
    *,
    description: str | None,
    category: str | None,
    sheet_name: str | None,
    preferred_price: Decimal | None,
    preferred_price_field: str | None,
) -> ProductClassification:
    desc = description or ""
    blob = desc.lower()

    if is_non_laptop_sheet(sheet_name):
        product_type = sheet_product_type_override(sheet_name) or "service"
    elif contains_non_laptop_keyword(blob):
        product_type = _non_laptop_type_from_text(blob)
    else:
        product_type = infer_product_type(desc, category, sheet_name=sheet_name)

    is_true_laptop = (
        product_type == "laptop"
        and not is_non_laptop_sheet(sheet_name)
        and not contains_non_laptop_keyword(blob)
        and _passes_strict_laptop_rules(desc, category, sheet_name)
    )
    if product_type == "laptop" and not is_true_laptop:
        product_type = "general"

    excluded_from_laptop = not is_true_laptop

    price_status = "ok"
    if preferred_price is None or not preferred_price_field:
        price_status = "requires_review"
    elif is_non_laptop_sheet(sheet_name):
        price_status = "requires_review"

    is_cotizable = (
        is_true_laptop
        or (
            product_type in COTIZABLE_TYPES
            and not is_non_laptop_sheet(sheet_name)
            and product_type not in NON_COTIZABLE_TYPES
        )
    ) and preferred_price is not None and price_status == "ok"

    if is_true_laptop:
        label = "producto cotizable"
    elif product_type in NON_COTIZABLE_TYPES:
        label = {
            "warranty": "garantía / servicio",
            "service": "servicio",
            "license": "licencia",
            "accessory": "accesorio",
        }.get(product_type, product_type)
    elif excluded_from_laptop:
        label = "excluido de comparación laptop"
    else:
        label = "producto cotizable" if product_type in COTIZABLE_TYPES else "producto general"

    return ProductClassification(
        product_type="laptop" if is_true_laptop else product_type,
        excluded_from_laptop=excluded_from_laptop,
        is_cotizable=is_cotizable,
        price_review_status=price_status,
        classification_label=label,
    )


def _passes_strict_laptop_rules(description: str, category: str | None, sheet_name: str | None) -> bool:
    blob = f"{description} {category or ''}".lower()
    if contains_non_laptop_keyword(blob):
        return False
    if any(k in blob for k in EXPLICIT_LAPTOP_KEYWORDS) or "notebooks" in blob:
        return True
    cat = normalize_header(category or "")
    if any(k in cat for k in ("notebook", "laptop", "portatil", "portátil")):
        return True
    if any(k in blob for k in LAPTOP_MODEL_KEYWORDS):
        return bool(parse_ram_gb(description) or parse_storage(description)[0] or re.search(r"\b\d+\s*gb\b", blob))
    return False
