/** Catálogo de módulos JAIOS — espejo del registro backend (solo lectura UI). */

export type ModuleStatus = "delivered" | "active" | "planned" | "future";

export interface PlatformModule {
  id: string;
  name: string;
  phase: number;
  status: ModuleStatus;
  route?: string;
}

export const PLATFORM_MODULES: PlatformModule[] = [
  { id: "core", name: "Plataforma base", phase: 1, status: "delivered" },
  { id: "dgcp", name: "Centro de Inteligencia DGCP", phase: 2, status: "delivered", route: "/dgcp" },
  { id: "odoo", name: "Centro de Inteligencia Odoo", phase: 3, status: "active", route: "/odoo" },
  { id: "m365", name: "Centro de Inteligencia Microsoft 365", phase: 4, status: "active", route: "/m365" },
  { id: "tasks", name: "Tareas y asignaciones", phase: 5, status: "active", route: "/tasks" },
  { id: "notifications", name: "Notificaciones", phase: 5, status: "active", route: "/notifications" },
  { id: "work_hub", name: "Centro de Trabajo", phase: 5, status: "active", route: "/work" },
  { id: "enterprise_search", name: "Búsqueda empresarial", phase: 6, status: "active", route: "/search" },
  { id: "search_acceleration", name: "Motor de aceleración de búsqueda", phase: 6, status: "active" },
  { id: "document_repository", name: "Repositorio documental", phase: 6, status: "active", route: "/documents" },
  { id: "supplier_intelligence", name: "Inteligencia de proveedores", phase: 6, status: "future" },
  { id: "lottery", name: "Lottery IA Control Center", phase: 6, status: "active", route: "/lottery" },
  { id: "price_intelligence", name: "Inteligencia de precios", phase: 6, status: "active", route: "/prices" },
  { id: "hermes_memory", name: "Memoria empresarial Hermes", phase: 7, status: "future" },
  { id: "multi_agent", name: "Operaciones multi-agente", phase: 7, status: "future" },
];

const STATUS_LABELS: Record<ModuleStatus, string> = {
  delivered: "Entregado",
  active: "Activo",
  planned: "Fase planificada",
  future: "Futuro",
};

const STATUS_CLASS: Record<ModuleStatus, string> = {
  delivered: "text-muted-foreground",
  active: "text-success",
  planned: "text-warning",
  future: "text-muted-foreground/60",
};

export function moduleStatusLabel(status: ModuleStatus): string {
  return STATUS_LABELS[status];
}

export function moduleStatusClass(status: ModuleStatus): string {
  return STATUS_CLASS[status];
}
