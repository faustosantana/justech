import type { OpportunityAction, OpportunityStatus } from "./dgcp";

export type FunnelStage =
  | "nuevas"
  | "interesadas"
  | "en_preparacion"
  | "listas_para_presentar"
  | "presentadas"
  | "suspendidas"
  | "adjudicadas"
  | "no_adjudicadas"
  | "descartadas";

export const FUNNEL_STAGES: FunnelStage[] = [
  "nuevas",
  "interesadas",
  "en_preparacion",
  "listas_para_presentar",
  "presentadas",
  "suspendidas",
  "adjudicadas",
  "no_adjudicadas",
  "descartadas",
];

export const EXPEDIENTE_FUNNEL_STAGES: FunnelStage[] = [
  "interesadas",
  "en_preparacion",
  "listas_para_presentar",
  "presentadas",
  "adjudicadas",
  "no_adjudicadas",
  "descartadas",
];

export const FUNNEL_STAGE_LABELS: Record<FunnelStage, string> = {
  nuevas: "Nuevas",
  interesadas: "Interesadas",
  en_preparacion: "En preparación",
  listas_para_presentar: "Listas para presentar",
  presentadas: "Presentadas",
  suspendidas: "Suspendidas",
  adjudicadas: "Adjudicadas",
  no_adjudicadas: "No adjudicadas",
  descartadas: "Descartadas",
};

export const ACTION_LABELS: Record<OpportunityAction, string> = {
  marcar_interes: "Marcar interés",
  desmarcar_interes: "Desmarcar interés",
  iniciar_preparacion: "Iniciar preparación",
  marcar_listo_presentar: "Marcar listo para presentar",
  marcar_presentada: "Marcar presentada",
  marcar_suspendida: "Marcar suspendida",
  marcar_adjudicada: "Marcar adjudicada",
  marcar_no_adjudicada: "Marcar no adjudicada",
  descartar: "Descartar",
  mostrar_interes: "Marcar interés",
  revisar: "Desmarcar interés",
  licitar: "Iniciar preparación",
  ganada: "Marcar adjudicada",
  perdida: "Marcar no adjudicada",
};

const FUNNEL_STATUS_MAP: Record<FunnelStage, OpportunityStatus[]> = {
  nuevas: ["detected", "to_review", "analyzing", "qualified", "not_qualified"],
  interesadas: ["interested"],
  en_preparacion: ["preparing", "to_bid", "pending_documents"],
  listas_para_presentar: ["ready_to_submit"],
  presentadas: ["submitted", "under_evaluation"],
  suspendidas: ["suspended"],
  adjudicadas: ["awarded", "won"],
  no_adjudicadas: ["lost"],
  descartadas: ["discarded", "cancelled"],
};

export function getOpportunityFunnelStage(status: OpportunityStatus): FunnelStage {
  for (const stage of FUNNEL_STAGES) {
    if (FUNNEL_STATUS_MAP[stage].includes(status)) return stage;
  }
  return "nuevas";
}

export function isDGCPOperationalInterest(status: OpportunityStatus): boolean {
  const stage = getOpportunityFunnelStage(status);
  return EXPEDIENTE_FUNNEL_STAGES.includes(stage) || stage === "suspendidas";
}

export function funnelLabelsRedundant(funnelStageLabel: string, statusLabel: string): boolean {
  if (!funnelStageLabel || !statusLabel) return true;
  if (funnelStageLabel === statusLabel) return true;
  const norm = (s: string) =>
    s
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/\s+/g, " ")
      .trim()
      .replace(/s$/, "");
  return norm(funnelStageLabel) === norm(statusLabel);
}

export function resolveOpportunityGuidance(opp: {
  status: OpportunityStatus;
  needs_review?: boolean;
  funnel_stage?: string | null;
  funnel_stage_label?: string | null;
  status_label?: string | null;
  next_recommended_action?: string | null;
  primary_action?: string | null;
  available_actions?: string[] | null;
}) {
  const funnelStage = (opp.funnel_stage as FunnelStage | undefined) ?? getOpportunityFunnelStage(opp.status);
  return {
    funnelStage,
    funnelStageLabel: opp.funnel_stage_label ?? FUNNEL_STAGE_LABELS[funnelStage],
    statusLabel: opp.status_label ?? opp.status,
    nextAction: opp.next_recommended_action ?? "",
    primaryAction: (opp.primary_action as OpportunityAction | null) ?? null,
    availableActions: (opp.available_actions ?? []) as OpportunityAction[],
  };
}
