import type { PlatformAccess } from "@/lib/admin";
import type { JaiosApp } from "@/lib/app-registry";

export const MUTATE_DENIED_MESSAGE = "No tienes permiso para realizar esta acción.";

/** Mapa app ID → clave en allowed_modules (cuando difiere del id). */
export const APP_MODULE_KEY: Record<string, string> = {
  precios: "prices",
  proveedores: "suppliers",
};

export function hasPermission(access: PlatformAccess | null, permission: string): boolean {
  if (!access) return false;
  return access.permissions.includes(permission);
}

export function canMutate(access: PlatformAccess | null, permission: string): boolean {
  return hasPermission(access, permission);
}

function passesAllowedModules(appId: string, access: PlatformAccess): boolean {
  if (access.allowed_modules == null || access.allowed_modules.length === 0) {
    return true;
  }
  const allowed = new Set(access.allowed_modules);
  const moduleKey = APP_MODULE_KEY[appId] ?? appId;
  return allowed.has(appId) || allowed.has(moduleKey);
}

function canViewAppByRole(app: JaiosApp, access: PlatformAccess): boolean {
  if (app.adminOnly) {
    return access.can_view_admin;
  }

  switch (app.id) {
    case "empresas-grupo":
    case "documentos":
      return hasPermission(access, "view_documents");
    case "licitaciones":
      return hasPermission(access, "view_dgcp");
    case "calendario":
      return hasPermission(access, "view_m365");
    case "agentes-ia":
      return hasPermission(access, "view_assistant");
    case "precios":
      return access.can_view_prices;
    case "proveedores":
      return access.can_view_suppliers;
    case "crm":
    case "ventas":
    case "compras":
    case "inventario":
    case "facturacion":
    case "clientes":
      return hasPermission(access, "view_odoo");
    default:
      return hasPermission(access, "view_modules");
  }
}

export function filterAppsByAccess(apps: JaiosApp[], access: PlatformAccess | null): JaiosApp[] {
  if (!access) return [];

  return apps.filter((app) => passesAllowedModules(app.id, access) && canViewAppByRole(app, access));
}
