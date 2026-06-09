"""Normalización de valores JSON-RPC Odoo → tipos Python/Pydantic."""

from __future__ import annotations

from decimal import Decimal
from typing import Any


def _is_empty(val: Any) -> bool:
    return val is False or val is None


def odoo_str(value: Any) -> str:
    """False/None → cadena vacía; nunca devuelve bool."""
    if _is_empty(value):
        return ""
    return str(value)


def odoo_str_opt(value: Any) -> str | None:
    """False/None/'' → None para campos opcionales."""
    if _is_empty(value):
        return None
    s = str(value).strip()
    return s or None


def odoo_bool(value: Any, *, default: bool = False) -> bool:
    if _is_empty(value):
        return default
    return bool(value)


def odoo_float(value: Any, *, default: float = 0.0) -> float:
    if _is_empty(value) or isinstance(value, bool):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def odoo_dec(value: Any) -> Decimal:
    if _is_empty(value):
        return Decimal("0")
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def odoo_date(value: Any) -> str | None:
    """Fechas Odoo: False → None, 'YYYY-MM-DD' truncado."""
    if _is_empty(value):
        return None
    s = str(value)
    return s[:10] if s else None


def odoo_m2o_name(val: Any) -> str:
    if isinstance(val, (list, tuple)) and len(val) >= 2:
        return odoo_str(val[1])
    if _is_empty(val):
        return ""
    return odoo_str(val)


def odoo_m2o_name_opt(val: Any) -> str | None:
    name = odoo_m2o_name(val)
    return name or None


def odoo_m2o_id(val: Any) -> int | None:
    if _is_empty(val) or isinstance(val, bool):
        return None
    if isinstance(val, (list, tuple)) and val:
        try:
            return int(val[0])
        except (TypeError, ValueError):
            return None
    if isinstance(val, int):
        return val
    return None


def odoo_m2m_ids(val: Any) -> list[int]:
    if _is_empty(val) or not isinstance(val, (list, tuple)):
        return []
    result: list[int] = []
    for item in val:
        if isinstance(item, int):
            result.append(item)
    return result
