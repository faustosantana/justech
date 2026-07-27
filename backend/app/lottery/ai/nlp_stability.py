"""Fase X — NLP Intent & Context Stability (v2.3.1).

Canonical intent taxonomy + entity extraction + follow-up / clarify gates.
Does NOT modify Motor, Ranking, Histórico, Prompt Maestro, Research Engine,
Discovery Engine, Knowledge Engine, Conversation Brain, or Planner bodies.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Literal

NlpIntent = Literal[
    "GREETING",
    "GENERAL_CHAT",
    "COUNT",
    "DATE",
    "LOTTERY",
    "POSITION",
    "COMPARE",
    "FOLLOW_UP",
    "ANALYZE",
    "REPORT",
    "DISCOVERY",
    "EXPLAIN",
    "HELP",
    "UNKNOWN",
]

NLP_INTENTS: tuple[str, ...] = (
    "GREETING",
    "GENERAL_CHAT",
    "COUNT",
    "DATE",
    "LOTTERY",
    "POSITION",
    "COMPARE",
    "FOLLOW_UP",
    "ANALYZE",
    "REPORT",
    "DISCOVERY",
    "EXPLAIN",
    "HELP",
    "UNKNOWN",
)

NLP_STABILITY_VERSION = "2.3.1"

_GREETING = re.compile(
    r"^\s*("
    r"hola|hola+|"
    r"buenos\s+dias|buenas\s+tardes|buenas\s+noches|buen\s+dia|"
    r"que\s+tal|como\s+estas|como\s+esta|como\s+te\s+va|"
    r"saludos|hey|hi|hello|buenass?"
    r")[\s!?.¡¿]*$",
    re.I,
)

_GENERAL_CHAT = re.compile(
    r"^\s*("
    r"gracias(\s+muchas)?|muchas\s+gracias|ok|okay|vale|perfecto|excelente|"
    r"genial|de\s+acuerdo|entendido|listo|dale"
    r")[\s!?.¡¿]*$",
    re.I,
)

_HELP = re.compile(
    r"\b(ayuda|help|que\s+puedes\s+hacer|como\s+te\s+uso|menu\s+de\s+opciones)\b",
    re.I,
)

_COUNT = re.compile(
    r"\b("
    r"cuantas?\s+veces|cuantos?\s+sorteos?\s+sali|"
    r"cuantas?\s+apariciones|apariciones\s+del?\s+\d{1,2}|"
    r"cuantas?\s+veces\s+(sali[oó]|apareci[oó]|salio)"
    r")\b",
    re.I,
)

_DATE = re.compile(
    r"\b("
    r"cuando\s+(sali[oó]|fue|apareci[oó])|"
    r"ultima\s+vez|ultima\s+aparicion|fecha\s+de\s+(la\s+)?ultima|"
    r"cual\s+fue\s+la\s+ultima|la\s+ultima(\s+vez)?|"
    r"hace\s+cuanto.*(sali|apareci)|en\s+que\s+fecha"
    r")\b",
    re.I,
)

_ANALYZE = re.compile(
    r"\b("
    r"analiz(a|ar|ame|emos)(\s+\w+){0,3}\s+(el\s+)?\d{1,2}|"
    r"analiz(a|ar|ame)\s+(completa|completamente|en\s+profundidad)|"
    r"haz(me)?\s+un\s+(estudio|analisis\s+completo)|"
    r"estudia(r)?\s+(el\s+)?\d{1,2}|"
    r"estudio\s+(completo\s+)?(del?\s+)?\d{1,2}|"
    r"investiga(r)?\s+(el\s+)?(grupo\s+(del\s+)?)?\d{1,2}|"
    r"investigacion\s+completa|analisis\s+completo|"
    r"comportamiento\s+historico\s+del?\s+\d{1,2}"
    r")\b",
    re.I,
)

_COMPARE = re.compile(
    r"\b("
    r"compara(me|r|lo|la)?|vs\.?|versus|"
    r"diferencias?\s+entre|\d{1,2}\s+vs\s+\d{1,2}|"
    r"frente\s+al?|contra\s+el?\s+\d{1,2}"
    r")\b",
    re.I,
)

_POSITION = re.compile(
    r"\b("
    r"primera(\s+posicion)?|segunda(\s+posicion)?|tercera(\s+posicion)?|"
    r"posicion\s+[123]|en\s+primera|en\s+segunda|solamente\s+en\s+primera|"
    r"solo\s+en\s+primera|cualquier\s+posicion"
    r")\b",
    re.I,
)

_LOTTERY = re.compile(
    r"\b("
    r"en\s+(nacional|leidsa|loteka|real|gana\s*mas|anguila|florida|cash4life)|"
    r"loteria\s+(nacional|leidsa|loteka)|quiniela\s+(real|loteka|leidsa)"
    r")\b",
    re.I,
)

_REPORT = re.compile(
    r"\b(informe|reporte|reporta|haz(me)?\s+un\s+informe|modo\s+informe)\b",
    re.I,
)

_DISCOVERY = re.compile(
    r"\b(descubr(e|ir|imiento)|hallazgos?\s+automatic|que\s+encontraste|"
    r"patrones?\s+observad|discovery)\b",
    re.I,
)

_EXPLAIN = re.compile(
    r"\b(explic(a|ame|ar)|por\s+que|como\s+se\s+calcul|que\s+significa|"
    r"en\s+simple|mas\s+sencillo|resum(e|eme|irlo))\b",
    re.I,
)

_EXPLICIT_FOLLOW_UP = re.compile(
    r"("
    r"^\s*("
    r"y\s+(en|despues|antes|solamente|solo|ahora|luego)|"
    r"y\s+la\s+(primera|segunda|tercera)|"
    r"cual\s+fue\s+la\s+ultima|"
    r"comparalo\s+con|comparala\s+con|compara(lo|la)?\s+con|"
    r"en\s+(nacional|leidsa|loteka|real|gana)|"
    r"despues\??|antes\??|"
    r"solamente\s+en|solo\s+en|"
    r"y\s+en\s+20\d{2}|este\s+ano|ese\s+mismo|"
    r"d\s*\+\s*[137]|las\s+siguientes"
    r")\b"
    r"|^(ultima|primera)\s+vez\b"
    r"|^solamente\s+ahi\b"
    r"|^esa\s+(pareja|combinacion)\b"
    r"|^ese\s+(grupo|analisis|numero)\b"
    r"|^\b(ese|esa|eso|alli|despues|antes)\b"
    r")",
    re.I,
)

_STANDALONE_COMPLETE = re.compile(
    r"\b("
    r"cuantas?\s+veces.*\b\d{1,2}\b|"
    r"analiz(a|ar).*?\b\d{1,2}\b|"
    r"cuando\s+sali[oó]\s+(el\s+)?\d{1,2}|"
    r"investiga(r)?.*?\b\d{1,2}\b|"
    r"estudia(r)?.*?\b\d{1,2}\b|"
    r"compara(me|r)?.*\b\d{1,2}\b.*\b\d{1,2}\b"
    r")",
    re.I,
)

_NUM = re.compile(r"\b(\d{1,2})\b")
_YEAR = re.compile(r"\b(20\d{2})\b")
_PAIR = re.compile(r"\b(\d{1,2})\s*(?:vs|y|/|\+|contra|,)\s*(\d{1,2})\b", re.I)
_MONTH = re.compile(
    r"\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\b",
    re.I,
)
_PERIOD = re.compile(
    r"\b(este\s+ano|ano\s+pasado|ultimos?\s+\d+\s+(dias|sorteos|meses)|"
    r"historial|todo\s+el\s+historico|desde\s+20\d{2})\b",
    re.I,
)

_LOTTERY_NAMES = [
    (re.compile(r"\bnacional\s+noche\b", re.I), "Nacional Noche"),
    (re.compile(r"\bnacional\s+d[ií]a\b", re.I), "Nacional Día"),
    (re.compile(r"\bloter[ií]a\s+nacional|\bnacional\b", re.I), "Nacional"),
    (re.compile(r"\bleidsa\b", re.I), "Leidsa"),
    (re.compile(r"\bloteka\b", re.I), "Loteka"),
    (re.compile(r"\bquiniela\s+real|\breal\b", re.I), "Real"),
    (re.compile(r"\bgana\s*m[aá]s\b", re.I), "Gana Más"),
    (re.compile(r"\bcash\s*4\s*life|cash4life\b", re.I), "Cash4Life"),
    (re.compile(r"\banguila\b", re.I), "Anguila"),
    (re.compile(r"\bflorida\b", re.I), "Florida"),
]

DEFAULT_ALL_HISTORY_LOTTERIES = (
    "Nacional",
    "Nacional Día",
    "Nacional Noche",
    "Leidsa",
    "Loteka",
    "Real",
    "Gana Más",
)

GREETING_REPLY = (
    "Hola, estoy muy bien. ¿Qué te gustaría investigar hoy?"
)

GENERAL_CHAT_REPLY = (
    "De acuerdo. Cuando quieras, dime qué número, comparación o caso "
    "quieres que investigue en el histórico."
)

HELP_REPLY = (
    "Puedo investigar históricos, conteos, últimas fechas, posiciones, "
    "comparaciones y análisis completos. "
    "Ejemplo: «¿Cuántas veces salió el 54?» — investigo de inmediato."
)


def _strip_punct(text: str) -> str:
    return re.sub(r"^[¿¡\s]+|[?!¡.,;:\s]+$", "", (text or "").strip())


def _norm(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


@dataclass
class NlpDecision:
    intent: str
    entities: dict[str, Any] = field(default_factory=dict)
    is_follow_up: bool = False
    needs_clarification: bool = False
    missing_slots: list[str] = field(default_factory=list)
    inherit_context: bool = False
    confidence: float = 0.9
    decision_log: list[str] = field(default_factory=list)
    conversational_reply: str | None = None
    run_tools: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "entities": self.entities,
            "is_follow_up": self.is_follow_up,
            "needs_clarification": self.needs_clarification,
            "missing_slots": list(self.missing_slots),
            "inherit_context": self.inherit_context,
            "confidence": self.confidence,
            "decision_log": list(self.decision_log),
            "run_tools": self.run_tools,
            "nlp_version": NLP_STABILITY_VERSION,
        }


def extract_entities(message: str) -> dict[str, Any]:
    raw = message or ""
    norm = _norm(raw)
    numbers = [m.zfill(2) for m in _NUM.findall(raw)]
    years = [int(y) for y in _YEAR.findall(raw)]
    numbers = [
        n
        for n in numbers
        if not (n.startswith("20") and len(n) == 2 and any(str(y).endswith(n) for y in years))
    ]
    pairs = [[a.zfill(2), b.zfill(2)] for a, b in _PAIR.findall(raw)]
    ternas: list[list[str]] = []
    trip = re.findall(r"\b(\d{1,2})\s*[,y]\s*(\d{1,2})\s*[,y]\s*(\d{1,2})\b", raw, re.I)
    for a, b, c in trip:
        ternas.append([a.zfill(2), b.zfill(2), c.zfill(2)])
    lotteries: list[str] = []
    for rx, name in _LOTTERY_NAMES:
        if rx.search(raw) and name not in lotteries:
            lotteries.append(name)
    positions: list[str] = []
    if re.search(r"\bprimera\b|posici[oó]n\s*1|1(ra)?\b", norm):
        positions.append("primera")
    if re.search(r"\bsegunda\b|posici[oó]n\s*2|2(da)?\b", norm):
        positions.append("segunda")
    if re.search(r"\btercera\b|posici[oó]n\s*3|3(ra)?\b", norm):
        positions.append("tercera")
    months = [m.lower() for m in _MONTH.findall(raw)]
    period = None
    pm = _PERIOD.search(norm)
    if pm:
        period = pm.group(0)
    comparisons = bool(_COMPARE.search(norm) or pairs)
    return {
        "numbers": list(dict.fromkeys(numbers))[:8],
        "pairs": pairs[:6],
        "ternas": ternas[:4],
        "lotteries": lotteries[:6],
        "years": years[:6],
        "months": months[:4],
        "positions": list(dict.fromkeys(positions)),
        "period": period,
        "comparisons": comparisons,
    }


def is_explicit_follow_up(message: str) -> bool:
    return bool(_EXPLICIT_FOLLOW_UP.search(_strip_punct(_norm(message or ""))))


def is_complete_standalone(message: str) -> bool:
    return bool(_STANDALONE_COMPLETE.search(_norm(message or "")))


def classify_nlp(
    message: str,
    *,
    has_active_context: bool = False,
) -> NlpDecision:
    """Classify user message with current-message priority and decision log."""
    raw = (message or "").strip()
    log: list[str] = []
    if not raw:
        log.append("empty→UNKNOWN")
        return NlpDecision(
            intent="UNKNOWN",
            needs_clarification=True,
            missing_slots=["query"],
            confidence=0.2,
            decision_log=log,
            run_tools=False,
            conversational_reply="¿Qué te gustaría consultar del histórico?",
        )

    entities = extract_entities(raw)
    norm = _strip_punct(_norm(raw))
    log.append(f"entities={{{','.join(k for k,v in entities.items() if v)}}}")

    # 1. Greeting — never tools
    if _GREETING.match(norm) or _GREETING.match(raw):
        log.append("rule=GREETING")
        return NlpDecision(
            intent="GREETING",
            entities=entities,
            confidence=0.99,
            decision_log=log,
            run_tools=False,
            conversational_reply=GREETING_REPLY,
        )

    # 2. Help how-to (before general chat)
    if re.match(
        r"^\s*(como\s+funciona(\s+(esto|el\s+chat|lottery\s*ia))?|"
        r"que\s+puedes\s+hacer|ayuda(\s+por\s+favor)?|help)\s*[\s!?.¡¿]*$",
        norm,
        re.I,
    ):
        log.append("rule=HELP")
        return NlpDecision(
            intent="HELP",
            entities=entities,
            confidence=0.97,
            decision_log=log,
            run_tools=False,
            conversational_reply=HELP_REPLY,
        )

    # 3. General chat / thanks / short ack
    if _GENERAL_CHAT.match(norm) or _GENERAL_CHAT.match(raw):
        log.append("rule=GENERAL_CHAT")
        return NlpDecision(
            intent="GENERAL_CHAT",
            entities=entities,
            confidence=0.97,
            decision_log=log,
            run_tools=False,
            conversational_reply=GENERAL_CHAT_REPLY,
        )

    # 3. Standalone complete questions → never inherit, current message wins
    standalone = is_complete_standalone(raw)
    explicit_fu = is_explicit_follow_up(raw)
    if standalone:
        log.append("priority=current_message_standalone")
    if explicit_fu and has_active_context and not standalone:
        log.append("follow_up=explicit_reference")
    elif has_active_context and not standalone and not entities.get("numbers"):
        # weak follow-up only with explicit markers
        if explicit_fu:
            log.append("follow_up=explicit")
        else:
            log.append("no_inherit_without_explicit_ref")

    # Intent priority (ANALYZE before COUNT — "analiza" must not become COUNT)
    if _ANALYZE.search(norm) and (
        entities.get("numbers") or re.search(r"grupo|pareja|estudio|profundidad|completa", norm)
    ):
        log.append("rule=ANALYZE")
        missing = [] if entities.get("numbers") else ["number"]
        return NlpDecision(
            intent="ANALYZE",
            entities=entities,
            needs_clarification=bool(missing),
            missing_slots=missing,
            inherit_context=False if standalone else (explicit_fu and has_active_context),
            is_follow_up=False,
            confidence=0.96,
            decision_log=log,
            run_tools=True,
            conversational_reply=("¿Qué número quieres que analice?" if missing else None),
        )

    if _COMPARE.search(norm):
        log.append("rule=COMPARE")
        nums = entities.get("numbers") or []
        missing = [] if len(nums) >= 2 or (explicit_fu and has_active_context and len(nums) >= 1) else (
            ["number"] if not nums else ["compare_with"]
        )
        # "compáralo con el 94" with context is follow-up compare
        is_fu = explicit_fu and has_active_context
        return NlpDecision(
            intent="COMPARE" if not is_fu or nums else "FOLLOW_UP",
            entities=entities,
            needs_clarification=False if (is_fu or len(nums) >= 2) else bool(missing),
            missing_slots=missing if not is_fu and len(nums) < 2 else [],
            inherit_context=is_fu,
            is_follow_up=is_fu,
            confidence=0.95,
            decision_log=log,
            run_tools=True,
        )

    if _COUNT.search(norm):
        log.append("rule=COUNT")
        missing = [] if entities.get("numbers") else ["number"]
        # Full history default — never ask lottery/date when number present
        return NlpDecision(
            intent="COUNT",
            entities=entities,
            needs_clarification=bool(missing),
            missing_slots=missing,
            inherit_context=False if standalone or entities.get("numbers") else (
                explicit_fu and has_active_context
            ),
            is_follow_up=bool(explicit_fu and has_active_context and not entities.get("numbers")),
            confidence=0.97,
            decision_log=log,
            run_tools=True,
            conversational_reply=("¿De qué número quieres el conteo?" if missing else None),
        )

    if _DATE.search(norm):
        log.append("rule=DATE")
        missing = [] if entities.get("numbers") else ["number"]
        inherit = bool(explicit_fu and has_active_context and not entities.get("numbers"))
        if inherit:
            missing = []
        return NlpDecision(
            intent="DATE" if not inherit else "FOLLOW_UP",
            entities=entities,
            needs_clarification=bool(missing),
            missing_slots=missing,
            inherit_context=inherit,
            is_follow_up=inherit,
            confidence=0.95,
            decision_log=log,
            run_tools=True,
            conversational_reply=("¿De qué número?" if missing else None),
        )

    if _DISCOVERY.search(norm):
        log.append("rule=DISCOVERY")
        return NlpDecision(
            intent="DISCOVERY",
            entities=entities,
            confidence=0.9,
            decision_log=log,
            run_tools=True,
        )

    if _REPORT.search(norm):
        log.append("rule=REPORT")
        return NlpDecision(
            intent="REPORT",
            entities=entities,
            confidence=0.9,
            decision_log=log,
            run_tools=True,
        )

    if _EXPLAIN.search(norm):
        log.append("rule=EXPLAIN")
        return NlpDecision(
            intent="EXPLAIN",
            entities=entities,
            inherit_context=bool(has_active_context),
            is_follow_up=bool(has_active_context),
            confidence=0.9,
            decision_log=log,
            run_tools=True,
        )

    if _HELP.search(norm):
        log.append("rule=HELP")
        return NlpDecision(
            intent="HELP",
            entities=entities,
            confidence=0.95,
            decision_log=log,
            run_tools=False,
            conversational_reply=HELP_REPLY,
        )

    # Position / lottery filter alone with context → FOLLOW_UP
    if has_active_context and explicit_fu and (_POSITION.search(norm) or _LOTTERY.search(norm)):
        kind = "POSITION" if _POSITION.search(norm) and not _LOTTERY.search(norm) else (
            "LOTTERY" if _LOTTERY.search(norm) else "FOLLOW_UP"
        )
        log.append(f"rule={kind}_follow_up")
        return NlpDecision(
            intent=kind if kind != "FOLLOW_UP" else "FOLLOW_UP",
            entities=entities,
            is_follow_up=True,
            inherit_context=True,
            confidence=0.93,
            decision_log=log,
            run_tools=True,
        )

    if _POSITION.search(norm) and entities.get("numbers"):
        log.append("rule=POSITION")
        return NlpDecision(
            intent="POSITION",
            entities=entities,
            confidence=0.9,
            decision_log=log,
            run_tools=True,
        )

    if _LOTTERY.search(norm) and entities.get("numbers"):
        log.append("rule=LOTTERY")
        return NlpDecision(
            intent="LOTTERY",
            entities=entities,
            confidence=0.88,
            decision_log=log,
            run_tools=True,
        )

    if explicit_fu and has_active_context:
        log.append("rule=FOLLOW_UP")
        return NlpDecision(
            intent="FOLLOW_UP",
            entities=entities,
            is_follow_up=True,
            inherit_context=True,
            confidence=0.9,
            decision_log=log,
            run_tools=True,
        )

    log.append("rule=UNKNOWN")
    return NlpDecision(
        intent="UNKNOWN",
        entities=entities,
        confidence=0.5,
        decision_log=log,
        run_tools=True,
    )
