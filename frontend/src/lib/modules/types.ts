import type { LucideIcon } from "lucide-react";

export type ViewType = "dashboard" | "list" | "kanban" | "calendar" | "charts" | "reports" | "config";

export type ModuleKpi = {
  id: string;
  label: string;
  value: string;
  delta?: string;
  tone?: "default" | "primary" | "success" | "warning" | "danger";
  href?: string;
};

export type QuickAction = {
  id: string;
  label: string;
  icon: LucideIcon;
  href?: string;
  onClick?: "copilot";
  copilotPrompt?: string;
};

export type ModuleActivity = {
  id: string;
  title: string;
  subtitle?: string;
  href?: string;
  timestamp?: string;
};

export type ModuleSection = {
  id: string;
  label: string;
  icon: LucideIcon;
  contentKey: string;
  description?: string;
  views?: ViewType[];
  /** Ocultar del sidebar aunque la ruta exista (p. ej. placeholders). */
  navHidden?: boolean;
  /** Alcance de entidad: internal_company | customer | supplier | government_entity */
  entityScope?: "internal_company" | "customer" | "supplier" | "government_entity" | "contact";
  roles?: string[];
  moduleKey?: string;
  /** Tab Odoo cuando contentKey es odoo:tab */
  odooTab?: string;
  /** Ruta legacy para iframe interno opcional */
  legacyHref?: string;
};

export type ModuleDefinition = {
  id: string;
  label: string;
  icon: LucideIcon;
  accent: string;
  searchPlaceholder: string;
  adminOnly?: boolean;
  routePrefixes: string[];
  odooTabs?: string[];
  dashboardSubtitle?: string;
  sections: ModuleSection[];
  defaultQuickActions: QuickAction[];
  copilotSuggestions: string[];
};

export type ModuleDashboardData = {
  kpis: ModuleKpi[];
  activity: ModuleActivity[];
  alerts?: ModuleActivity[];
};

export function moduleBase(appId: string): string {
  return `/apps/${appId}`;
}

export function moduleSectionHref(appId: string, sectionId: string): string {
  return `/apps/${appId}/${sectionId}`;
}
