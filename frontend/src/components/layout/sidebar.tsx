"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Bell,
  Briefcase,
  Building2,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Database,
  FileSearch,
  FileStack,
  LayoutDashboard,
  LineChart,
  Search,
  Settings,
  Shield,
  Target,
} from "lucide-react";

import { BrandLogo } from "@/components/brand/brand-logo";
import { apiClient } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import { t } from "@/i18n";
import { cn } from "@/lib/utils";

const messages = t();

type NavItem = {
  href: string;
  label: string;
  icon: typeof LayoutDashboard;
  badge?: boolean;
};

type NavGroup = {
  label: string;
  items: NavItem[];
};

const NAV_GROUPS: NavGroup[] = [
  {
    label: "Inicio",
    items: [{ href: "/dashboard", label: "Command Center", icon: LayoutDashboard }],
  },
  {
    label: "Operaciones",
    items: [
      { href: "/work", label: messages.nav.work, icon: Briefcase },
      { href: "/tasks", label: messages.nav.tasks, icon: ClipboardList },
      { href: "/notifications", label: messages.nav.notifications, icon: Bell, badge: true },
    ],
  },
  {
    label: "Comercial",
    items: [
      { href: "/odoo", label: "Clientes y ventas", icon: Database },
      { href: "/prices/drafts", label: "Cotizaciones", icon: ClipboardList },
      { href: "/prices", label: messages.nav.prices, icon: LineChart },
    ],
  },
  {
    label: "Licitaciones",
    items: [
      { href: "/dgcp", label: "DGCP", icon: FileSearch },
      { href: "/oportunidades", label: "Expedientes DGCP", icon: Target },
    ],
  },
  {
    label: "Documentos",
    items: [{ href: "/documents", label: "Repositorio", icon: FileStack }],
  },
  {
    label: "Plataforma",
    items: [
      { href: "/search", label: messages.nav.search, icon: Search },
      { href: "/m365", label: messages.nav.m365, icon: Target },
    ],
  },
  {
    label: "Administración",
    items: [
      { href: "/empresas", label: "Empresas y proveedores", icon: Building2 },
      { href: "/configuracion", label: messages.nav.settings, icon: Settings },
    ],
  },
];

interface SidebarProps {
  collapsed?: boolean;
  onToggle?: () => void;
}

function isActive(pathname: string, href: string): boolean {
  if (pathname === href) return true;
  if (href === "/dashboard") return false;
  if (href === "/prices") {
    return pathname.startsWith("/prices") && !pathname.startsWith("/prices/drafts");
  }
  if (href === "/prices/drafts") {
    return pathname.startsWith("/prices/drafts");
  }
  return pathname.startsWith(`${href}/`) || pathname.startsWith(href);
}

export function Sidebar({ collapsed = false, onToggle }: SidebarProps) {
  const pathname = usePathname();
  const [unread, setUnread] = useState(0);
  const [showAdmin, setShowAdmin] = useState(false);

  useEffect(() => {
    if (!getAccessToken()) return;
    apiClient.getNotificationUnreadCount()
      .then((r) => setUnread(r.unread_count))
      .catch(() => setUnread(0));
    apiClient.getAdminAccess()
      .then((a) => setShowAdmin(a.can_view))
      .catch(() => setShowAdmin(false));
  }, [pathname]);

  const groups: NavGroup[] = [
    ...NAV_GROUPS,
    ...(showAdmin
      ? [{
          label: "Centro admin",
          items: [{ href: "/admin", label: "Usuarios y permisos", icon: Shield }],
        }]
      : []),
  ];

  return (
    <aside
      className={cn(
        "brand-sidebar flex h-full shrink-0 flex-col transition-[width] duration-200",
        collapsed ? "w-[4.25rem]" : "w-64",
      )}
    >
      <div className="flex h-16 shrink-0 items-center justify-between border-b border-border/70 px-3">
        <BrandLogo
          size="sm"
          iconOnly={collapsed}
          showSubtitle={!collapsed}
          href="/dashboard"
          className={cn(collapsed && "mx-auto")}
        />
        {onToggle && (
          <button
            type="button"
            onClick={onToggle}
            className="hidden rounded-lg p-1.5 text-muted-foreground hover:bg-muted md:inline-flex"
            aria-label={collapsed ? "Expandir menú" : "Colapsar menú"}
          >
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </button>
        )}
      </div>

      <nav className="min-h-0 flex-1 space-y-4 overflow-y-auto p-2">
        {groups.map((group) => (
          <div key={group.label}>
            {!collapsed && (
              <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/70">
                {group.label}
              </p>
            )}
            <div className="space-y-1">
              {group.items.map(({ href, label, icon: Icon, badge }) => {
                const active = isActive(pathname, href);
                return (
                  <Link
                    key={href}
                    href={href}
                    title={collapsed ? label : undefined}
                    className={cn(
                      "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium",
                      active ? "brand-sidebar-nav-active" : "brand-sidebar-nav-item",
                      collapsed && "justify-center px-2",
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    {!collapsed && <span className="flex-1 truncate">{label}</span>}
                    {!collapsed && badge && unread > 0 && (
                      <span className="rounded-full bg-primary px-1.5 py-0.5 text-[10px] font-bold text-primary-foreground">
                        {unread > 99 ? "99+" : unread}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>
    </aside>
  );
}
