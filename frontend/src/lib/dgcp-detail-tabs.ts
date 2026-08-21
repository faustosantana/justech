/** Navegación canónica del detalle DGCP (workspace) + aliases legacy. */

import {
  Brain,
  ClipboardList,
  FileStack,
  LayoutDashboard,
  Landmark,
  ListChecks,
  Package,
  Wrench,
  type LucideIcon,
} from "lucide-react";

export const DGCP_DETAIL_TABS = [
  { id: "resumen", label: "Resumen", icon: LayoutDashboard, shortLabel: "Resumen" },
  { id: "analisis-ia", label: "Análisis IA", icon: Brain, shortLabel: "Análisis" },
  { id: "documentos", label: "Documentos", icon: FileStack, shortLabel: "Documentos" },
  { id: "checklist", label: "Checklist", icon: ListChecks, shortLabel: "Checklist" },
  { id: "fichas", label: "Fichas técnicas", icon: Wrench, shortLabel: "Fichas" },
  { id: "tareas", label: "Tareas", icon: ClipboardList, shortLabel: "Tareas" },
  { id: "adjudicaciones", label: "Inteligencia", icon: Landmark, shortLabel: "Inteligencia" },
  { id: "expediente", label: "Expediente", icon: Package, shortLabel: "Expediente" },
] as const;

export type DgcpDetailTabId = (typeof DGCP_DETAIL_TABS)[number]["id"];

/** Rutas antiguas → pestaña canónica (compatibilidad de enlaces). */
export const DGCP_LEGACY_TAB_ALIASES: Record<string, DgcpDetailTabId> = {
  requisitos: "analisis-ia",
  alertas: "analisis-ia",
  riesgos: "analisis-ia",
  "documentos-proceso": "documentos",
  "documentos-justech": "documentos",
  autollenado: "documentos",
  formularios: "documentos",
  "documentos-solicitados": "documentos",
  "fichas-tecnicas": "fichas",
  historico: "adjudicaciones",
  "inteligencia-historica": "adjudicaciones",
  comercial: "expediente",
  historial: "expediente",
  registro: "expediente",
};

export function resolveDgcpDetailTab(raw: string | null | undefined): DgcpDetailTabId {
  if (!raw) return "resumen";
  if (DGCP_DETAIL_TABS.some((t) => t.id === raw)) return raw as DgcpDetailTabId;
  return DGCP_LEGACY_TAB_ALIASES[raw] ?? "resumen";
}

export type DgcpDetailTabDef = {
  id: DgcpDetailTabId;
  label: string;
  icon: LucideIcon;
  shortLabel?: string;
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
