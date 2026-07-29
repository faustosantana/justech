"""Official Lottery Scope — single source of truth for Lottery IA conversational analysis.

Product universe = the 7 enabled lotteries (see frontend PRODUCT_SEVEN_LOTTERY_NAMES
and docs/lottery numeric_relations J10H catalog). Stored history may contain ~50
lotteries; they are never mixed into Analyst answers unless this scope is extended.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable

# Canonical product names (aliases resolve via LotteryResolver / _ALIAS_TO_CANONICAL).
# Order matches product dashboard conventions where practical.
OFFICIAL_LOTTERY_SCOPE: tuple[str, ...] = (
    "Gana Más",
    "Nacional",  # → Loteria Nacional
    "New York 10:30",
    "New York 2:30",
    "Leidsa",  # → Quiniela Leidsa
    "Loteka",  # → Quiniela Loteka
    "Real",  # → Quiniela Real
)

# DB catalog names (authoritative for SQL / is_featured checks)
OFFICIAL_LOTTERY_DB_NAMES: tuple[str, ...] = (
    "Gana Mas",
    "Loteria Nacional",
    "New York 10:30",
    "New York 2:30",
    "Quiniela Leidsa",
    "Quiniela Loteka",
    "Quiniela Real",
)

OFFICIAL_LOTTERY_SCOPE_VERSION = "1.1.0"

# Aliases → canonical scope name (keys via _norm)
_ALIAS_TO_CANONICAL: dict[str, str] = {
    # Gana Más (all accent/spacing variants fold via _norm)
    "gana mas": "Gana Más",
    "ganamas": "Gana Más",
    "gana-mas": "Gana Más",
    "gana_mas": "Gana Más",
    # Nacional / Lotería Nacional
    "nacional": "Nacional",
    "loteria nacional": "Nacional",
    "lotería nacional": "Nacional",
    # New York (product “Nacional Día/Noche” informal → NY draws)
    "new york 10:30": "New York 10:30",
    "new york 10 30": "New York 10:30",
    "ny 10:30": "New York 10:30",
    "ny 10 30": "New York 10:30",
    "ny noche": "New York 10:30",
    "new york noche": "New York 10:30",
    "new york 2:30": "New York 2:30",
    "new york 2 30": "New York 2:30",
    "ny 2:30": "New York 2:30",
    "ny 2 30": "New York 2:30",
    "ny dia": "New York 2:30",
    "new york dia": "New York 2:30",
    "nacional dia": "New York 2:30",
    "nacional noche": "Nacional",
    # Quinielas
    "leidsa": "Leidsa",
    "quiniela leidsa": "Leidsa",
    "loteka": "Loteka",
    "quiniela loteka": "Loteka",
    "real": "Real",
    "quiniela real": "Real",
    "loteria real": "Real",
}


def _norm(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", (text or "").lower().strip())
    bare = "".join(c for c in nfkd if not unicodedata.combining(c))
    bare = bare.replace(".", " ").replace(":", " ").replace("_", " ").replace("-", " ")
    bare = re.sub(r"\s+", " ", bare).strip()
    # Collapse spaceless ganamas already covered; also strip spaces for compact alias lookup
    return bare


def official_lottery_names() -> list[str]:
    return list(OFFICIAL_LOTTERY_SCOPE)


def official_db_names() -> list[str]:
    return list(OFFICIAL_LOTTERY_DB_NAMES)


def official_scope_count() -> int:
    return len(OFFICIAL_LOTTERY_SCOPE)


def scope_label_es(*, short: bool = False) -> str:
    n = official_scope_count()
    if short:
        return f"{n} loterías habilitadas"
    return f"las {n} loterías habilitadas del sistema"


def canonicalize_lottery_name(name: str | None) -> str | None:
    if not name:
        return None
    raw = str(name).strip()
    if raw in OFFICIAL_LOTTERY_SCOPE:
        return raw
    if raw in OFFICIAL_LOTTERY_DB_NAMES:
        # Map DB → scope alias
        idx = OFFICIAL_LOTTERY_DB_NAMES.index(raw)
        return OFFICIAL_LOTTERY_SCOPE[idx]
    key = _norm(raw)
    if key in _ALIAS_TO_CANONICAL:
        return _ALIAS_TO_CANONICAL[key]
    compact = key.replace(" ", "")
    if compact in _ALIAS_TO_CANONICAL:
        return _ALIAS_TO_CANONICAL[compact]
    for canon in OFFICIAL_LOTTERY_SCOPE:
        if _norm(canon) == key:
            return canon
    for dbn in OFFICIAL_LOTTERY_DB_NAMES:
        if _norm(dbn) == key:
            idx = OFFICIAL_LOTTERY_DB_NAMES.index(dbn)
            return OFFICIAL_LOTTERY_SCOPE[idx]
    return None


def is_official_lottery(name: str | None) -> bool:
    return canonicalize_lottery_name(name) is not None


def resolve_query_lotteries(
    lotteries: Iterable[str] | None = None,
    *,
    allow_empty_as_official: bool = True,
) -> list[str]:
    """Return official-only lottery names for a query (scope aliases).

    - None / empty → full OFFICIAL_LOTTERY_SCOPE (when allow_empty_as_official).
    - Explicit list → keep only official names (canonicalized, order preserved).
    """
    names = [str(x).strip() for x in (lotteries or []) if str(x).strip()]
    if not names:
        return official_lottery_names() if allow_empty_as_official else []
    out: list[str] = []
    for n in names:
        canon = canonicalize_lottery_name(n)
        if canon and canon not in out:
            out.append(canon)
    return out


def reject_non_official(lotteries: Iterable[str] | None) -> list[str]:
    rejected: list[str] = []
    for n in lotteries or []:
        if str(n).strip() and not is_official_lottery(str(n)):
            rejected.append(str(n).strip())
    return rejected


def external_lottery_message(name: str) -> str:
    label = ", ".join(
        (
            "Gana Más",
            "Lotería Nacional",
            "New York 10:30",
            "New York 2:30",
            "Quiniela Leidsa",
            "Quiniela Loteka",
            "Quiniela Real",
        )
    )
    return (
        f"«{name}» no forma parte de las {official_scope_count()} loterías habilitadas "
        f"({label}). "
        "Indica una lotería del catálogo oficial o pregunta sin filtrar por lotería."
    )


def evidence_uses_non_official_lotteries(evidence: dict[str, Any] | None) -> bool:
    if not evidence or not isinstance(evidence, dict):
        return False
    names: list[str] = []
    vals = evidence.get("lotteries") or []
    if isinstance(vals, list):
        names.extend(str(x) for x in vals if x)
    last = evidence.get("last") if isinstance(evidence.get("last"), dict) else {}
    if last.get("lottery"):
        names.append(str(last["lottery"]))
    for e in last.get("appearances") or last.get("entries") or []:
        if isinstance(e, dict) and e.get("lottery"):
            names.append(str(e["lottery"]))
    for it in evidence.get("items") or []:
        if not isinstance(it, dict):
            continue
        if it.get("lottery"):
            names.append(str(it["lottery"]))
        for e in it.get("appearances") or it.get("entries") or []:
            if isinstance(e, dict) and e.get("lottery"):
                names.append(str(e["lottery"]))
    return any(not is_official_lottery(n) for n in names)


def replace_global_lottery_phrasing(text: str) -> str:
    if not text:
        return text
    out = re.sub(
        r"\ben todas las loter[ií]as\b",
        f"en {scope_label_es()}",
        text,
        flags=re.I,
    )
    out = re.sub(
        r"\btodas las loter[ií]as\b",
        scope_label_es(),
        out,
        flags=re.I,
    )
    return out
