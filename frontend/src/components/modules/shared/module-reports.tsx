"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ModuleActivityTimeline, ModuleKpiGrid } from "@/components/module/module-dashboard";
import { apiClient } from "@/lib/api";
import { loadModuleDashboard } from "@/lib/modules/dashboard-data";
import { MODULE_BY_ID } from "@/lib/modules/registry";
import type { ModuleActivity, ModuleKpi } from "@/lib/modules/types";

export function ModuleReportsSection({ moduleId }: { moduleId: string }) {
  const mod = MODULE_BY_ID[moduleId];
  const [kpis, setKpis] = useState<ModuleKpi[]>([]);
  const [activity, setActivity] = useState<ModuleActivity[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!mod) return;
    loadModuleDashboard(mod)
      .then((d) => {
        setKpis(d.kpis);
        setActivity(d.activity);
      })
      .finally(() => setLoading(false));
  }, [mod]);

  if (!mod) return null;
  if (loading) return <p className="text-sm text-muted-foreground">Cargando reportes…</p>;

  return (
    <div className="space-y-8">
      <section>
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Indicadores · {mod.label}
        </h2>
        <ModuleKpiGrid kpis={kpis} />
      </section>
      <section className="rounded-2xl border border-border/60 bg-card/80 p-5">
        <h2 className="mb-4 text-xs font-semibold uppercase tracking-widest text-muted-foreground">Actividad</h2>
        <ModuleActivityTimeline items={activity} />
      </section>
    </div>
  );
}

export function ModuleOdooConfigSection() {
  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <p className="text-sm text-muted-foreground">Integración ERP Odoo para este módulo.</p>
      <Link href="/configuracion/integraciones/odoo" className="inline-flex rounded-xl bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">
        Configurar Odoo
      </Link>
    </div>
  );
}
