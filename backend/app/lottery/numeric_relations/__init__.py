"""Motor de Relaciones Numéricas para Loterías (Fases A+B).

Universo fijo 1..100. Tabla 1 madre (n÷1220) y Tabla 2 confirmación (1220÷n).
Análisis histórico anclado a drawn_number = observed_number N.
"""

from __future__ import annotations

from app.lottery.numeric_relations.analysis import (
    analyze_mother_code,
    analyze_observed_number,
    match_neighbors_against_draw_numbers,
)
from app.lottery.numeric_relations.catalog import (
    TableCatalog,
    build_catalog,
    get_table1_companions,
    get_table2_code_for_number,
    get_table2_neighbors,
)
from app.lottery.numeric_relations.constants import DIVISOR, N_MAX, N_MIN
from app.lottery.numeric_relations.decimal_math import sum_literal_digits
from app.lottery.numeric_relations.history import DrawHistoryPort, InMemoryDrawHistory
from app.lottery.numeric_relations.models import (
    AnalysisResult,
    OccurrenceLimit,
    StrengthenedCandidate,
)
from app.lottery.numeric_relations.scoring import make_dedupe_key, score_candidate
from app.lottery.numeric_relations.service import NumericRelationsService
from app.lottery.numeric_relations.table1 import (
    calculate_table1_value,
    format_table1_digits,
    generate_table1,
    group_table1_by_code,
)
from app.lottery.numeric_relations.table2 import (
    calculate_table2_value,
    format_table2_digits,
    generate_table2,
    group_table2_by_code,
)

__all__ = [
    "N_MIN",
    "N_MAX",
    "DIVISOR",
    "TableCatalog",
    "OccurrenceLimit",
    "AnalysisResult",
    "StrengthenedCandidate",
    "DrawHistoryPort",
    "InMemoryDrawHistory",
    "NumericRelationsService",
    "build_catalog",
    "calculate_table1_value",
    "calculate_table2_value",
    "format_table1_digits",
    "format_table2_digits",
    "sum_literal_digits",
    "generate_table1",
    "generate_table2",
    "group_table1_by_code",
    "group_table2_by_code",
    "get_table1_companions",
    "get_table2_code_for_number",
    "get_table2_neighbors",
    "match_neighbors_against_draw_numbers",
    "analyze_observed_number",
    "analyze_mother_code",
    "make_dedupe_key",
    "score_candidate",
]
