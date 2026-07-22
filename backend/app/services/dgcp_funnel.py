"""Embudo operativo de licitaciones — estados, transiciones y guía de acciones."""

from __future__ import annotations

from enum import Enum
from typing import NamedTuple

from fastapi import HTTPException


class FunnelStage(str, Enum):
    NUEVAS = "nuevas"
    INTERESADAS = "interesadas"
    EN_PREPARACION = "en_preparacion"
    LISTAS_PARA_PRESENTAR = "listas_para_presentar"
    PRESENTADAS = "presentadas"
    SUSPENDIDAS = "suspendidas"
    ADJUDICADAS = "adjudicadas"
    NO_ADJUDICADAS = "no_adjudicadas"
    DESCARTADAS = "descartadas"


class OpportunityAction(str, Enum):
    MARCAR_INTERES = "marcar_interes"
    DESMARCAR_INTERES = "desmarcar_interes"
    INICIAR_PREPARACION = "iniciar_preparacion"
    MARCAR_LISTO_PRESENTAR = "marcar_listo_presentar"
    MARCAR_PRESENTADA = "marcar_presentada"
    MARCAR_SUSPENDIDA = "marcar_suspendida"
    MARCAR_ADJUDICADA = "marcar_adjudicada"
    MARCAR_NO_ADJUDICADA = "marcar_no_adjudicada"
    DESCARTAR = "descartar"
    # Legacy aliases — aceptados en API, normalizados internamente
    MOSTRAR_INTERES = "mostrar_interes"
    REVISAR = "revisar"
    LICITAR = "licitar"
    GANADA = "ganada"
    PERDIDA = "perdida"


LEGACY_ACTION_ALIASES: dict[str, OpportunityAction] = {
    "mostrar_interes": OpportunityAction.MARCAR_INTERES,
    "revisar": OpportunityAction.DESMARCAR_INTERES,
    "licitar": OpportunityAction.INICIAR_PREPARACION,
    "ganada": OpportunityAction.MARCAR_ADJUDICADA,
    "perdida": OpportunityAction.MARCAR_NO_ADJUDICADA,
}

ACTION_TO_TARGET_STATUS: dict[OpportunityAction, str] = {
    OpportunityAction.MARCAR_INTERES: "interested",
    OpportunityAction.DESMARCAR_INTERES: "detected",
    OpportunityAction.INICIAR_PREPARACION: "preparing",
    OpportunityAction.MARCAR_LISTO_PRESENTAR: "ready_to_submit",
    OpportunityAction.MARCAR_PRESENTADA: "submitted",
    OpportunityAction.MARCAR_SUSPENDIDA: "suspended",
    OpportunityAction.MARCAR_ADJUDICADA: "awarded",
    OpportunityAction.MARCAR_NO_ADJUDICADA: "lost",
    OpportunityAction.DESCARTAR: "discarded",
}

ACTION_LABELS_ES: dict[str, str] = {
    "marcar_interes": "Marcar interés",
    "desmarcar_interes": "Desmarcar interés",
    "iniciar_preparacion": "Iniciar preparación",
    "marcar_listo_presentar": "Marcar listo para presentar",
    "marcar_presentada": "Marcar presentada",
    "marcar_suspendida": "Marcar suspendida",
    "marcar_adjudicada": "Marcar adjudicada",
    "marcar_no_adjudicada": "Marcar no adjudicada",
    "descartar": "Descartar",
}

FUNNEL_STAGE_LABELS_ES: dict[str, str] = {
    "nuevas": "Nuevas",
    "interesadas": "Interesadas",
    "en_preparacion": "En preparación",
    "listas_para_presentar": "Listas para presentar",
    "presentadas": "Presentadas",
    "suspendidas": "Suspendidas",
    "adjudicadas": "Adjudicadas",
    "no_adjudicadas": "No adjudicadas",
    "descartadas": "Descartadas",
}

STATUS_LABELS_ES: dict[str, str] = {
    "detected": "Nueva",
    "interested": "Interesada",
    "preparing": "En preparación",
    "ready_to_submit": "Lista para presentar",
    "submitted": "Presentada",
    "under_evaluation": "Presentada (en evaluación)",
    "suspended": "Suspendida",
    "awarded": "Adjudicada",
    "lost": "No adjudicada",
    "discarded": "Descartada",
    "cancelled": "Cancelada",
    # Legacy — se normalizan al mostrar
    "to_review": "Nueva (requiere revisión)",
    "to_bid": "En preparación",
    "won": "Adjudicada",
    "analyzing": "En análisis",
    "qualified": "Calificada",
    "not_qualified": "No calificada",
    "pending_documents": "Pendiente documentos",
}

# Estados agrupados por etapa del embudo (incluye legacy)
FUNNEL_STATUS_MAP: dict[FunnelStage, frozenset[str]] = {
    FunnelStage.NUEVAS: frozenset({"detected", "to_review", "analyzing", "qualified", "not_qualified"}),
    FunnelStage.INTERESADAS: frozenset({"interested"}),
    FunnelStage.EN_PREPARACION: frozenset({"preparing", "to_bid", "pending_documents"}),
    FunnelStage.LISTAS_PARA_PRESENTAR: frozenset({"ready_to_submit"}),
    FunnelStage.PRESENTADAS: frozenset({"submitted", "under_evaluation"}),
    FunnelStage.SUSPENDIDAS: frozenset({"suspended"}),
    FunnelStage.ADJUDICADAS: frozenset({"awarded", "won"}),
    FunnelStage.NO_ADJUDICADAS: frozenset({"lost"}),
    FunnelStage.DESCARTADAS: frozenset({"discarded", "cancelled"}),
}

EXPEDIENTE_FUNNEL_STAGES: frozenset[FunnelStage] = frozenset({
    FunnelStage.INTERESADAS,
    FunnelStage.EN_PREPARACION,
    FunnelStage.LISTAS_PARA_PRESENTAR,
    FunnelStage.PRESENTADAS,
    FunnelStage.ADJUDICADAS,
    FunnelStage.NO_ADJUDICADAS,
    FunnelStage.DESCARTADAS,
})

ALLOWED_TRANSITIONS: dict[str, frozenset[OpportunityAction]] = {
    "detected": frozenset({
        OpportunityAction.MARCAR_INTERES,
        OpportunityAction.DESCARTAR,
    }),
    "to_review": frozenset({
        OpportunityAction.MARCAR_INTERES,
        OpportunityAction.DESCARTAR,
    }),
    "interested": frozenset({
        OpportunityAction.DESMARCAR_INTERES,
        OpportunityAction.INICIAR_PREPARACION,
        OpportunityAction.MARCAR_SUSPENDIDA,
        OpportunityAction.DESCARTAR,
    }),
    "preparing": frozenset({
        OpportunityAction.MARCAR_LISTO_PRESENTAR,
        OpportunityAction.MARCAR_SUSPENDIDA,
        OpportunityAction.DESCARTAR,
    }),
    "to_bid": frozenset({
        OpportunityAction.MARCAR_LISTO_PRESENTAR,
        OpportunityAction.MARCAR_SUSPENDIDA,
        OpportunityAction.DESCARTAR,
    }),
    "ready_to_submit": frozenset({
        OpportunityAction.MARCAR_PRESENTADA,
        OpportunityAction.MARCAR_SUSPENDIDA,
        OpportunityAction.DESCARTAR,
    }),
    "submitted": frozenset({
        OpportunityAction.MARCAR_ADJUDICADA,
        OpportunityAction.MARCAR_NO_ADJUDICADA,
        OpportunityAction.MARCAR_SUSPENDIDA,
        OpportunityAction.DESCARTAR,
    }),
    "under_evaluation": frozenset({
        OpportunityAction.MARCAR_ADJUDICADA,
        OpportunityAction.MARCAR_NO_ADJUDICADA,
        OpportunityAction.MARCAR_SUSPENDIDA,
        OpportunityAction.DESCARTAR,
    }),
    "suspended": frozenset({
        OpportunityAction.DESMARCAR_INTERES,
        OpportunityAction.INICIAR_PREPARACION,
        OpportunityAction.MARCAR_LISTO_PRESENTAR,
        OpportunityAction.MARCAR_PRESENTADA,
        OpportunityAction.DESCARTAR,
    }),
    "awarded": frozenset({OpportunityAction.DESCARTAR}),
    "won": frozenset({OpportunityAction.DESCARTAR}),
    "lost": frozenset({OpportunityAction.DESCARTAR}),
    "discarded": frozenset(),
    "cancelled": frozenset(),
    # Pipeline huérfanos — permitir avanzar o descartar
    "analyzing": frozenset({OpportunityAction.MARCAR_INTERES, OpportunityAction.DESCARTAR}),
    "qualified": frozenset({OpportunityAction.INICIAR_PREPARACION, OpportunityAction.DESCARTAR}),
    "not_qualified": frozenset({OpportunityAction.DESCARTAR}),
    "pending_documents": frozenset({
        OpportunityAction.MARCAR_LISTO_PRESENTAR,
        OpportunityAction.DESCARTAR,
    }),
}

NEXT_ACTION_HINTS: dict[str, str] = {
    "detected": "Revise el proceso y marque interés si desea participar.",
    "to_review": "Revise el proceso y marque interés si desea participar.",
    "interested": "Inicie la preparación del expediente.",
    "preparing": "Complete el expediente y márquelo listo para presentar.",
    "to_bid": "Complete el expediente y márquelo listo para presentar.",
    "ready_to_submit": "Suba la oferta manualmente al portal DGCP y confirme con «Marcar presentada».",
    "submitted": "Registre el resultado: adjudicada o no adjudicada.",
    "under_evaluation": "Registre el resultado: adjudicada o no adjudicada.",
    "suspended": "Reanude el proceso o descarte si ya no participará.",
    "awarded": "Proceso cerrado — adjudicada.",
    "won": "Proceso cerrado — adjudicada.",
    "lost": "Proceso cerrado — no adjudicada.",
    "discarded": "Proceso descartado.",
    "cancelled": "Proceso cancelado.",
}


class FunnelGuidance(NamedTuple):
    funnel_stage: str
    funnel_stage_label: str
    status_label: str
    next_recommended_action: str
    primary_action: str | None
    available_actions: list[str]


def normalize_action(raw: str) -> OpportunityAction:
    try:
        action = OpportunityAction(raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Acción no válida: {raw}") from exc
    return LEGACY_ACTION_ALIASES.get(action.value, action)


def normalize_status(status: str) -> str:
    """Normaliza legacy a status canónico para transiciones."""
    if status == "to_bid":
        return "preparing"
    if status == "won":
        return "awarded"
    return status


def funnel_stage_for_status(status: str) -> FunnelStage:
    for stage, statuses in FUNNEL_STATUS_MAP.items():
        if status in statuses:
            return stage
    return FunnelStage.NUEVAS


def statuses_for_funnel_stage(stage: FunnelStage | str) -> frozenset[str]:
    if isinstance(stage, str):
        stage = FunnelStage(stage)
    return FUNNEL_STATUS_MAP[stage]


def validate_transition(from_status: str, raw_action: str | OpportunityAction) -> str:
    raw = raw_action.value if isinstance(raw_action, OpportunityAction) else raw_action
    action_enum = normalize_action(raw)
    current = from_status
    allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
    if action_enum not in allowed:
        stage = FUNNEL_STAGE_LABELS_ES[funnel_stage_for_status(current).value]
        action_label = ACTION_LABELS_ES.get(action_enum.value, action_enum.value)
        raise HTTPException(
            status_code=409,
            detail=f"No se puede «{action_label}» desde la etapa «{stage}».",
        )
    if action_enum in (OpportunityAction.MARCAR_ADJUDICADA, OpportunityAction.MARCAR_NO_ADJUDICADA):
        if current not in ("submitted", "under_evaluation"):
            raise HTTPException(
                status_code=409,
                detail="Solo puede registrar resultado después de marcar la oferta como presentada.",
            )
    return ACTION_TO_TARGET_STATUS[action_enum]


def available_actions_for_status(status: str) -> list[str]:
    return sorted(a.value for a in ALLOWED_TRANSITIONS.get(status, frozenset()))


def primary_action_for_status(status: str) -> str | None:
    priority = {
        "detected": "marcar_interes",
        "to_review": "marcar_interes",
        "interested": "iniciar_preparacion",
        "preparing": "marcar_listo_presentar",
        "to_bid": "marcar_listo_presentar",
        "ready_to_submit": "marcar_presentada",
        "submitted": "marcar_adjudicada",
        "under_evaluation": "marcar_adjudicada",
        "suspended": "iniciar_preparacion",
    }
    primary = priority.get(status)
    if primary and primary in available_actions_for_status(status):
        return primary
    actions = available_actions_for_status(status)
    return actions[0] if actions else None


def build_funnel_guidance(status: str, *, needs_review: bool = False) -> FunnelGuidance:
    stage = funnel_stage_for_status(status)
    status_label = STATUS_LABELS_ES.get(status, status)
    if needs_review and status in ("detected", "to_review"):
        status_label = "Nueva (requiere revisión)"
    hint = NEXT_ACTION_HINTS.get(status, "Revise el proceso.")
    if status == "ready_to_submit":
        hint = (
            "Suba la oferta manualmente al portal DGCP. "
            "JAIOS no asume que la oferta fue presentada hasta que usted confirme."
        )
    return FunnelGuidance(
        funnel_stage=stage.value,
        funnel_stage_label=FUNNEL_STAGE_LABELS_ES[stage.value],
        status_label=status_label,
        next_recommended_action=hint,
        primary_action=primary_action_for_status(status),
        available_actions=available_actions_for_status(status),
    )


def is_operational_interest_status(status: str) -> bool:
    """Proceso con interés operativo — tabs de expediente/checklist habilitadas."""
    return funnel_stage_for_status(status) in EXPEDIENTE_FUNNEL_STAGES or status in {
        "interested",
        "preparing",
        "to_bid",
        "ready_to_submit",
        "submitted",
        "under_evaluation",
        "suspended",
        "awarded",
        "won",
        "lost",
    }


def migrate_legacy_status_on_read(status: str, needs_review: bool) -> tuple[str, bool]:
    """Convierte to_review legacy a detected + needs_review."""
    if status == "to_review":
        return "detected", True
    return status, needs_review
