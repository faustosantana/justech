"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { LotteryAIDevModeProvider, useLotteryAIDevMode } from "@/components/lottery/ai-admin-dev-mode";
import { apiClient } from "@/lib/api";
import { getAccessToken, getUserRole } from "@/lib/auth";
import { canAccessLotteryAdmin, isLotteryClientRole } from "@/lib/lottery";

const NAV_GROUPS = [
  {
    label: "RESUMEN",
    items: [
      { label: "Dashboard", href: "/lottery/admin/ai" },
      { label: "Alertas", href: "/lottery/admin/ai#alerts" },
    ],
  },
  {
    label: "CONFIGURACIÓN",
    items: [
      { label: "Agente", href: "/lottery/admin/ai/agent" },
      { label: "Prompts", href: "/lottery/admin/ai/prompts" },
      { label: "Modelos", href: "/lottery/admin/ai/models" },
      { label: "Memoria", href: "/lottery/admin/ai/memory" },
      { label: "Tools", href: "/lottery/admin/ai/tools" },
      { label: "Paquetes", href: "/lottery/admin/ai/analysis-packs" },
      { label: "Loterías predeterminadas", href: "/lottery/admin/ai/defaults" },
      { label: "Seguridad", href: "/lottery/admin/ai/safety" },
    ],
  },
  {
    label: "PRUEBAS",
    items: [
      { label: "Playground", href: "/lottery/admin/ai/playground" },
      { label: "Benchmarks", href: "/lottery/admin/ai/benchmarks" },
    ],
  },
  {
    label: "OPERACIÓN",
    items: [
      { label: "Sesiones", href: "/lottery/admin/ai/sessions" },
      { label: "Versiones", href: "/lottery/admin/ai/versions" },
      { label: "Auditoría", href: "/lottery/admin/ai/audit" },
      { label: "Relaciones numéricas", href: "/lottery/admin/control-center/motor/relaciones" },
      { label: "Lottery IA", href: "/lottery" },
    ],
  },
];

function DevModeToggle() {
  const { developerMode, setDeveloperMode } = useLotteryAIDevMode();
  const [busy, setBusy] = useState(false);

  const toggle = async () => {
    const next = !developerMode;
    if (next && !window.confirm("¿Activar Modo desarrollador? Se mostrarán UUID, JSON y nombres internos. Quedará auditado.")) {
      return;
    }
    setBusy(true);
    try {
      await apiClient.postLotteryAIDeveloperMode(next);
      setDeveloperMode(next);
    } catch {
      // Still allow local toggle if audit endpoint fails (offline)
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
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-muted-foreground">Verificando acceso…</p>
      </div>
    );
  }

  if (denied) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-destructive">Acceso denegado</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-border/60 bg-background px-6 py-3">
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-base font-semibold tracking-tight">
            Centro de Administración de Lottery IA
          </h1>
          <div className="flex items-center gap-4 text-sm">
            <DevModeToggle />
            <Link href="/lottery" className="text-primary underline">
              Inicio
            </Link>
            <Link href="/lottery/admin/lotteries" className="text-primary underline">
              Loterías
            </Link>
            <Link href="/lottery/admin/sync" className="text-primary underline">
              Sync
            </Link>
            <Link href="/lottery/admin/scheduler" className="text-primary underline">
              Scheduler
            </Link>
          </div>
        </div>
      </header>
      <div className="flex flex-1 overflow-hidden">
        <aside className="w-52 shrink-0 overflow-y-auto border-r border-border/60 bg-muted/20 px-3 py-4">
          {NAV_GROUPS.map((group) => (
            <div key={group.label} className="mb-5">
              <p className="mb-1.5 px-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                {group.label}
              </p>
              {group.items.map((item) => {
                const itemPath = item.href.split("#")[0];
                const active =
                  itemPath === pathname && (item.href.includes("#") ? pathname === "/lottery/admin/ai" : true);
                const isAlerts = item.href.includes("#alerts");
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center justify-between rounded px-2 py-1.5 text-sm transition-colors ${
                      active
                        ? "bg-primary/10 font-medium text-primary"
                        : "text-foreground/80 hover:bg-muted hover:text-foreground"
                    }`}
                  >
                    <span>{item.label}</span>
                    {isAlerts && openAlerts > 0 ? (
                      <span className="rounded-full bg-destructive/90 px-1.5 text-[10px] text-destructive-foreground">
                        {openAlerts}
                      </span>
                    ) : null}
                  </Link>
                );
              })}
            </div>
          ))}
        </aside>
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}

export default function LotteryAIAdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <LotteryAIDevModeProvider>
      <LayoutInner>{children}</LayoutInner>
    </LotteryAIDevModeProvider>
  );
}
