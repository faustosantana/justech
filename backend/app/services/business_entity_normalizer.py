"""Normalización semántica de productos y clientes para el Assistant empresarial."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.business_terms import (
    CUSTOMER_ALIASES,
    PRODUCT_SYNONYMS,
    clean_entity,
    expand_customer_terms,
    expand_product_terms,
)


@dataclass
class NormalizedProduct:
    label: str
    search_terms: list[str]
    filter_terms: list[str]
    variants_display: list[str] = field(default_factory=list)


@dataclass
class NormalizedCustomer:
    label: str
    search_terms: list[str]
    variants_display: list[str] = field(default_factory=list)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


def _match_customer_alias(text: str) -> tuple[str | None, list[str]]:
    lowered = text.lower().strip()
    for canonical, aliases in CUSTOMER_ALIASES.items():
        for alias in aliases:
            if alias in lowered or lowered in alias:
                return canonical.title(), _dedupe(aliases)
    return None, []


def normalize_customer(raw: str | None) -> NormalizedCustomer | None:
    label = clean_entity(raw)
    if not label:
        return None
    canonical, alias_variants = _match_customer_alias(label)
    display_label = canonical or label
    terms = expand_customer_terms(display_label)
    if alias_variants:
        terms = _dedupe(terms + alias_variants)
    variants = _dedupe([display_label] + alias_variants + terms)[:10]
    return NormalizedCustomer(label=display_label, search_terms=terms, variants_display=variants)


def _extract_spec_tokens(text: str) -> list[str]:
    return re.findall(r"\d{2,4}", text)


def normalize_product(raw: str | None) -> NormalizedProduct | None:
    label = clean_entity(raw)
    if not label:
        return None
    lowered = label.lower()
    terms = expand_product_terms(label)
    variants: list[str] = [label]

    for _key, syns in PRODUCT_SYNONYMS.items():
        if any(s in lowered for s in syns):
            variants.extend(syns[:6])
            break

    specs = _extract_spec_tokens(label)
    if specs:
        base = re.sub(r"\d{2,4}", "", lowered).strip()
        for spec in specs:
            variants.append(f"{base} {spec}".strip())
            variants.append(spec)
        if "papel" in lowered or any("papel" in t for t in terms):
            for spec in specs:
                variants.extend([
                    f"papel {spec}",
                    f"rollo papel {spec}",
                    f"papel térmico {spec}",
                    f"papel bond {spec}",
                    f"papel termico {spec}",
                ])

    terms = _dedupe(terms + variants)
    filter_terms = [
        t for t in terms
        if len(t) >= 3 or t.isdigit()
    ]
    filter_stop = {"hemos", "vendido", "vendidos", "rollos", "rollos", "fardos", "faldos", "unidades"}
    filter_terms = [t for t in filter_terms if t not in filter_stop][:5]

    return NormalizedProduct(
        label=label,
        search_terms=terms[:20],
        filter_terms=filter_terms or terms[:5],
        variants_display=_dedupe(variants)[:12],
    )


def format_variants_list(variants: list[str], limit: int = 8) -> str:
    if not variants:
        return "—"
    shown = variants[:limit]
    text = ", ".join(f"«{v}»" for v in shown)
    if len(variants) > limit:
        text += f" (+{len(variants) - limit} más)"
    return text
