/** Navegación canónica del detalle DGCP (7 pestañas) + aliases legacy. */

import {
  Brain,
  ClipboardList,
  FileStack,
  Landmark,
  ListChecks,
  Package,
  Wrench,
  type LucideIcon,
} from "lucide-react";

export const DGCP_DETAIL_TABS = [
  { id: "analisis-ia", label: "Análisis IA", icon: Brain },
  { id: "documentos", label: "Documentos solicitados", icon: FileStack },
  { id: "checklist", label: "Checklist", icon: ListChecks },
  { id: "fichas", label: "Fichas técnicas", icon: Wrench },
  { id: "tareas", label: "Tareas", icon: ClipboardList },
  { id: "adjudicaciones", label: "Inteligencia histórica", icon: Landmark },
  { id: "expediente", label: "Expediente", icon: Package },
] as const;

export type DgcpDetailTabId = (typeof DGCP_DETAIL_TABS)[number]["id"];

/** Rutas antiguas → pestaña canónica (compatibilidad de enlaces). */
export const DGCP_LEGACY_TAB_ALIASES: Record<string, DgcpDetailTabId> = {
  resumen: "analisis-ia",
  requisitos: "analisis-ia",
  alertas: "analisis-ia",
  riesgos: "analisis-ia",
  "documentos-proceso": "documentos",
  "documentos-justech": "documentos",
  autollenado: "documentos",
  formularios: "documentos",
  "fichas-tecnicas": "fichas",
  historico: "adjudicaciones",
  comercial: "expediente",
  historial: "expediente",
  registro: "expediente",
};

export function resolveDgcpDetailTab(raw: string | null | undefined): DgcpDetailTabId {
  if (!raw) return "analisis-ia";
  if (DGCP_DETAIL_TABS.some((t) => t.id === raw)) return raw as DgcpDetailTabId;
  return DGCP_LEGACY_TAB_ALIASES[raw] ?? "analisis-ia";
}

export type DgcpDetailTabDef = {
  id: DgcpDetailTabId;
  label: string;
  icon: LucideIcon;
};

/** Filtra recomendaciones/riesgos con ruido técnico interno. */
export function isUserFacingRecommendation(text: string): boolean {
  const t = (text || "").trim();
  if (!t) return false;
  const lower = t.toLowerCase();
  const blocked = [
    "company_key",
    "company key",
    "manufacturer",
    "proveedor_estado",
    "regex",
    "token",
    "variable",
    "json",
    "ventas corporativas",
    "logística",
    "logistica",
    "field_name",
    "snake_case",
    "uuid",
    "prompt_hash",
    "model=",
  ];
  if (blocked.some((b) => lower.includes(b))) return false;
  if (/^[a-z0-9_]+$/.test(t) && t.includes("_")) return false;
  if (t.startsWith("{") || t.startsWith("[")) return false;
  return true;
}
