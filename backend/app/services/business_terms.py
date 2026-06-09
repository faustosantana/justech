"""Diccionario empresarial y expansión de sinónimos para el Assistant."""

from __future__ import annotations

import re

PRODUCT_SYNONYMS: dict[str, list[str]] = {
    "teclado": ["teclado", "teclados", "keyboard", "keyboards"],
    "laptop": ["laptop", "laptops", "notebook", "notebooks", "portátil", "portatil", "portable"],
    "computadora": [
        "computadora", "computadoras", "pc", "desktop", "equipo", "equipos", "workstation",
        "ordenador", "ordenadores", "laptop", "laptops", "notebook", "notebooks", "portátil", "portatil", "portable",
    ],
    "monitor": ["monitor", "monitores", "pantalla", "pantallas", "display"],
    "licencia": [
        "licencia", "licencias", "license", "suscripción", "suscripcion",
        "microsoft 365", "office 365", "office365", "m365", "teams", "exchange",
        "business basic", "business standard", "microsoft teams",
    ],
    "microsoft": ["microsoft", "m365", "office 365", "office365", "microsoft 365"],
    "impresora": ["impresora", "impresoras", "multifuncional", "toner", "tóner", "printer"],
    "fortinet": ["fortigate", "fortinet", "firewall"],
    "dell": ["dell"],
    "hp": ["hp", "hewlett"],
    "lenovo": ["lenovo"],
    "papel": [
        "papel", "papeles", "rollo papel", "rollo de papel", "rollos de papel", "rollos papel",
        "papel térmico", "papel termico", "papel bond", "papel impresora", "papel para impresora",
        "resma", "resmas", "caja de papel", "cajas de papel", "paquete de papel", "paquetes de papel",
        "papel 350", "papel 365", "rollo 350", "rollo térmico", "rollo termico", "rollo térmico 350",
        "350", "365", "350ft", "350 pies",
    ],
    "rollo": [
        "rollo", "rollos", "rollo papel", "rollos papel", "rollo térmico", "rollo termico",
        "rollos térmicos", "rollos termicos",
    ],
    "fardo": [
        "fardo", "fardos", "falda", "faldos", "faldo", "faldos de papel",
        "fardos de papel",
    ],
}

CUSTOMER_ALIASES: dict[str, list[str]] = {
    "farma trix": ["farma trix", "farmatrix", "farma-trix", "farma triz", "farmtrix", "farma trix srl"],
    "banco ademi": ["banco ademi", "ademi", "banco múltiple ademi", "banco multiple ademi", "banco ademi s a"],
    "capital dbg": ["capital dbg", "capital", "dbg", "capital digital business group"],
}

BRAND_TERMS = ("dell", "hp", "lenovo", "fortigate", "fortinet", "microsoft")

KNOWN_PRODUCT_KEYS = tuple(PRODUCT_SYNONYMS.keys())


def normalize_question(question: str) -> str:
    q = question.strip()
    if q.startswith("¿"):
        q = q[1:].strip()
    return q.rstrip("?").strip()


def clean_entity(raw: str | None) -> str | None:
    if not raw:
        return None
    text = raw.strip().rstrip("?.")
    text = re.sub(r"^(?:de|del|la|el|los|las)\s+", "", text, flags=re.I)
    text = re.sub(r"^(?:a|para)\s+", "", text, flags=re.I)
    return text.strip() or None


def expand_customer_terms(raw: str | None) -> list[str]:
    if not raw:
        return []
    text = raw.lower().strip().rstrip("?.")
    terms = [text]
    for canonical, aliases in CUSTOMER_ALIASES.items():
        if any(a in text or text in a for a in aliases) or canonical in text:
            terms.extend(aliases)
            terms.append(canonical)
            break
    for token in re.split(r"[\s,/\-]+", text):
        if len(token) >= 3 and token not in terms:
            terms.append(token)
    return _dedupe_terms(terms)


def _dedupe_terms(terms: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for t in terms:
        t = t.strip()
        if t and t not in seen:
            seen.add(t)
            ordered.append(t)
    return ordered


def expand_product_terms(raw: str | None) -> list[str]:
    if not raw:
        return []
    text = raw.lower().strip().rstrip("?.")
    terms: list[str] = [text]
    if text.endswith("s") and len(text) > 3:
        terms.append(text[:-1])

    for _key, syns in PRODUCT_SYNONYMS.items():
        if any(s in text for s in syns):
            terms.extend(syns)
            break

    for brand in BRAND_TERMS:
        if brand in text:
            terms.append(brand)

    for token in re.split(r"[\s,/]+", text):
        if len(token) >= 2 and token not in terms:
            terms.append(token)

    return _dedupe_terms(terms)


def detect_product_in_text(text: str) -> tuple[str | None, list[str]]:
    """Detecta producto mencionado en texto libre."""
    lowered = text.lower()
    best_label: str | None = None
    best_terms: list[str] = []

    for _key, syns in PRODUCT_SYNONYMS.items():
        for syn in sorted(syns, key=len, reverse=True):
            if syn in lowered:
                label = clean_entity(syn) or syn
                terms = expand_product_terms(label)
                if len(syn) > len(best_label or ""):
                    best_label = label
                    best_terms = terms

    if best_label:
        return best_label, best_terms

    tokens = [t for t in re.split(r"[\s,?]+", lowered) if len(t) >= 3]
    stop = {
        "hemos", "vendido", "vendidos", "vendimos", "cuanto", "cuánto", "cuantas",
        "cuántas", "clientes", "compraron", "licitaciones", "licitacion", "tareas",
        "pendiente", "proveedor", "compramos", "banco", "ademi", "farma", "trix",
        "le", "les", "rollos", "rollos", "fardos", "faldos", "unidades",
    }
    for token in tokens:
        if token not in stop and not token.isdigit():
            label = clean_entity(token)
            if label:
                return label, expand_product_terms(label)

    return None, []


def matches_product_name(name: str, terms: list[str], *, filter_terms: list[str] | None = None) -> bool:
    if not terms and not filter_terms:
        return True
    lowered = (name or "").lower()
    filters = filter_terms or [
        t for t in terms if len(t) >= 3 or t.isdigit()
    ]
    stop = {"de", "del", "la", "el", "los", "las", "un", "una", "hemos", "vendido", "vendidos", "rollos", "fardos", "faldos", "unidades"}
    filters = [t for t in filters if t not in stop][:6]
    if not filters:
        return any(term in lowered for term in terms)

    digit_filters = [t for t in filters if t.isdigit()]
    text_filters = [t for t in filters if not t.isdigit() and len(t) >= 3]

    if digit_filters and not any(d in lowered for d in digit_filters):
        return False

    if text_filters:
        return any(token in lowered for token in text_filters)

    return any(term in lowered for term in terms)
