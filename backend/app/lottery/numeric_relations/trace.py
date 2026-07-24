"""Construcción de trazas auditables por coincidencia y por candidato."""

from __future__ import annotations

from app.lottery.numeric_relations.models import Match, StrengthenedCandidate


def build_match_trace(match: Match) -> str:
    group_s = ",".join(str(x) for x in match.table2_group)
    neighbors_s = ",".join(str(x) for x in match.neighbors)
    pos = match.position_label or str(match.position)
    return (
        f"salió {match.observed_number}"
        f" → ocurrencia histórica real del {match.observed_number}"
        f" ({match.lottery_name}, {match.draw_date.isoformat()}, sorteo {match.draw_id}, posición {pos})"
        f" → código madre {match.mother_code}"
        f" → compañero {match.companion}"
        f" → código Tabla 2 {match.table2_code}"
        f" → grupo Tabla 2 [{group_s}]"
        f" → vecinos [{neighbors_s}]"
        f" → vecino encontrado {match.neighbor}"
        f" → +{match.points} al compañero {match.companion}"
    )


def build_candidate_trace(candidate: StrengthenedCandidate, *, observed_number: int) -> str:
    if not candidate.matches:
        return (
            f"salió {observed_number}"
            f" → código madre {candidate.table1_code}"
            f" → compañero {candidate.number}"
            f" → código Tabla 2 {candidate.table2_code}"
            f" → sin coincidencias de vecinos → score 0"
        )
    matched = ",".join(str(x) for x in candidate.matched_neighbors)
    return (
        f"salió {observed_number}"
        f" → código madre {candidate.table1_code}"
        f" → compañero {candidate.number}"
        f" → código Tabla 2 {candidate.table2_code}"
        f" → vecinos coincidentes [{matched}]"
        f" → score {candidate.score}"
        f" → se fortalece {candidate.number} para el próximo sorteo"
    )
