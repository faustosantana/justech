"""Schemas for the Complete Analysis Engine (versioned, auditable)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

ENGINE_VERSION = "complete-analysis-engine-j1.0.0"
TABLE_VERSION = "nr-historical-relations-j1.0.0"


class NodeType(str, Enum):
    OBSERVED = "número observado"
    RELATED_T1 = "número relacionado por Tabla 1"
    COMPANION_T1 = "compañero de Tabla 1"
    RELATED_T2 = "número relacionado por Tabla 2"
    NEIGHBOR_T2 = "vecino de Tabla 2"
    DERIVED = "número derivado"
    CANDIDATE = "candidato"
    FUERTE = "fuerte"
    HISTORICAL_RESULT = "resultado histórico"
    DRAW = "sorteo"
    LOTTERY = "lotería"
    POSITION = "posición"
    CASE = "caso"
    CHAIN = "cadena"


class EdgeType(str, Enum):
    T1_MOTHER_RELATION = "T1_MOTHER_RELATION"
    T1_COMPANION = "T1_COMPANION"
    T2_NEIGHBOR = "T2_NEIGHBOR"
    T2_CONFIRMATION = "T2_CONFIRMATION"
    DERIVATION_LEVEL_1 = "DERIVATION_LEVEL_1"
    DERIVATION_LEVEL_2 = "DERIVATION_LEVEL_2"
    CROSS_CONFIRMATION = "CROSS_CONFIRMATION"
    MULTI_SOURCE_SUPPORT = "MULTI_SOURCE_SUPPORT"
    INDEPENDENT_PATH = "INDEPENDENT_PATH"
    HISTORICAL_FULFILLMENT = "HISTORICAL_FULFILLMENT"
    SAME_DAY_CHAIN = "SAME_DAY_CHAIN"
    NEXT_DAY_CHAIN = "NEXT_DAY_CHAIN"
    CASE_CLOSED = "CASE_CLOSED"
    NEW_ANALYSIS_STARTED = "NEW_ANALYSIS_STARTED"


class Classification(str, Enum):
    FUERTE_PRINCIPAL = "FUERTE_PRINCIPAL"
    FUERTE_SECUNDARIO = "FUERTE_SECUNDARIO"
    CANDIDATO_CONFIRMADO = "CANDIDATO_CONFIRMADO"
    CANDIDATO_PARCIAL = "CANDIDATO_PARCIAL"
    DERIVACION_RELEVANTE = "DERIVACION_RELEVANTE"
    VECINO_T2_DIRECTO = "VECINO_T2_DIRECTO"
    FAMILIA_T1 = "FAMILIA_T1"
    SIN_EVIDENCIA_SUFICIENTE = "SIN_EVIDENCIA_SUFICIENTE"


class RankProfile(str, Enum):
    STRICT = "strict"
    BROAD = "amplio"
    MANUAL_RECONSTRUCTED = "manual_reconstruido"
    EXPERIMENTAL = "experimental"


class InputMode(str, Enum):
    FIRST_POSITIONS = "primeras_posiciones"
    ALL_POSITIONS = "todas_posiciones"
    MANUAL = "seleccion_manual"
    FEATURED_SEVEN = "featured_seven"


class SignalStatus(str, Enum):
    ACTIVO = "ACTIVO"
    CUMPLIDO_EXACTO = "CUMPLIDO_EXACTO"
    CUMPLIDO_FAMILIA_T1 = "CUMPLIDO_FAMILIA_T1"
    CUMPLIDO_VECINO_T2 = "CUMPLIDO_VECINO_T2"
    EXPIRADO = "EXPIRADO"
    CANCELADO = "CANCELADO"
    CERRADO = "CERRADO"


class ExplanationLevel(str, Enum):
    EXECUTIVE = "ejecutivo"
    ANALYTICAL = "analitico"
    TECHNICAL = "tecnico"


@dataclass
class GraphNode:
    node_id: str
    number: int | None
    node_type: str
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GraphEdge:
    evidence_id: str
    source: str
    target: str
    relation_type: str
    table_type: str | None
    observed_origin: int | None
    depth: int
    direct_or_indirect: str
    date: str | None = None
    lottery: str | None = None
    position: str | None = None
    engine_version: str = ENGINE_VERSION
    table_version: str = TABLE_VERSION
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DerivationPath:
    path_id: str
    route: list[int]
    observed_origin: int
    tables_used: list[str]
    relation_types: list[str]
    depth: int
    destination: int
    hops: int
    independent: bool
    reuses_nodes: bool
    forms_cycle: bool
    historical_support: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CandidateEvidence:
    candidate_number: int
    supporting_observed_numbers: list[int] = field(default_factory=list)
    table1_sources: list[int] = field(default_factory=list)
    table2_sources: list[int] = field(default_factory=list)
    table1_companions: list[int] = field(default_factory=list)
    table2_neighbors: list[int] = field(default_factory=list)
    direct_confirmers: list[int] = field(default_factory=list)
    indirect_confirmers: list[int] = field(default_factory=list)
    derivation_paths: list[dict[str, Any]] = field(default_factory=list)
    independent_path_count: int = 0
    total_path_count: int = 0
    direct_path_count: int = 0
    cross_table_support: bool = False
    multi_source_support: bool = False
    same_source_repetitions: int = 0
    historical_activations: int = 0
    historical_exact_hits: int = 0
    historical_first_position_hits: int = 0
    historical_any_position_hits: int = 0
    historical_t1_family_hits: int = 0
    historical_t2_neighbor_hits: int = 0
    median_days_to_exact: float | None = None
    average_days_to_exact: float | None = None
    d1_hits: int = 0
    d2_hits: int = 0
    d3_hits: int = 0
    d4_hits: int = 0
    d5_hits: int = 0
    d6_hits: int = 0
    d7_hits: int = 0
    lottery_distribution: dict[str, int] = field(default_factory=dict)
    position_distribution: dict[str, int] = field(default_factory=dict)
    year_distribution: dict[str, int] = field(default_factory=dict)
    recent_equivalent_cases: list[dict[str, Any]] = field(default_factory=list)
    exceptions: list[str] = field(default_factory=list)
    ambiguity_score: float = 0.0
    path_fingerprints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScoreComponents:
    T1_SOURCE_SUPPORT: float = 0.0
    T2_CONFIRMATION_SUPPORT: float = 0.0
    CROSS_TABLE_SUPPORT: float = 0.0
    MULTIPLE_OBSERVED_SUPPORT: float = 0.0
    INDEPENDENT_PATH_SUPPORT: float = 0.0
    DIRECT_PATH_SUPPORT: float = 0.0
    MULTI_CONFIRMATION_SUPPORT: float = 0.0
    HISTORICAL_EXACT_RATE: float = 0.0
    HISTORICAL_D1_D3_RATE: float = 0.0
    HISTORICAL_D1_D7_RATE: float = 0.0
    FIRST_POSITION_SUPPORT: float = 0.0
    ANY_POSITION_SUPPORT: float = 0.0
    RECENT_PATTERN_SUPPORT: float = 0.0
    CROSS_LOTTERY_SUPPORT: float = 0.0
    CHAIN_CONTINUITY_SUPPORT: float = 0.0
    DERIVATION_DEPTH_PENALTY: float = 0.0
    AMBIGUITY_PENALTY: float = 0.0
    DUPLICATE_PATH_PENALTY: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RankedCandidate:
    number: int
    classification: str
    classification_reason: str
    total_score: float
    components: ScoreComponents
    analytical_confidence: float
    evidence: CandidateEvidence
    positive_evidence: list[str] = field(default_factory=list)
    penalties: list[str] = field(default_factory=list)
    rank: int = 0
    gap_to_next: float | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["components"] = self.components.to_dict()
        d["evidence"] = self.evidence.to_dict()
        return d


@dataclass
class AnalysisRequest:
    numbers: list[int]
    date: date | None = None
    positions: list[str] = field(default_factory=lambda: ["first"])
    mode: str = RankProfile.MANUAL_RECONSTRUCTED.value
    derivation_depth: int = 2
    historical_window_years: int = 7
    lotteries: list[str] = field(default_factory=list)
    input_mode: str = InputMode.MANUAL.value
    create_signals: bool = True
    explanation_level: str = ExplanationLevel.ANALYTICAL.value


@dataclass
class ExperimentalSignal:
    signal_id: str
    number: int
    classification: str
    score: float
    analytical_confidence: float
    supporting_evidence: dict[str, Any]
    observed_numbers: list[int]
    analysis_date: str
    analysis_id: str
    lotteries: list[str]
    positions: list[str]
    mode: str
    derivation_depth: int
    estimated_window: list[str]
    historical_profile: dict[str, Any]
    alternatives: list[int]
    engine_version: str = ENGINE_VERSION
    status: str = SignalStatus.ACTIVO.value
    experimental: bool = True
    first_appearance_date: str | None = None
    relative_day: int | None = None
    first_lottery: str | None = None
    first_position: str | None = None
    all_appearances: list[dict[str, Any]] = field(default_factory=list)
    closed_at: str | None = None
    case_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CompleteAnalysisResult:
    analysis_id: str
    engine_version: str
    table_version: str
    observed_numbers: list[int]
    analysis_date: str | None
    positions: list[str]
    mode: str
    derivation_depth: int
    stages_completed: list[str]
    graph_complete_before_discovery: bool
    primary_signal: dict[str, Any] | None
    alternatives: list[dict[str, Any]]
    ranked_candidates: list[dict[str, Any]]
    evidence_summary: dict[str, Any]
    graph: dict[str, Any]
    derivations: list[dict[str, Any]]
    signals: list[dict[str, Any]]
    explanation: dict[str, Any]
    experimental: bool = True
    limitations: list[str] = field(default_factory=list)
    tiebreak: dict[str, Any] | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def new_id(prefix: str = "id") -> str:
    return f"{prefix}_{uuid4().hex[:12]}"
