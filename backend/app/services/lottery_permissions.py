"""Permisos y aislamiento del módulo lottery."""

from __future__ import annotations

LOTTERY_PERMISSIONS = frozenset({
    "lottery.access",
    "lottery.search",
    "lottery.chat",
    "lottery.compare",
    "lottery.statistics",
    "lottery.export",
    "lottery.share",
    "lottery.saved_queries",
    "lottery.admin",
    "lottery.import",
    "lottery.sync",
    "lottery.audit",
})

LOTTERY_CLIENT_PERMISSIONS = frozenset({
    "lottery.access",
    "lottery.search",
    "lottery.chat",
    "lottery.compare",
    "lottery.statistics",
    "lottery.export",
    "lottery.saved_queries",
})
# lottery.share no incluido por defecto para Lottery Client.
LOTTERY_CLIENT_ROLE = "lottery_client"

# Prefijos API permitidos para el rol Lottery Client (aislamiento estricto).
LOTTERY_CLIENT_ALLOWED_API_PREFIXES = (
    "/api/v1/auth",
    "/api/v1/lottery",
    "/api/v1/health",
)

# Rutas de UI visibles para Lottery Client.
LOTTERY_CLIENT_ALLOWED_UI_ROUTES = frozenset({
    "/lottery",
    "/lottery/search",
    "/lottery/compare",
    "/lottery/statistics",
    "/lottery/chat",
    "/lottery/lotteries",
    "/lottery/saved",
    "/lottery/favorites",
    "/lottery/print",
})
# /lottery/admin/* explícitamente excluido

# Ambiguity: no mapping definitivo para "nacional dia" en Fase 1.
AMBIGUOUS_NACIONAL_DIA_CANDIDATES = (
    {"source_id": 20, "name": "La Primera Tarde", "confidence": "medium"},
    {"source_id": 21, "name": "La Suerte MD", "confidence": "medium"},
)

# Aliases confirmados (source_id) — no incluye Nacional Día.
CONFIRMED_PRIORITY_SOURCE_IDS = {
    "real": 13,
    "loteria real": 13,
    "lotería real": 13,
    "quiniela real": 13,
    "new york dia": 16,
    "new york día": 16,
    "ny dia": 16,
    "ny día": 16,
    "new york 2:30": 16,
    "loteka": 6,
    "quiniela loteka": 6,
    "leidsa": 5,
    "quiniela leidsa": 5,
    "nacional noche": 4,
    "loteria nacional": 4,
    "lotería nacional": 4,
    "new york noche": 17,
    "ny noche": 17,
    "new york 10:30": 17,
}

# Aliases que NO deben resolverse silenciosamente.
UNRESOLVED_AMBIGUOUS_ALIASES = frozenset({
    "nacional dia",
    "nacional día",
    "nacional",
})
