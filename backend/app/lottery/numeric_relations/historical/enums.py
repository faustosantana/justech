"""Enums del analizador histórico de relaciones T1↔T2."""

from __future__ import annotations

from enum import Enum


class ConfirmationWindowMode(str, Enum):
    SAME_DRAW = "SAME_DRAW"
    SAME_DATE = "SAME_DATE"
    SAME_SESSION = "SAME_SESSION"
    HOURS_AFTER = "HOURS_AFTER"
    NEXT_DRAW_PER_CONFIRMING_LOTTERY = "NEXT_DRAW_PER_CONFIRMING_LOTTERY"
    NEXT_K_DRAWS = "NEXT_K_DRAWS"


class SessionBucket(str, Enum):
    MORNING = "morning"  # 00:00–11:59 local
    AFTERNOON = "afternoon"  # 12:00–17:59 local
    NIGHT = "night"  # 18:00–23:59 local


class SampleTier(str, Enum):
    VERY_LOW = "MUESTRA_MUY_BAJA"  # 1–4
    LOW = "MUESTRA_BAJA"  # 5–9
    MODERATE = "MUESTRA_MODERADA"  # 10–29
    SOLID = "MUESTRA_MAS_SOLIDA"  # 30+
    EMPTY = "SIN_MUESTRA"  # 0


class Horizon(str, Enum):
    NEXT_1 = "next_1"
    WITHIN_2 = "within_2"
    WITHIN_3 = "within_3"
    WITHIN_5 = "within_5"
    WITHIN_10 = "within_10"


HORIZON_OFFSETS: dict[Horizon, int] = {
    Horizon.NEXT_1: 1,
    Horizon.WITHIN_2: 2,
    Horizon.WITHIN_3: 3,
    Horizon.WITHIN_5: 5,
    Horizon.WITHIN_10: 10,
}
