/** Feature flags DGCP — Fases 2–4 (fallback legacy cuando false). */

function envFlag(name: string, defaultOn = true): boolean {
  const raw = process.env[name];
  if (raw === undefined || raw === "") return defaultOn;
  return raw === "1" || raw.toLowerCase() === "true";
}

export const dgcpDynamicChecklistEnabled = () =>
  envFlag("NEXT_PUBLIC_DGCP_DYNAMIC_CHECKLIST", true);

export const dgcpSmartAutofillEnabled = () =>
  envFlag("NEXT_PUBLIC_DGCP_SMART_AUTOFILL", true);

/** Fase 0: tab Autollenado en barra principal. false = acceso secundario (Formularios). */
export const dgcpAutofillPrimaryTabEnabled = () => {
  const raw = process.env.NEXT_PUBLIC_DGCP_AUTOFILL_PRIMARY_TAB;
  if (raw === undefined || raw === "") return false;
  return raw === "1" || raw.toLowerCase() === "true";
};

/** Fase 2: Centro de Preparación como vista principal del proceso. */
export const dgcpPreparationCenterEnabled = () => {
  const raw = process.env.NEXT_PUBLIC_DGCP_PREPARATION_CENTER;
  if (raw === undefined || raw === "") return false;
  return raw === "1" || raw.toLowerCase() === "true";
};

export const dgcpUnifiedExpedienteEnabled = () =>
  envFlag("NEXT_PUBLIC_DGCP_UNIFIED_EXPEDIENTE", true);

export const dgcpHermesDocumentAnalysisEnabled = () =>
  envFlag("NEXT_PUBLIC_DGCP_HERMES_DOCUMENT_ANALYSIS", true);

export const dgcpTechSheetsEnabled = () => {
  const raw = process.env.NEXT_PUBLIC_DGCP_TECH_SHEETS;
  if (raw === undefined || raw === "") return false;
  return raw === "1" || raw.toLowerCase() === "true";
};

export const dgcpExpedienteTechnicalIntelligenceEnabled = () => {
  const raw = process.env.NEXT_PUBLIC_DGCP_PRODUCT_INTELLIGENCE;
  if (raw === undefined || raw === "") return false;
  return raw === "1" || raw.toLowerCase() === "true";
};

/** @deprecated Use dgcpExpedienteTechnicalIntelligenceEnabled */
export const dgcpProductIntelligenceEnabled = dgcpExpedienteTechnicalIntelligenceEnabled;

export const dgcpOfferPreparationCenterEnabled = () => {
  const raw = process.env.NEXT_PUBLIC_DGCP_OFFER_PREPARATION_CENTER;
  if (raw === undefined || raw === "") return false;
  return raw === "1" || raw.toLowerCase() === "true";
};

export const dgcpProcessUpdatesEnabled = () => {
  const raw = process.env.NEXT_PUBLIC_DGCP_PROCESS_UPDATES;
  if (raw === undefined || raw === "") return false;
  return raw === "1" || raw.toLowerCase() === "true";
};

export const UNIFIED_STATUS_LABELS: Record<string, string> = {
  detectado: "Detectado",
  pendiente: "Pendiente",
  completado: "Completado",
  vencido: "Vencido",
  requiere_revision: "Requiere revisión",
  rechazado: "Rechazado",
  no_aplica: "No aplica",
};
