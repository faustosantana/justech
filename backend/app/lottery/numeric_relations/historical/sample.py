"""Clasificación de tamaño de muestra (no oculta patrones)."""

from __future__ import annotations

from app.lottery.numeric_relations.historical.enums import SampleTier

WARNING_THRESHOLD = 10


def classify_sample(n: int) -> SampleTier:
    n = int(n)
    if n <= 0:
        return SampleTier.EMPTY
    if n <= 4:
        return SampleTier.VERY_LOW
    if n <= 9:
        return SampleTier.LOW
    if n <= 29:
        return SampleTier.MODERATE
    return SampleTier.SOLID


def sample_warning(n: int) -> str | None:
    """Advertencia si n < 10; no excluye el patrón."""
    n = int(n)
    if n <= 0:
        return "Sin ocurrencias para este patrón."
    if n < WARNING_THRESHOLD:
        return (
            f"Muestra insuficiente para certeza: esta condición solo se ha observado {n} veces. "
            "La clasificación no convierte el resultado en certeza estadística."
        )
    return None
