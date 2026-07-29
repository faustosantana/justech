"""Deterministic social / chitchat detection (Conversational Routing 3.0).

Runs before clarification, contextual follow-up, subject inheritance, and
investigative Hermes. Never inherits subjects or opens research/workspace.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


def _norm(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _strip(text: str) -> str:
    return re.sub(r"^[¿¡\s]+|[?!¡.,;:\s]+$", "", (text or "").strip())


def _soft_norm(text: str) -> str:
    """Lowercase, strip accents, drop punctuation (keep spaces)."""
    n = _norm(text)
    n = re.sub(r"[¿¡?,.;:!]+", " ", n)
    return re.sub(r"\s+", " ", n).strip()


# Pure greetings / time-of-day
_GREETING = re.compile(
    r"^\s*("
    r"hola|hey|hi|hello|saludos|buenass?|"
    r"buenos\s+dias|buenas\s+tardes|buenas\s+noches|buen\s+dia"
    r")\s*$",
    re.I,
)

# Reciprocal wellbeing / how-are-you family (the forensic bug phrase)
_WELLBEING = re.compile(
    r"^\s*("
    r"como\s+estas|como\s+esta|como\s+te\s+va|que\s+tal|"
    r"todo\s+bien(\s*(y\s+tu|y\s+usted))?|"
    r"muy\s+bien(\s*(y\s+tu|gracias))?|"
    r"que\s+bueno|bien\s+y\s+tu|"
    r"y\s+tu(\s+que\s+tal)?"
    r")\s*$",
    re.I,
)

# Short social acknowledgements — never analytical clarification by length alone
_ACK = re.compile(
    r"^\s*("
    r"gracias(\s+muchas)?|muchas\s+gracias|"
    r"ok|okay|vale|perfecto|excelente|genial|"
    r"de\s+acuerdo|entendido|listo|dale|"
    r"super|suuper|claro|asi\s+es|correcto|"
    r"bien|muy\s+bien|que\s+bien|fantastico|maravilloso"
    r")\s*$",
    re.I,
)

# Digits / lottery analytics → never social
_ANALYTICAL_HINT = re.compile(
    r"("
    r"\d{1,2}|"
    r"coincid|loter|sorteo|fecha|tabla|export|"
    r"\bexcel\b|\bxlsx\b|"
    r"desglos|filtr|orden|pagina|resultado|investiga|analiz|"
    r"cuant|cuando|sali[oó]|apareci|compar|"
    r"gana\s*mas|loteka|nacional|leidsa"
    r")",
    re.I,
)


@dataclass(frozen=True)
class SocialChitchatMatch:
    matched: bool
    reason_code: str = "SOCIAL_CHITCHAT_MATCH"
    reply: str = ""
    subtype: str = ""  # greeting | wellbeing | ack


_REPLIES = {
    "greeting": "Hola. ¿Qué deseas investigar hoy?",
    "wellbeing_how": "Muy bien, gracias. ¿Qué deseas analizar?",
    "wellbeing_reciprocal": "Todo bien también. ¿Qué deseas investigar ahora?",
    "thanks": "Con gusto.",
    "ack_perfecto": "Perfecto.",
    "ack_excelente": "Excelente.",
    "ack_entendido": "Entendido.",
    "ack_generic": "De acuerdo. ¿Qué deseas investigar?",
}


def social_reply_for(raw: str, *, subtype: str) -> str:
    n = _strip(_norm(raw))
    if subtype == "greeting":
        return _REPLIES["greeting"]
    if subtype == "wellbeing":
        if re.search(r"todo\s+bien|y\s+tu|bien\s+y", n):
            return _REPLIES["wellbeing_reciprocal"]
        return _REPLIES["wellbeing_how"]
    if re.search(r"gracias", n):
        return _REPLIES["thanks"]
    if re.search(r"^perfecto", n):
        return _REPLIES["ack_perfecto"]
    if re.search(r"^excelente", n):
        return _REPLIES["ack_excelente"]
    if re.search(r"^entendido", n):
        return _REPLIES["ack_entendido"]
    return _REPLIES["ack_generic"]


def detect_social_chitchat(message: str) -> SocialChitchatMatch | None:
    """Return a match when the turn is purely social (no analytics)."""
    raw = (message or "").strip()
    if not raw or len(raw) > 80:
        return None
    if _ANALYTICAL_HINT.search(_soft_norm(raw)):
        return None

    n = _soft_norm(raw)
    if not n:
        return None

    if _GREETING.match(n):
        return SocialChitchatMatch(
            matched=True,
            subtype="greeting",
            reply=social_reply_for(raw, subtype="greeting"),
        )
    if _WELLBEING.match(n):
        return SocialChitchatMatch(
            matched=True,
            subtype="wellbeing",
            reply=social_reply_for(raw, subtype="wellbeing"),
        )
    if _ACK.match(n):
        return SocialChitchatMatch(
            matched=True,
            subtype="ack",
            reply=social_reply_for(raw, subtype="ack"),
        )
    return None
