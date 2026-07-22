"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { ChevronLeft, ChevronRight, LayoutGrid, Star } from "lucide-react";
import { useMemo } from "react";

import type { JaiosApp } from "@/lib/app-registry";
import type { AppNavItem } from "@/lib/app-registry";
import { filterNavByAccess, setCurrentAppId } from "@/lib/app-navigation";
import type { PlatformAccess } from "@/lib/admin";
import { getUserRole } from "@/lib/auth";
import { cn } from "@/lib/utils";

type Props = {
  app: JaiosApp;
  collapsed: boolean;
  onToggle: () => void;
  access: PlatformAccess | null;
};

function isNavActive(pathname: string, search: string, href: string): boolean {
  const [path, query] = href.split("?");
  const pathMatch = pathname === path || (path !== "/" && pathname.startsWith(`${path}/`));
  if (!query) return pathMatch && pathname === path;
  if (!pathMatch) return false;
  const params = new URLSearchParams(query);
  const current = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  for (const [k, v] of params.entries()) {
    if (current.get(k) !== v) return false;
  }
  return true;
}

export function ApplicationSidebar({ app, collapsed, onToggle, access }: Props) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const search = searchParams.toString() ? `?${searchParams.toString()}` : "";

  const nav = useMemo(
    () => filterNavByAccess(app.nav, access, getUserRole()),
    [app.nav, access],
  );

  const AppIcon = app.icon;

  return (
    <aside
      className={cn(
        "flex h-full shrink-0 flex-col border-r border-border/80 bg-card/95 backdrop-blur-md transition-[width] duration-200",
        collapsed ? "w-[4.25rem]" : "w-60",
      )}
    >
      <div className="flex h-14 items-center gap-2 border-b border-border/60 px-3">
        <Link
          href={app.homeHref}
          className={cn("flex min-w-0 flex-1 items-center gap-2.5 rounded-xl px-2 py-1.5 hover:bg-muted/50", collapsed && "justify-center")}
          title={app.label}
        >
          <span className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-xl", app.accent)}>
            <AppIcon className="h-5 w-5" strokeWidth={1.5} />
          </span>
          {!collapsed && (
            <span className="truncate text-sm font-semibold text-foreground">{app.label}</span>
          )}
        </Link>
        <button
          type="button"
          onClick={onToggle}
          className="hidden rounded-lg p-1.5 text-muted-foreground hover:bg-muted md:inline-flex"
          aria-label={collapsed ? "Expandir menú" : "Colapsar menú"}
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>

      <nav className="min-h-0 flex-1 space-y-0.5 overflow-y-auto p-2">
        {nav.map((item) => (
          <NavLink
            key={item.id}
            item={item}
            appId={app.id}
            active={isNavActive(pathname, search, item.href)}
            collapsed={collapsed}
          />
        ))}
      </nav>

      <div className="space-y-1 border-t border-border/60 p-2">
        <Link
          href="/dashboard"
          className={cn(
            "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-muted-foreground transition hover:bg-primary/8 hover:text-primary",
            collapsed && "justify-center px-2",
          )}
          title="Todas las aplicaciones"
        >
          <LayoutGrid className="h-4 w-4 shrink-0" />
          {!collapsed && <span>Aplicaciones</span>}
        </Link>
      </div>
    </aside>
  );
}

function NavLink({
  item,
  appId,
  active,
  collapsed,
}: {
  item: AppNavItem;
  appId: string;
  active: boolean;
  collapsed: boolean;
}) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      onClick={() => setCurrentAppId(appId)}
      title={collapsed ? item.label : undefined}
      className={cn(
        "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition",
        active ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
        collapsed && "justify-center px-2",
      )}
    >
      <Icon className="h-4 w-4 shrink-0" />
      {!collapsed && <span className="truncate">{item.label}</span>}
    </Link>
  );
}

export function FavoriteToggle({ appId, favorited, onToggle }: { appId: string; favorited: boolean; onToggle: (id: string) => void }) {
  return (
    <button
      type="button"
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        onToggle(appId);
      }}
      className="absolute right-2 top-2 rounded-full p-1 text-muted-foreground/50 transition hover:text-amber-500"
      aria-label={favorited ? "Quitar de favoritos" : "Agregar a favoritos"}
    >
      <Star className={cn("h-3.5 w-3.5", favorited && "fill-amber-400 text-amber-500")} />
    </button>
  );
}
