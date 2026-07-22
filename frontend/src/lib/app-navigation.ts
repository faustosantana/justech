import type { PlatformAccess } from "@/lib/admin";
import { APP_BY_ID, JAIOS_APPS, type AppNavItem, type JaiosApp, type LauncherApp } from "@/lib/app-registry";
import { filterAppsByAccess as filterAppsByPermissions } from "@/lib/permissions";

const STORAGE_APP = "jaios-current-app";
const STORAGE_FAVORITES = "jaios-app-favorites";

export function setCurrentAppId(appId: string): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(STORAGE_APP, appId);
}

export function getCurrentAppId(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(STORAGE_APP);
}

export function getFavoriteAppIds(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_FAVORITES);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}

export function toggleFavoriteApp(appId: string): string[] {
  const current = getFavoriteAppIds();
  const next = current.includes(appId) ? current.filter((id) => id !== appId) : [...current, appId];
  localStorage.setItem(STORAGE_FAVORITES, JSON.stringify(next));
  return next;
}

function parseTab(search: string): string | null {
  if (!search) return null;
  return new URLSearchParams(search).get("tab");
}

function matchPrefix(pathname: string, prefixes: string[]): boolean {
  return prefixes.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

function resolveOdooApp(tab: string | null, storedId: string | null): JaiosApp | null {
  const odooApps = JAIOS_APPS.filter((a) => a.odooTabs?.length);
  if (tab) {
    const byTab = odooApps.find((a) => a.odooTabs?.includes(tab));
    if (byTab) return byTab;
  }
  if (storedId && APP_BY_ID[storedId]?.odooTabs) return APP_BY_ID[storedId];
  return APP_BY_ID.ventas ?? null;
}

export function resolveActiveApp(pathname: string, search = ""): JaiosApp | null {
  if (pathname === "/dashboard" || pathname === "/") return null;

  const stored = getCurrentAppId();

  if (pathname.startsWith("/apps/")) {
    const appId = pathname.split("/")[2];
    if (appId && APP_BY_ID[appId]) return APP_BY_ID[appId];
  }

  if (pathname.startsWith("/odoo")) {
    return resolveOdooApp(parseTab(search), stored);
  }

  if (pathname.startsWith("/empresas")) {
    if (/^\/empresas\/[^/]+$/.test(pathname)) {
      return APP_BY_ID.proveedores ?? APP_BY_ID["empresas-grupo"];
    }
    return APP_BY_ID["empresas-grupo"] ?? APP_BY_ID.crm;
  }

  if (pathname.startsWith("/comunicaciones")) {
    if (stored === "crm" && parseTab(search) === "contactos") return APP_BY_ID.crm;
    return APP_BY_ID.comunicaciones;
  }

  if (pathname.startsWith("/inteligencia")) {
    return APP_BY_ID["agentes-ia"];
  }

  for (const app of JAIOS_APPS) {
    if (app.id === "configuracion") continue;
    if (matchPrefix(pathname, app.routePrefixes)) {
      if (stored && APP_BY_ID[stored] && matchPrefix(pathname, APP_BY_ID[stored].routePrefixes)) {
        return APP_BY_ID[stored];
      }
      return app;
    }
  }

  if (pathname.startsWith("/configuracion") || pathname.startsWith("/admin")) {
    return APP_BY_ID.configuracion;
  }

  if (stored && APP_BY_ID[stored]) return APP_BY_ID[stored];
  return null;
}

export function filterNavByAccess(nav: AppNavItem[], access: PlatformAccess | null, userRole: string | null): AppNavItem[] {
  return nav.filter((item) => {
    if (item.roles?.length) {
      const role = (userRole ?? access?.role ?? "").toLowerCase();
      if (!item.roles.some((r) => role.includes(r))) return false;
    }
    if (item.moduleKey && access?.modules && access.modules[item.moduleKey] === false) return false;
    return true;
  });
}

export { filterAppsByAccess } from "@/lib/permissions";

export function filterLauncherApps(apps: LauncherApp[], access: PlatformAccess | null): LauncherApp[] {
  if (!access) return [];
  const allowedIds = new Set(filterAppsByPermissions(JAIOS_APPS, access).map((a) => a.id));
  return apps.filter((a) => allowedIds.has(a.id));
}

export type Breadcrumb = { label: string; href?: string };

export function buildBreadcrumbs(app: JaiosApp | null, pathname: string, search = ""): Breadcrumb[] {
  const crumbs: Breadcrumb[] = [{ label: "Aplicaciones", href: "/dashboard" }];
  if (!app) return crumbs;

  crumbs.push({ label: app.label, href: app.homeHref });

  if (pathname.startsWith("/apps/")) {
    const parts = pathname.split("/").filter(Boolean);
    const sectionId = parts[2];
    if (sectionId && sectionId !== app.id) {
      const navItem = app.nav.find((n) => n.href === `/apps/${app.id}/${sectionId}`);
      crumbs.push({ label: navItem?.label ?? sectionId.replace(/-/g, " ") });
    }
    return crumbs;
  }

  const full = `${pathname}${search}`;
  const activeNav = app.nav.find((n) => {
    const [path, query] = n.href.split("?");
    if (pathname !== path && !pathname.startsWith(`${path}/`)) return false;
    if (!query) return !search || pathname !== path ? pathname.startsWith(path) : true;
    return full.includes(query) || search.includes(query.split("=")[1] ?? "");
  });

  if (activeNav && activeNav.href !== app.homeHref) {
    crumbs.push({ label: activeNav.label });
  } else if (pathname !== app.homeHref.split("?")[0]) {
    const segment = pathname.split("/").filter(Boolean).pop();
    if (segment && segment !== app.id) {
      crumbs.push({ label: segment.replace(/-/g, " ") });
    }
  }

  return crumbs;
}

export function contextualSearchHref(app: JaiosApp | null, query: string): string {
  const q = encodeURIComponent(query.trim());
  if (app?.id === "licitaciones") {
    return `/apps/licitaciones/procesos?q=${q}`;
  }
  return `/search?q=${q}${app ? `&context=${encodeURIComponent(app.id)}` : ""}`;
}
