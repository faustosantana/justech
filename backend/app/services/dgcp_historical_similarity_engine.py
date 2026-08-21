"""Motor de similitud para histórico de adjudicaciones DGCP."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal

# Sinónimos comunes en compras públicas RD (rubro TI y suministros)
SYNONYM_GROUPS: list[set[str]] = [
    {"laptop", "laptops", "portatil", "portátil", "notebook", "computadora", "portable"},
    {"desktop", "pc", "computador", "escritorio", "torre"},
    {"servidor", "server", "servidores"},
    {"impresora", "printer", "multifuncional", "imagen", "imageclass"},
    {"toner", "tóner", "toners", "cartucho", "cartuchos", "tinta", "consumible", "consumibles"},
    {"hp", "hewlett", "packard", "canon", "lexmark", "brother", "epson", "xerox", "ricoh"},
    {"licencia", "licencias", "software", "suscripcion", "suscripción"},
    {"mantenimiento", "soporte", "servicio"},
    {"papel", "resma", "resmas", "oficina"},
    {"medicamento", "farmaco", "fármaco", "insumo", "medico", "médico"},
    {"vehiculo", "vehículo", "automovil", "automóvil", "camioneta"},
    {"aire", "acondicionado", "split", "hvac"},
    {"cafe", "café", "bebida"},
    {"switch", "switches", "router", "routers", "fortinet", "fortigate", "firewall", "cisco"},
    {"insumo", "insumos", "enfermeria", "enfermería", "glucosa"},
]

STOPWORDS = {
    "de", "la", "el", "los", "las", "un", "una", "para", "por", "con", "sin", "del", "al", "en", "y", "o",
    "adquisicion", "adquisición", "compra", "suministro", "contratacion", "contratación", "servicio", "servicios",
}

# Términos genéricos de procesos DGCP — no definen el rubro del producto
PROCESS_GENERIC_TOKENS = {
    "mipymes", "mipyme", "dirigido", "institucion", "dependencia", "dependencias", "diferentes",
    "bienes", "uso", "entidad", "proceso", "publico", "publica", "contratacion", "contratación",
    "adquisicion", "adquisición", "suministro", "suministros", "servicio", "servicios", "contrato",
    "licitacion", "licitación", "oferta", "ofertas", "proveedor", "proveedores", "estado",
    "nacional", "general", "ministerio", "direccion", "dirección", "departamento", "unidad",
    "area", "área", "requerimiento", "requerimientos", "articulo", "artículo", "articulos",
    "artículos", "item", "items", "linea", "línea", "lineas", "líneas",
}

# Penalización extra para «Procesos similares» (otras instituciones)
GENERIC_MATCH_TOKENS = PROCESS_GENERIC_TOKENS | {
    "materiales", "material", "certificacion", "certificación", "registro", "economica", "económica",
    "legal", "equipo", "equipos", "insumo", "insumos", "red", "network", "obsolescencia",
    "profesionales", "entrega", "solicitud", "control", "centro", "manipulacion", "manipulación",
    "grafico", "gráfico", "compra", "compras", "adjudicacion", "adjudicación", "generales", "general",
}

TECHNICAL_FAMILIES: dict[str, set[str]] = {
    "networking": {
        "switch", "switches", "router", "routers", "fortinet", "fortigate", "firewall", "cisco",
        "access", "punto", "wifi", "redes", "networking",
    },
    "printers": {"impresora", "impresoras", "printer", "multifuncional", "ecotank", "laserjet"},
    "laptops": {"laptop", "laptops", "notebook", "portatil", "portátil", "computadora"},
    "servers": {"servidor", "servidores", "server", "poweredge"},
    "monitors": {"monitor ", "monitores", "pantalla", "display"},
    "flags": {"bandera", "banderas", "sublimada", "estandarte"},
    "medical_supplies": {
        "guante", "guantes", "mascarilla", "nebulizar", "glucosa", "electrodo", "esteril",
        "nitrile", "nitrilo", "insumo", "insumos", "enfermeria", "enfermería",
    },
    "ferreteria": {
        "coupling", "pvc", "tornillo", "martillo", "llave", "herramienta", "ferreteria",
        "ferretería", "cemento", "broca", "taladro", "tomacorriente", "sifon", "llave",
    },
    "advertising": {
        "vallas", "valla", "publicidad", "pantalla", "pantallas", "led", "digital", "mupi",
        "marbete", "mobiliario", "alquiler", "exterior", "gran", "formato",
    },
    "toners": {"toner", "tóner", "cartucho", "cartuchos", "tinta"},
    "glucose_monitoring": {"glucosa", "monitoreo", "tiras", "lanceta", "glucometro", "glucómetro"},
}

PLUMBING_PRESSURE_TERMS = {
    "presion", "presión", "preion", "manometro", "manómetro", "glicerina", "psi", "utwps", "neumatico",
    "bomba", "automatico", "automático", "genebre",
}

NETWORKING_ANCHOR_TERMS = {
    "fortinet", "fortigate", "firewall", "router", "routers", "cisco", "puertos", "gigabit", "poe", "vpn",
}

INCOMPATIBLE_FAMILY_PAIRS: set[frozenset[str]] = {
    frozenset({"networking", "printers"}),
    frozenset({"networking", "flags"}),
    frozenset({"networking", "medical_supplies"}),
    frozenset({"networking", "ferreteria"}),
    frozenset({"laptops", "printers"}),
    frozenset({"laptops", "flags"}),
    frozenset({"laptops", "medical_supplies"}),
    frozenset({"laptops", "ferreteria"}),
    frozenset({"printers", "medical_supplies"}),
    frozenset({"printers", "flags"}),
    frozenset({"flags", "medical_supplies"}),
    frozenset({"flags", "ferreteria"}),
    frozenset({"medical_supplies", "ferreteria"}),
    frozenset({"ferreteria", "advertising"}),
    frozenset({"glucose_monitoring", "ferreteria"}),
    frozenset({"glucose_monitoring", "flags"}),
    frozenset({"glucose_monitoring", "networking"}),
    frozenset({"glucose_monitoring", "printers"}),
}

MIN_SIMILAR_PROCESS_SCORE = 55.0
MIN_PRODUCT_ANCHOR_TOKENS = 1
MIN_SPECIFIC_KEYWORD_OVERLAP = 2

INSTITUTION_GENERIC_TOKENS = {
    "centro", "direccion", "general", "nacional", "ministerio", "hospital", "instituto",
    "regional", "provincial", "desarrollo", "humano", "rehabilitacion", "psicosocial",
    "administracion", "departamento", "unidad", "comision", "secretaria", "fundacion",
    "organismo", "dominicano", "republica", "publico", "publica", "estado", "sistema",
    "programa", "servicios", "social", "salud", "educacion", "cultural", "tecnico",
}


@dataclass
class SimilarityMatch:
    award_id: str
    process_code: str
    contract_code: str | None
    buyer_institution: str
    supplier_name: str | None
    award_date: str | None
    item_description: str | None
    unit_price: Decimal | None
    quantity: Decimal | None
    awarded_amount: Decimal | None
    modality: str | None
    contract_url: str | None
    process_url: str | None
    similarity_score: float
    similarity_level: str
    match_reasons: list[str]
    matched_keywords: list[str] | None = None
    contract_object: str | None = None
    unit_measure: str | None = None
    source: str = "dgcp_contratos_articulos"
    publication_to_award_days: int | None = None


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def expand_tokens(tokens: set[str]) -> set[str]:
    expanded = set(tokens)
    for group in SYNONYM_GROUPS:
        if tokens & group:
            expanded |= group
    return expanded


def tokenize(text: str, *, min_len: int = 3) -> set[str]:
    norm = normalize_text(text or "")
    return {t for t in norm.split() if len(t) >= min_len and t not in STOPWORDS}


def build_query_tokens(*texts: str | None) -> set[str]:
    tokens: set[str] = set()
    for text in texts:
        if text:
            tokens |= tokenize(text)
    return expand_tokens(tokens)


def core_query_tokens(*texts: str | None) -> set[str]:
    """Tokens de producto/rubro — excluye genéricos del pliego."""
    all_tokens = build_query_tokens(*texts)
    core = {t for t in all_tokens if t not in PROCESS_GENERIC_TOKENS and len(t) >= 4}
    if core:
        return core
    # Fallback: tokens más largos aunque sean genéricos
    long_tokens = {t for t in all_tokens if len(t) >= 5}
    return long_tokens or all_tokens


def strict_core_tokens(*texts: str | None) -> set[str]:
    """Core tokens sin genéricos — para procesos similares entre instituciones."""
    core = core_query_tokens(*texts)
    return {t for t in core if t not in GENERIC_MATCH_TOKENS}


def has_keyword_overlap(query_tokens: set[str], text: str) -> bool:
    if not query_tokens:
        return True
    text_tokens = expand_tokens(tokenize(text))
    return bool(query_tokens & text_tokens)


def display_keywords(tokens: set[str], *, limit: int = 12) -> list[str]:
    """Ordena keywords para UI — prioriza tokens de producto."""
    core = [t for t in tokens if t not in PROCESS_GENERIC_TOKENS and len(t) >= 4]
    rest = [t for t in tokens if t not in core]
    ordered = sorted(core, key=lambda t: (-len(t), t)) + sorted(rest)
    return ordered[:limit]


def score_award(
    *,
    query_tokens: set[str],
    query_institution: str,
    query_objeto: str | None,
    award_institution: str,
    award_objeto: str | None,
    award_search_text: str,
    same_institution_required: bool,
) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0

    inst_q = normalize_text(query_institution)
    inst_a = normalize_text(award_institution)
    if inst_q and inst_a:
        if inst_q == inst_a or inst_q in inst_a or inst_a in inst_q:
            score += 35
            reasons.append("Misma institución compradora")
        elif same_institution_required:
            return 0.0, ["Institución distinta (filtro activo)"]

    if query_objeto and award_objeto and normalize_text(query_objeto) == normalize_text(award_objeto):
        score += 20
        reasons.append("Mismo objeto de proceso")

    award_tokens = expand_tokens(tokenize(award_search_text))
    if not query_tokens:
        return score, reasons

    overlap = query_tokens & award_tokens
    if overlap:
        ratio = len(overlap) / max(len(query_tokens), 1)
        pts = min(45, ratio * 60 + len(overlap) * 3)
        score += pts
        sample = ", ".join(sorted(overlap)[:5])
        reasons.append(f"Palabras clave coincidentes: {sample}")

    return score, reasons


def institution_matches(query_institution: str, candidate_institution: str) -> bool:
    """Coincidencia laxa — solo para compatibilidad; preferir institution_matches_strict."""
    return institution_matches_strict(query_institution, candidate_institution)


def institution_matches_strict(
    query_institution: str,
    candidate_institution: str,
    *,
    query_institution_code: str | int | None = None,
    candidate_institution_code: str | int | None = None,
) -> bool:
    if query_institution_code is not None and candidate_institution_code is not None:
        if str(query_institution_code) == str(candidate_institution_code):
            return True

    inst_q = normalize_text(query_institution)
    inst_a = normalize_text(candidate_institution)
    if not inst_q or not inst_a:
        return False
    if inst_q == inst_a or inst_q in inst_a or inst_a in inst_q:
        return True

    q_tokens = {t for t in inst_q.split() if len(t) >= 4 and t not in INSTITUTION_GENERIC_TOKENS}
    a_tokens = {t for t in inst_a.split() if len(t) >= 4 and t not in INSTITUTION_GENERIC_TOKENS}
    if not q_tokens or not a_tokens:
        return False
    overlap = q_tokens & a_tokens
    if any(len(t) >= 8 for t in overlap):
        return True
    return len(overlap) >= 2


def similarity_level(score: float) -> str:
    if score >= 70:
        return "alta"
    if score >= 45:
        return "media"
    if score >= 20:
        return "baja"
    return "muy_baja"


def match_classification(score: float, *, exact_item: bool = False) -> str:
    """Clasificación profesional: EXACTA | ALTA_SIMILITUD | RELACIONADA."""
    if exact_item or score >= 85:
        return "EXACTA"
    if score >= 55:
        return "ALTA_SIMILITUD"
    return "RELACIONADA"


def match_classification_label(code: str, *, similarity_pct: float | None = None) -> str:
    if code == "EXACTA":
        return "Última compra exacta" if similarity_pct is None else "Compra exacta"
    if code == "ALTA_SIMILITUD":
        pct = f" — {similarity_pct:.0f}% similitud" if similarity_pct is not None else ""
        return f"Última compra comparable{pct}" if similarity_pct is not None else "Compra comparable"
    return "Compra relacionada"


# Estados de adjudicación/contrato que NO cuentan como compra válida
INVALID_AWARD_STATUS_MARKERS = (
    "cancelad",
    "desiert",
    "anulad",
    "sin efecto",
    "rechazad",
    "suspendid",
)


def is_valid_award_status(status: str | None) -> bool:
    """True si el estado representa adjudicación/contrato válido (no desierto/cancelado)."""
    if not status or not str(status).strip():
        # Sin estado pero con contrato URL se trata en la capa de servicio
        return True
    s = normalize_text(str(status))
    return not any(m in s for m in INVALID_AWARD_STATUS_MARKERS)


def _filter_generic(tokens: set[str]) -> set[str]:
    return {t for t in tokens if t not in GENERIC_MATCH_TOKENS}


def detect_technical_families(*texts: str | None) -> set[str]:
    """Detecta familias técnicas del rubro en textos del proceso."""
    blob = normalize_text(" ".join(t for t in texts if t))
    if not blob:
        return set()
    found: set[str] = set()
    for family, terms in TECHNICAL_FAMILIES.items():
        if any(term in blob for term in terms):
            found.add(family)
    return found


def families_are_compatible(query_families: set[str], candidate_families: set[str]) -> bool:
    if not query_families or not candidate_families:
        return True
    shared = query_families & candidate_families
    if shared:
        for cf in candidate_families - query_families:
            for qf in query_families:
                if frozenset({cf, qf}) in INCOMPATIBLE_FAMILY_PAIRS:
                    return False
        for qf in query_families - candidate_families:
            for cf in candidate_families:
                if frozenset({qf, cf}) in INCOMPATIBLE_FAMILY_PAIRS:
                    return False
        return True
    for pair in INCOMPATIBLE_FAMILY_PAIRS:
        if pair <= query_families | candidate_families:
            return False
    return False


def is_specific_objeto(objeto: str | None) -> bool:
    """True si el objeto del proceso describe un rubro concreto, no un pliego genérico."""
    if not objeto:
        return False
    specific = _filter_generic(tokenize(objeto))
    return len(specific) >= 2


def non_generic_keyword_overlap(query_core: set[str], candidate_text: str) -> set[str]:
    """Intersección de keywords técnicas sin términos genéricos."""
    q = _filter_generic(query_core)
    if not q:
        return set()
    q_exp = expand_tokens(q)
    cand = _filter_generic(expand_tokens(tokenize(candidate_text)))
    return _filter_generic(q_exp & cand)


def product_anchor_tokens(tokens: set[str]) -> set[str]:
    """Tokens que anclan el rubro del producto (familia técnica o marca/modelo)."""
    anchors: set[str] = set()
    filtered = _filter_generic(tokens)
    for family, terms in TECHNICAL_FAMILIES.items():
        if filtered & terms:
            anchors |= filtered & terms
    brands = {
        "dell", "hp", "hpe", "lenovo", "acer", "asus", "cisco", "fortinet", "fortigate",
        "canon", "epson", "brother", "samsung", "microsoft", "kingston", "intel",
    }
    anchors |= {t for t in filtered if t in brands or len(t) >= 6}
    return anchors


def unspsc_matches(
    query: tuple[str | None, str | None, str | None],
    candidate: tuple[str | None, str | None, str | None],
) -> bool:
    qf, qc, qs = query
    cf, cc, cs = candidate
    if qf and cf and qf == cf:
        return True
    if qc and cc and qc == cc:
        return True
    if qs and cs and qs == cs:
        return True
    return False


def score_similar_process(
    *,
    query_texts: list[str],
    query_core: set[str],
    query_objeto: str | None,
    query_unspsc: tuple[str | None, str | None, str | None] = (None, None, None),
    candidate_texts: list[str],
    candidate_objeto: str | None,
    candidate_unspsc: tuple[str | None, str | None, str | None] = (None, None, None),
) -> tuple[float, list[str], list[str]] | None:
    """
    Scoring estricto para procesos similares (otras instituciones).
    Retorna None si la coincidencia es demasiado débil o incompatible.
    """
    query_blob = " ".join(query_texts)
    candidate_blob = " ".join(t for t in candidate_texts if t)
    primary_candidate = next((t for t in candidate_texts if t and t.strip()), "")
    query_families = detect_technical_families(query_blob, query_objeto)
    candidate_families = detect_technical_families(primary_candidate, candidate_objeto)

    if not families_are_compatible(query_families, candidate_families):
        return None

    cand_norm = normalize_text(primary_candidate)
    cand_full = normalize_text(candidate_blob)
    if "networking" in query_families:
        if any(t in cand_norm for t in ("switch", "switches", "p-switch", "pswitch")):
            plumbing = any(t in cand_norm for t in PLUMBING_PRESSURE_TERMS)
            network = any(t in cand_norm for t in NETWORKING_ANCHOR_TERMS | {"pfsense", "pfSense".lower()})
            if plumbing and not network:
                return None

    if "glucose_monitoring" in query_families:
        if not any(t in cand_norm for t in TECHNICAL_FAMILIES["glucose_monitoring"]):
            return None

    overlap = non_generic_keyword_overlap(query_core, primary_candidate)
    matched = sorted(overlap, key=lambda t: (-len(t), t))

    anchor_overlap = product_anchor_tokens(overlap)
    shared_families = query_families & candidate_families
    unspsc_hit = unspsc_matches(query_unspsc, candidate_unspsc)

    if query_families and not shared_families and not unspsc_hit:
        family_terms: set[str] = set()
        for fam in query_families:
            family_terms |= TECHNICAL_FAMILIES.get(fam, set())
        if not (overlap & family_terms):
            return None

    if not matched and not shared_families and not unspsc_hit:
        return None

    # Rechazar coincidencias solo por genéricos residual
    if len(matched) < MIN_SPECIFIC_KEYWORD_OVERLAP and not shared_families and not unspsc_hit:
        if len(anchor_overlap) < MIN_PRODUCT_ANCHOR_TOKENS:
            return None

    score = 0.0
    reasons: list[str] = []

    if shared_families:
        labels = ", ".join(sorted(shared_families))
        score += 30
        reasons.append(f"Misma familia técnica: {labels}")

    if unspsc_hit:
        score += 25
        parts = [p for p in query_unspsc if p]
        if parts:
            reasons.append(f"Categoría UNSPSC coincidente ({parts[0]})")

    if matched:
        ratio = len(matched) / max(len(_filter_generic(query_core)), 1)
        pts = min(40, ratio * 50 + len(matched) * 4)
        score += pts
        sample = ", ".join(matched[:6])
        reasons.append(f"Palabras técnicas coincidentes: {sample}")

    if (
        query_objeto
        and candidate_objeto
        and is_specific_objeto(query_objeto)
        and normalize_text(query_objeto) == normalize_text(candidate_objeto)
    ):
        score += 15
        reasons.append("Mismo objeto específico de proceso")

    # Penalizar si la mayoría de coincidencias son débiles
    generic_hits = len(overlap & GENERIC_MATCH_TOKENS)
    if generic_hits:
        score -= generic_hits * 5

    if anchor_overlap:
        score += min(10, len(anchor_overlap) * 5)

    if score < MIN_SIMILAR_PROCESS_SCORE:
        return None

    if not matched and (shared_families or unspsc_hit):
        matched = sorted(anchor_overlap or shared_families, key=lambda t: (-len(t), t))

    return round(score, 1), reasons, matched[:12]
