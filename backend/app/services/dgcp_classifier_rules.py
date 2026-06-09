from __future__ import annotations

import re
from dataclasses import dataclass, field

from integrations.dgcp.schemas import DGCPProcesoRecord

COMPANY_LABELS = {
    "justech": "Justech SRL",
    "just_office": "Just Office SRL",
    "mf_plug_safe": "MF Plug & Safe Services SRL",
    "omni_solutions": "Omni Solutions SRL",
}

KEYWORD_RULES: dict[str, list[tuple[str, int]]] = {
    "justech": [
        (r"\bsoftware\b", 4), (r"\baplicaci[oó]n\b", 4), (r"\bsistema(s)?\b", 3),
        (r"\btecnolog[ií]a\b", 3), (r"\binform[aá]tic", 4), (r"\bcomput", 4),
        (r"\bhardware\b", 4), (r"\bservidor(es)?\b", 4), (r"\bserver\b", 4),
        (r"\bcloud\b", 4), (r"\bnube\b", 3), (r"\bmicrosoft\b", 4),
        (r"\bwindows\b", 3), (r"\boffice\s*365\b", 4), (r"\blicencia(s)?\b", 3),
        (r"\bmigraci[oó]n\b", 3), (r"\bdigital\b", 2), (r"\bdatacenter\b", 4),
        (r"\bdata\s*center\b", 4), (r"\bplataforma\b", 3), (r"\bdesarrollo\b", 3),
        (r"\bweb\b", 2), (r"\bapp\b", 2), (r"\bsoporte\s+t[eé]cnic", 4),
        (r"\binfraestructura\s+ti\b", 5), (r"\bwifi\b", 3), (r"\bred(es)?\b", 2),
        (r"\bfibra\s+[oó]ptic", 4), (r"\bcibersegur", 4), (r"\bbackup\b", 3),
        (r"\bvirtualiz", 4), (r"\binteligencia\s+artificial\b", 4),
        (r"\bautomatiz", 3), (r"\bbase\s+de\s+datos\b", 4), (r"\bsql\b", 3),
        (r"\bendpoint\b", 3), (r"\blaptop\b", 4), (r"\bnotebook\b", 4),
        (r"\btablet\b", 3), (r"\bimpresora\s+de\s+red\b", 3), (r"\bscanner\b", 3),
        (r"\btelecomunic", 4), (r"\bvoip\b", 4), (r"\btelefon[ií]a\s+ip\b", 4),
        (r"\bactive\s+directory\b", 4), (r"\bdominio\b", 2), (r"\bantivirus\b", 4),
        (r"\bfirewall\b", 4), (r"\bstorage\b", 3), (r"\balmacenamiento\b", 2),
        (r"\bswitch\b", 3), (r"\brouter\b", 3), (r"\bmonitor(es)?\b", 2),
        (r"\bproyector(es)?\b", 2), (r"\bequipo(s)?\s+de\s+c[oó]mputo\b", 5),
        (r"\bcomputadora(s)?\b", 4), (r"\bpc\b", 2), (r"\bdesktop\b", 3),
    ],
    "just_office": [
        (r"\bmobiliario\b", 5), (r"\boficina\b", 2), (r"\bpapeler", 4),
        (r"\btoner\b", 5), (r"\bcartucho\b", 4), (r"\bimpresor", 3),
        (r"\bsuministro(s)?\s+de\s+oficina\b", 5), (r"\bmaterial\s+de\s+oficina\b", 5),
        (r"\bescritorio(s)?\b", 4), (r"\bsilla(s)?\b", 3), (r"\barchivo\b", 2),
        (r"\bfolder\b", 3), (r"\bcarpeta(s)?\b", 2), (r"\bluminaria(s)?\b", 4),
        (r"\baire\s+acondicionado\b", 3), (r"\blimpieza\b", 3), (r"\bcafeter", 3),
        (r"\b[uú]tiles\b", 2), (r"\bbol[ií]grafo\b", 3), (r"\bresma\b", 3),
        (r"\bpapel\b", 2), (r"\bdetergente\b", 3), (r"\bdesinfect", 3),
        (r"\bhigiene\b", 2), (r"\bconsumible(s)?\b", 3), (r"\bestanter", 3),
        (r"\bgaveta(s)?\b", 3), (r"\bmesa(s)?\s+de\s+trabajo\b", 4),
        (r"\bnevera\b", 2), (r"\brefriger", 2), (r"\bmenaje\b", 3),
        (r"\balimentos?\b", 2), (r"\bcomestible", 2), (r"\bv[ií]veres\b", 2),
        (r"\buniforme(s)?\b", 2), (r"\btextil(es)?\b", 2),
    ],
    "mf_plug_safe": [
        (r"\bseguridad\b", 3), (r"\bcctv\b", 5), (r"\bvideovigilancia\b", 5),
        (r"\balarma(s)?\b", 4), (r"\bcontrol\s+de\s+acceso\b", 5),
        (r"\bbiom[eé]tric", 4), (r"\bprotecci[oó]n\b", 2), (r"\bel[eé]ctric", 4),
        (r"\bplanta\s+el[eé]ctrica\b", 5), (r"\bups\b", 5), (r"\bgenerador(es)?\b", 4),
        (r"\benerg[ií]a\b", 2), (r"\btransformador(es)?\b", 4),
        (r"\btablero(s)?\s+el[eé]ctric", 5), (r"\bcableado\b", 4),
        (r"\binstalaci[oó]n\s+el[eé]ctrica\b", 5), (r"\bcontra\s+incendio\b", 5),
        (r"\bextintor(es)?\b", 4), (r"\bdetector(es)?\b", 3), (r"\bplug\b", 3),
        (r"\bsafe\b", 2), (r"\brehabilitaci[oó]n\s+el[eé]ctrica\b", 5),
        (r"\bmantenimiento\s+preventivo\b", 3), (r"\bsubestaci[oó]n\b", 4),
        (r"\binterruptor(es)?\b", 3), (r"\bluminaria\s+led\b", 3),
        (r"\biluminaci[oó]n\b", 2), (r"\belectromec", 4), (r"\bcuadro\s+el[eé]ctrico\b", 5),
        (r"\bgrounding\b", 4), (r"\bpuesta\s+a\s+tierra\b", 4),
        (r"\bsistema\s+de\s+alarma\b", 5), (r"\bc[aá]mara(s)?\s+de\s+seguridad\b", 5),
    ],
    "omni_solutions": [
        (r"\bconsultor[ií]a\b", 4), (r"\bintegraci[oó]n\b", 4),
        (r"\binteroperabilidad\b", 5), (r"\bportal\s+ciudadano\b", 5),
        (r"\berp\b", 5), (r"\bcrm\b", 5), (r"\bgesti[oó]n\s+documental\b", 5),
        (r"\bworkflow\b", 4), (r"\bproceso(s)?\s+de\s+negocio\b", 4),
        (r"\btransformaci[oó]n\s+digital\b", 4), (r"\bmodernizaci[oó]n\b", 3),
        (r"\bimplementaci[oó]n\s+de\s+sistema\b", 5), (r"\bsoluci[oó]n\s+integral\b", 4),
        (r"\bomni\b", 4), (r"\bbusiness\s+intelligence\b", 5),
        (r"\btablero\s+de\s+control\b", 4), (r"\bpmo\b", 3), (r"\bpmis\b", 3),
        (r"\bgesti[oó]n\s+de\s+proyecto\b", 4), (r"\bcapacitaci[oó]n\b", 2),
        (r"\bformaci[oó]n\b", 2), (r"\bauditor[ií]a\b", 2), (r"\bdiagn[oó]stico\b", 3),
        (r"\bestrategia\b", 2), (r"\boptimizaci[oó]n\b", 3), (r"\binterconexi[oó]n\b", 4),
        (r"\bapi\b", 3), (r"\bmiddleware\b", 4), (r"\borquestaci[oó]n\b", 4),
    ],
}

INSTITUTION_RULES: dict[str, list[tuple[str, int]]] = {
    "justech": [
        (r"ministerio\s+de\s+educaci[oó]n", 3), (r"one\b", 2), (r"educaci[oó]n", 2),
        (r"telecomunic", 3), (r"indotel", 4), (r"cyber", 3), (r"tecnolog", 2),
    ],
    "just_office": [
        (r"hospital", 2), (r"ministerio\s+de\s+salud", 2), (r"msp\b", 2),
        (r"municipal", 2), (r"ayuntamiento", 2), (r"relaciones\s+exteriores", 2),
    ],
    "mf_plug_safe": [
        (r"edesur", 4), (r"edeeste", 4), (r"edenorte", 4), (r"edeh", 3),
        (r"energ[ií]a", 3), (r"electricidad", 3), (r"tesorer[ií]a", 2),
        (r"obras\s+p[uú]blicas", 2), (r"mopc\b", 2), (r"defensa", 2),
    ],
    "omni_solutions": [
        (r"tesorer[ií]a\s+nacional", 3), (r"dgii", 3), (r"econom[ií]a", 2),
        (r"planificaci[oó]n", 2), (r"administraci[oó]n\s+p[uú]blica", 3),
        (r"procuradur", 2), (r"contralor", 2),
    ],
}

OBJETO_BIAS: dict[str, dict[str, int]] = {
    "Servicios": {
        "justech": 8, "omni_solutions": 10, "mf_plug_safe": 6, "just_office": 2,
    },
    "Bienes": {
        "just_office": 10, "justech": 8, "mf_plug_safe": 5, "omni_solutions": 2,
    },
    "Obras": {
        "mf_plug_safe": 12, "justech": 3, "omni_solutions": 4, "just_office": 2,
    },
}

ARTICLE_PATTERNS = [
    r"adquisici[oó]n\s+de\s+([^.;,\n]{3,80})",
    r"compra\s+de\s+([^.;,\n]{3,80})",
    r"suministro\s+de\s+([^.;,\n]{3,80})",
    r"servicio\s+de\s+([^.;,\n]{3,80})",
    r"contrataci[oó]n\s+de\s+([^.;,\n]{3,80})",
]


@dataclass
class RuleMatchResult:
    company: str | None = None
    confidence_score: int = 0
    classification_reason: str = ""
    matched_keywords: list[str] = field(default_factory=list)
    article_tokens: list[str] = field(default_factory=list)
    rule_hits: dict[str, list[str]] = field(default_factory=dict)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def build_classification_text(record: DGCPProcesoRecord) -> str:
    parts = [
        record.titulo,
        record.descripcion or "",
        record.unidad_compra,
        record.objeto_proceso or "",
        record.subobjeto_proceso or "",
        record.modalidad or "",
        record.area_requiriente or "",
    ]
    extra = record.extra or {}
    for key in ("articulos", "artículos", "items", "lineas", "líneas", "detalle"):
        value = extra.get(key)
        if isinstance(value, list):
            parts.extend(str(v) for v in value)
        elif isinstance(value, str):
            parts.append(value)
    return _normalize(" ".join(p for p in parts if p))


def extract_article_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for pattern in ARTICLE_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            fragment = _normalize(match.group(1))
            if len(fragment) >= 3:
                tokens.append(fragment)
    if not tokens and len(text) > 20:
        chunks = re.split(r"[;,/|]", text)
        for chunk in chunks[:8]:
            chunk = chunk.strip()
            if 4 <= len(chunk) <= 80:
                tokens.append(chunk)
    return tokens[:12]


def apply_keyword_rules(text: str, institution: str) -> RuleMatchResult:
    result = RuleMatchResult()
    result.article_tokens = extract_article_tokens(text)
    article_text = " ".join(result.article_tokens)
    full_text = f"{text} {article_text}".strip()

    company_hits: dict[str, list[tuple[str, int]]] = {
        c: [] for c in COMPANY_LABELS
    }

    for company, patterns in KEYWORD_RULES.items():
        for pattern, weight in patterns:
            if re.search(pattern, full_text, re.IGNORECASE):
                company_hits[company].append((pattern, weight))

    inst_norm = _normalize(institution)
    for company, patterns in INSTITUTION_RULES.items():
        for pattern, weight in patterns:
            if re.search(pattern, inst_norm, re.IGNORECASE):
                company_hits[company].append((f"inst:{pattern}", weight))

    for company, hits in company_hits.items():
        if hits:
            result.rule_hits[company] = [h[0] for h in hits]

    totals = {
        company: sum(w for _, w in hits)
        for company, hits in company_hits.items()
        if hits
    }
    if not totals:
        return result

    ranked = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    best_company, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0
    margin = best_score - second_score

    if best_score >= 8 and margin >= 3:
        result.company = best_company
        keywords = [h[0] for h in company_hits[best_company][:5]]
        result.matched_keywords = keywords
        result.confidence_score = min(95, 55 + best_score * 2 + margin * 3)
        result.classification_reason = (
            f"Regla: coincidencias fuertes para {COMPANY_LABELS[best_company]} "
            f"({', '.join(keywords[:3])})"
        )
    return result
