import { LayoutDashboard, type LucideIcon } from "lucide-react";

import { MODULE_REGISTRY, moduleToNav } from "@/lib/modules/registry";
import { moduleBase } from "@/lib/modules/types";

export type AppNavItem = {
  id: string;
  label: string;
  href: string;
  icon: LucideIcon;
  roles?: string[];
  moduleKey?: string;
};

export type JaiosApp = {
  id: string;
  label: string;
  homeHref: string;
  icon: LucideIcon;
  accent: string;
  routePrefixes: string[];
  odooTabs?: string[];
  nav: AppNavItem[];
  searchPlaceholder: string;
  adminOnly?: boolean;
};

export const JAIOS_APPS: JaiosApp[] = MODULE_REGISTRY.map((m) => ({
  id: m.id,
  label: m.label,
  homeHref: moduleBase(m.id),
  icon: m.icon,
  accent: m.accent,
  routePrefixes: [moduleBase(m.id), ...m.routePrefixes.filter((p) => !p.startsWith("/apps/"))],
  odooTabs: m.odooTabs,
  searchPlaceholder: m.searchPlaceholder,
  adminOnly: m.adminOnly,
  nav: [
    { id: "dashboard", label: "Dashboard", href: moduleBase(m.id), icon: LayoutDashboard },
    ...moduleToNav(m),
  ],
}));

export const APP_BY_ID = Object.fromEntries(JAIOS_APPS.map((a) => [a.id, a])) as Record<string, JaiosApp>;

export type LauncherApp = {
  id: string;
  label: string;
  href: string;
  icon: LucideIcon;
  accent: string;
};

export const LAUNCHER_APPS: LauncherApp[] = JAIOS_APPS.map((a) => ({
  id: a.id,
  label: a.label,
  href: a.homeHref,
  icon: a.icon,
  accent: a.accent,
}));
