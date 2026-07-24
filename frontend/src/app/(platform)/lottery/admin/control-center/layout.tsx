"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
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

export default function ControlCenterLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  const [denied, setDenied] = useState(false);

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

  if (!ready || denied) {
    return (
      <AppShell>
        <div className="p-6 text-sm text-muted-foreground">Verificando acceso…</div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="mx-auto flex max-w-7xl flex-col gap-4 p-4 md:flex-row md:p-6">
        <aside className="w-full shrink-0 md:w-56">
          <Link href="/lottery/admin/control-center" className="mb-3 block text-lg font-semibold">
            Lottery IA · Inteligencia
          </Link>
          <nav className="space-y-4 text-sm">
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
                          className={`block rounded px-2 py-1 ${
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
        </aside>
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </AppShell>
  );
}
