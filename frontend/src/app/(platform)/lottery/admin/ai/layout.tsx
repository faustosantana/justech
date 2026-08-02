"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { LotteryAIDevModeProvider, useLotteryAIDevMode } from "@/components/lottery/ai-admin-dev-mode";
import { apiClient } from "@/lib/api";
import { getAccessToken, getUserRole } from "@/lib/auth";
import { canAccessLotteryAdmin, isLotteryClientRole } from "@/lib/lottery";

/**
 * Pre-J11A (TD-002): admin/ai se renderiza dentro del AppShell oficial.
 * Sin sidebar/header propios — una sola identidad Lottery IA Control Center.
 * La navegación secundaria de IA es una tira in-content (no shell).
 */

const NAV_GROUPS = [
  {
    label: "Resumen",
    items: [
      { label: "Dashboard", href: "/lottery/admin/ai" },
      { label: "Alertas", href: "/lottery/admin/ai#alerts" },
    ],
  },
  {
    label: "Configuración",
    items: [
      { label: "Configuración IA", href: "/lottery/admin/ai/configuracion" },
      { label: "Agente", href: "/lottery/admin/ai/agent" },
      { label: "Prompts", href: "/lottery/admin/ai/prompts" },
      { label: "Modelos", href: "/lottery/admin/ai/models" },
      { label: "Memoria", href: "/lottery/admin/ai/memory" },
      { label: "Tools", href: "/lottery/admin/ai/tools" },
      { label: "Paquetes", href: "/lottery/admin/ai/analysis-packs" },
      { label: "Predeterminadas", href: "/lottery/admin/ai/defaults" },
      { label: "Seguridad", href: "/lottery/admin/ai/safety" },
    ],
  },
  {
    label: "Pruebas",
    items: [
      { label: "Playground", href: "/lottery/admin/ai/playground" },
      { label: "Benchmarks", href: "/lottery/admin/ai/benchmarks" },
    ],
  },
  {
    label: "Operación",
    items: [
      { label: "Sesiones", href: "/lottery/admin/ai/sessions" },
      { label: "Versiones", href: "/lottery/admin/ai/versions" },
      { label: "Auditoría", href: "/lottery/admin/ai/audit" },
    ],
  },
];

function DevModeToggle() {
  const { developerMode, setDeveloperMode } = useLotteryAIDevMode();
  const [busy, setBusy] = useState(false);

  const toggle = async () => {
    const next = !developerMode;
    if (
      next &&
      !window.confirm(
        "¿Activar Modo desarrollador? Se mostrarán UUID, JSON y nombres internos. Quedará auditado.",
      )
    ) {
      return;
    }
    setBusy(true);
    try {
      await apiClient.postLotteryAIDeveloperMode(next);
      setDeveloperMode(next);
    } catch {
      setDeveloperMode(next);
    } finally {
      setBusy(false);
    }
  };

  return (
    <label className="flex cursor-pointer items-center gap-2 text-xs text-muted-foreground">
      <input type="checkbox" checked={developerMode} disabled={busy} onChange={() => void toggle()} />
      Modo desarrollador
    </label>
  );
}

function LayoutInner({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [denied, setDenied] = useState(false);
  const [checking, setChecking] = useState(true);
  const [openAlerts, setOpenAlerts] = useState(0);

  useEffect(() => {
    if (!getAccessToken()) {
      router.replace("/login?session=expired");
      return;
    }
    const role = getUserRole();
    if (isLotteryClientRole(role)) {
      setDenied(true);
      router.replace("/lottery");
      return;
    }
    apiClient
      .getPlatformAccess()
      .then((access) => {
        const perms = access?.permissions ?? [];
        if (!canAccessLotteryAdmin(role, perms)) {
          setDenied(true);
          router.replace("/lottery");
        }
      })
      .catch(() => {
        if (!canAccessLotteryAdmin(role)) {
          setDenied(true);
          router.replace("/lottery");
        }
      })
      .finally(() => setChecking(false));
    apiClient
      .getLotteryAIAlerts({ status: "open", limit: 1 })
      .then((res) => setOpenAlerts(Number(res.open_alerts_count ?? res.counts?.open ?? 0)))
      .catch(() => setOpenAlerts(0));
  }, [router]);

  if (checking) {
    return (
      <AppShell title="Centro de IA" description="Administración de Lottery IA">
        <div className="p-6 text-sm text-muted-foreground">Verificando acceso…</div>
      </AppShell>
    );
  }

  if (denied) {
    return (
      <AppShell title="Centro de IA">
        <div className="p-6 text-sm text-destructive">Acceso denegado</div>
      </AppShell>
    );
  }

  const flatItems = NAV_GROUPS.flatMap((g) => g.items);

  return (
    <AppShell title="Centro de IA" description="Administración de Lottery IA dentro de Lottery IA Control Center">
      <div className="mx-auto max-w-7xl space-y-4 p-4 min-[769px]:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3">
          <p className="text-sm text-muted-foreground">
            Sección administrativa — misma navegación lateral del producto.
          </p>
          <DevModeToggle />
        </div>

        <nav
          aria-label="Secciones de administración de IA"
          className="flex flex-wrap gap-1.5 overflow-x-auto pb-1"
        >
          {flatItems.map((item) => {
            const itemPath = item.href.split("#")[0];
            const active =
              itemPath === pathname &&
              (item.href.includes("#") ? pathname === "/lottery/admin/ai" : true);
            const isAlerts = item.href.includes("#alerts");
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs transition-colors sm:text-sm ${
                  active
                    ? "bg-primary/10 font-medium text-primary"
                    : "bg-muted/40 text-foreground/80 hover:bg-muted hover:text-foreground"
                }`}
              >
                <span>{item.label}</span>
                {isAlerts && openAlerts > 0 ? (
                  <span className="rounded bg-destructive/90 px-1.5 text-[10px] text-destructive-foreground">
                    {openAlerts}
                  </span>
                ) : null}
              </Link>
            );
          })}
        </nav>

        <div className="min-w-0">{children}</div>
      </div>
    </AppShell>
  );
}

export default function LotteryAIAdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <LotteryAIDevModeProvider>
      <LayoutInner>{children}</LayoutInner>
    </LotteryAIDevModeProvider>
  );
}
