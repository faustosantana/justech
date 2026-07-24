"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { getAccessToken, getUserRole } from "@/lib/auth";
import { canAccessLotteryAdmin, isLotteryClientRole } from "@/lib/lottery";

/** Nav J-10: análisis primero; tablas y auditoría después; Prompt Studio colapsado al final. */
const NAV = [
  {
    label: "Análisis",
    items: [
      { href: "/lottery/admin/control-center", label: "Inteligencia (7 destacadas)", exact: true },
      { href: "/lottery/admin/control-center/motor/historial-numero", label: "Historial del Número" },
      { href: "/lottery/admin/control-center/motor/comparador", label: "Comparador" },
    ],
  },
  {
    label: "Motor (consulta)",
    items: [
      { href: "/lottery/admin/control-center/motor/table1", label: "Tabla 1" },
      { href: "/lottery/admin/control-center/motor/table2", label: "Tabla 2" },
      { href: "/lottery/admin/control-center/motor/groups-table1", label: "Agrupaciones T1" },
      { href: "/lottery/admin/control-center/motor/groups-table2", label: "Agrupaciones T2" },
      { href: "/lottery/admin/control-center/motor/relaciones", label: "Relaciones" },
      { href: "/lottery/admin/control-center/motor/auditoria", label: "Auditoría" },
    ],
  },
  {
    label: "Avanzado",
    items: [
      { href: "/lottery/admin/control-center/motor/historico", label: "Histórico (consulta)" },
      { href: "/lottery/admin/control-center/motor/combinaciones", label: "Matriz" },
      { href: "/lottery/admin/control-center/motor/patron", label: "Patrón" },
      { href: "/lottery/admin/control-center/predicciones", label: "Predicciones" },
      { href: "/lottery/admin/control-center/prompt-studio", label: "Prompt Studio" },
    ],
  },
];

function NavLinks({
  pathname,
  onNavigate,
}: {
  pathname: string;
  onNavigate?: () => void;
}) {
  return (
    <nav className="space-y-4 text-sm" aria-label="Metodología y herramientas">
      {NAV.map((g) => (
        <div key={g.label}>
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {g.label}
          </div>
          <ul className="space-y-1">
            {g.items.map((item) => {
              const exact = "exact" in item && item.exact;
              const active = exact
                ? pathname === item.href
                : pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={onNavigate}
                    className={`block rounded px-2 py-2 min-h-11 md:min-h-0 md:py-1 ${
                      active ? "bg-primary/10 font-medium text-primary" : "hover:bg-muted"
                    }`}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}

export default function ControlCenterLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  const [denied, setDenied] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    if (!getAccessToken()) {
      router.replace("/login?session=expired");
      return;
    }
    const role = getUserRole();
    if (isLotteryClientRole(role) || !canAccessLotteryAdmin(role)) {
      setDenied(true);
      router.replace("/lottery");
      return;
    }
    setReady(true);
  }, [router]);

  useEffect(() => {
    setMobileNavOpen(false);
  }, [pathname]);

  if (!ready || denied) {
    return (
      <AppShell>
        <div className="p-6 text-sm text-muted-foreground">Verificando acceso…</div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      {/* ≤768px: un solo control Metodología; ≥769px: aside secundario persistente */}
      <div className="mx-auto flex max-w-7xl flex-col gap-4 p-4 min-[769px]:flex-row min-[769px]:p-6">
        <div className="min-[769px]:hidden">
          <div className="flex items-center justify-between gap-2">
            <Link href="/lottery/admin/control-center" className="text-lg font-semibold">
              Lottery IA · Inteligencia
            </Link>
            <Button
              type="button"
              variant="outline"
              className="min-h-11"
              aria-expanded={mobileNavOpen}
              aria-controls="cc-mobile-nav"
              onClick={() => setMobileNavOpen((v) => !v)}
            >
              {mobileNavOpen ? "Cerrar menú" : "Metodología"}
            </Button>
          </div>
          {mobileNavOpen ? (
            <div
              id="cc-mobile-nav"
              className="mt-3 max-h-[70vh] overflow-y-auto rounded-lg border bg-background p-3"
              role="dialog"
              aria-label="Navegación del Control Center"
            >
              <NavLinks pathname={pathname} onNavigate={() => setMobileNavOpen(false)} />
            </div>
          ) : null}
        </div>

        <aside className="hidden w-56 shrink-0 min-[769px]:block">
          <Link href="/lottery/admin/control-center" className="mb-3 block text-lg font-semibold">
            Lottery IA · Inteligencia
          </Link>
          <NavLinks pathname={pathname} />
        </aside>

        <main className="min-w-0 flex-1 overflow-x-hidden">{children}</main>
      </div>
    </AppShell>
  );
}
