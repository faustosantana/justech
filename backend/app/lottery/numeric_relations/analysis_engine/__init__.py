"""Complete Analysis Engine package — Motor Automático de Relaciones Numéricas."""

from app.lottery.numeric_relations.analysis_engine.complete_analysis_service import (
    chain_timeline,
    run_complete_analysis,
)
from app.lottery.numeric_relations.analysis_engine.schemas import (
    ENGINE_VERSION,
    TABLE_VERSION,
    AnalysisRequest,
    CompleteAnalysisResult,
)

__all__ = [
    "ENGINE_VERSION",
    "TABLE_VERSION",
    "AnalysisRequest",
    "CompleteAnalysisResult",
    "run_complete_analysis",
    "chain_timeline",
]
