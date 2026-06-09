"use client";

import Link from "next/link";
import {
  AlertTriangle,
  Briefcase,
  ClipboardList,
  Cloud,
  Database,
  FileSearch,
  FileStack,
  LineChart,
  Plus,
  Search,
  Upload,
} from "lucide-react";

import { AssistantPromptCard } from "@/components/assistant/assistant-prompt-card";
import { AlertCard } from "@/components/ui/alert-card";
import { Button } from "@/components/ui/button";
import { MetricCard } from "@/components/ui/metric-card";
import { SectionCard } from "@/components/ui/section-card";
import type { ExecutiveDashboard } from "@/lib/dashboard";
import { cn } from "@/lib/utils";

interface ExecutiveDashboardViewProps {
  data: ExecutiveDashboard;
}

const MODULE_ICONS: Record<string, typeof Database> = {
  odoo: Database,
  dgcp: FileSearch,
  documents: FileStack,
  tasks: ClipboardList,
  m365: Cloud,
};

function formatDateEs(iso: string) {
  try {
    return new Intl.DateTimeFormat("es-DO", {
      weekday: "long",
      day: "numeric",
      month: "long",
      year: "numeric",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function parseMetricValue(value: string): number {
  const n = Number(value.replace(/[^\d.-]/g, ""));
  return Number.isFinite(n) ? n : 0;
}

function moduleStatusClass(status: string): string {
  const s = status.toLowerCase();
  if (s.includes("conectado") && !s.includes("no")) return "text-success bg-success/10 border-success/20";
  if (s.includes("no conectado") || s.includes("offline")) return "text-warning bg-warning/10 border-warning/20";
  return "text-primary bg-primary/10 border-primary/20";
}

export function ExecutiveDashboardView({ data }: ExecutiveDashboardViewProps) {
  const today = formatDateEs(data.updated_at);
  const updatedTime = new Intl.DateTimeFormat("es-DO", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(data.updated_at));

  const highlightKpis = [...data.kpis]
    .sort((a, b) => {
      const toneScore = (t?: string) =>
        t === "danger" ? 4 : t === "warning" ? 3 : t === "primary" ? 2 : 1;
      const scoreA = toneScore(a.tone) * 100 + parseMetricValue(a.value);
      const scoreB = toneScore(b.tone) * 100 + parseMetricValue(b.value);
      return scoreB - scoreA;
    })
    .slice(0, 4);

  const odooModule = data.modules.find((m) => m.id === "odoo");
  const odooOffline = odooModule?.status.toLowerCase().includes("no conectado");
  const hasActionableAlerts = data.alerts.length > 0;
  const hasActivity = data.activity.length > 0;

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
      <header className="brand-surface-accent overflow-hidden p-6 md:p-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <span className="brand-chip">Centro de mando</span>
            <p className="text-sm capitalize text-muted-foreground">{today}</p>
            <h1 className="text-3xl font-bold tracking-tight md:text-4xl">
              Buenos días, {data.user_name}
            </h1>
            <p className="text-base text-muted-foreground md:text-lg">
              {data.company_name || data.tenant_name}
              {" · "}
              Vista consolidada de ventas, licitaciones, documentos y operaciones
            </p>
            <p className="text-xs text-muted-foreground">
              Actualizado {updatedTime} · {data.kpis.length} indicadores · {data.modules.length} módulos
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {data.modules.map((mod) => (
              <span
                key={mod.id}
                className={cn(
                  "inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-medium",
                  moduleStatusClass(mod.status),
                )}
              >
                {mod.label}: {mod.status}
              </span>
            ))}
          </div>
        </div>
      </header>

      {odooOffline && (
        <div className="brand-surface-accent flex flex-col gap-3 rounded-2xl border-warning/30 bg-warning/5 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-warning" />
            <div>
              <p className="font-semibold text-foreground">Odoo no conectado</p>
              <p className="text-sm text-muted-foreground">
                Ventas, facturas y cuentas por cobrar no se están sincronizando. Conecta Odoo para ver KPIs reales.
              </p>
            </div>
          </div>
          <Button asChild>
            <Link href="/odoo/settings">Configurar Odoo</Link>
          </Button>
        </div>
      )}

      <AssistantPromptCard
        message={data.proactive_message}
        suggestions={data.assistant_suggestions}
      />

      <SectionCard title="Prioridades de hoy" description="Indicadores con mayor impacto operativo">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {highlightKpis.map((kpi) => (
            <MetricCard
              key={kpi.id}
              label={kpi.label}
              value={kpi.value}
              source={kpi.source}
              href={kpi.href ?? undefined}
              tone={(kpi.tone as "primary" | "success" | "warning" | "danger" | "muted") ?? "primary"}
              delta={kpi.delta ?? undefined}
            />
          ))}
        </div>
      </SectionCard>

      <SectionCard title="Todos los indicadores" description="KPIs consolidados por fuente de datos">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {data.kpis.map((kpi) => (
            <MetricCard
              key={kpi.id}
              label={kpi.label}
              value={kpi.value}
              source={kpi.source}
              href={kpi.href ?? undefined}
              tone={(kpi.tone as "primary" | "success" | "warning" | "danger" | "muted") ?? "primary"}
              delta={kpi.delta ?? undefined}
            />
          ))}
        </div>
      </SectionCard>

      <div className="grid gap-6 xl:grid-cols-3">
        <SectionCard
          title="Módulos operativos"
          description="Estado y métricas por área"
          className="xl:col-span-2"
        >
          <div className="grid gap-4 md:grid-cols-2">
            {data.modules.map((mod) => {
              const Icon = MODULE_ICONS[mod.id] ?? Briefcase;
              return (
                <Link
                  key={mod.id}
                  href={mod.href}
                  className="brand-surface group rounded-xl p-4 transition hover:border-primary/30 hover:shadow-md"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary transition group-hover:bg-primary group-hover:text-primary-foreground">
                        <Icon className="h-5 w-5" />
                      </div>
                      <div>
                        <h3 className="font-semibold">{mod.label}</h3>
                        <span
                          className={cn(
                            "mt-1 inline-flex rounded-full border px-2 py-0.5 text-[10px] font-medium",
                            moduleStatusClass(mod.status),
                          )}
                        >
                          {mod.status}
                        </span>
                      </div>
                    </div>
                  </div>
                  <ul className="mt-4 space-y-1.5 text-sm text-muted-foreground">
                    {mod.metrics.map((m) => (
                      <li key={m} className="flex items-center gap-2">
                        <span className="h-1 w-1 rounded-full bg-primary/40" />
                        {m}
                      </li>
                    ))}
                  </ul>
                </Link>
              );
            })}
          </div>
        </SectionCard>

        <SectionCard title="Requieren atención" description="Alertas prioritarias">
          {!hasActionableAlerts ? (
            <div className="rounded-xl border border-dashed border-border/80 bg-muted/20 p-6 text-center">
              <p className="text-sm font-medium text-foreground">Sin alertas críticas</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Cuando haya tareas vencidas, licitaciones o documentos pendientes aparecerán aquí.
              </p>
              <Button variant="outline" size="sm" className="mt-4" asChild>
                <Link href="/work">Ir al centro de trabajo</Link>
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {data.alerts.map((alert) => (
                <AlertCard
                  key={alert.id}
                  title={alert.title}
                  source={alert.source}
                  href={alert.href}
                  priority={
                    alert.priority === "danger"
                      ? "danger"
                      : alert.priority === "warning"
                        ? "warning"
                        : "primary"
                  }
                  assignee={alert.assignee ?? undefined}
                />
              ))}
            </div>
          )}
        </SectionCard>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <SectionCard title="Actividad reciente" description="Timeline operativo">
          {!hasActivity ? (
            <div className="rounded-xl border border-dashed border-border/80 bg-muted/20 p-6 text-center">
              <p className="text-sm font-medium text-foreground">Sin actividad reciente</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Las tareas, notificaciones y movimientos del equipo se mostrarán en esta línea de tiempo.
              </p>
              <Button variant="outline" size="sm" className="mt-4" asChild>
                <Link href="/tasks">Ver tareas</Link>
              </Button>
            </div>
          ) : (
            <ul className="space-y-3">
              {data.activity.map((item) => (
                <li key={item.id} className="rounded-xl border border-border/60 bg-background/80 px-4 py-3">
                  <div className="border-l-2 border-primary/40 pl-3">
                    {item.href ? (
                      <Link href={item.href} className="font-medium hover:text-primary">
                        {item.title}
                      </Link>
                    ) : (
                      <p className="font-medium">{item.title}</p>
                    )}
                    <p className="text-sm text-muted-foreground">{item.subtitle}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </SectionCard>

        <SectionCard title="Acciones rápidas" description="Operaciones frecuentes del día">
          <div className="grid gap-2 sm:grid-cols-2">
            {[
              { href: "/tasks", label: "Crear tarea", icon: Plus },
              { href: "/search", label: "Buscar cliente", icon: Search },
              { href: "/prices", label: "Buscar precio", icon: LineChart },
              { href: "/prices/drafts", label: "Preparar cotización", icon: ClipboardList },
              { href: "/dgcp", label: "Revisar licitaciones", icon: FileSearch },
              { href: "/documents", label: "Subir documento", icon: Upload },
              { href: "/odoo", label: "Ver facturas vencidas", icon: FileStack },
            ].map(({ href, label, icon: Icon }) => (
              <Button key={href} variant="outline" className="h-11 justify-start" asChild>
                <Link href={href}>
                  <Icon className="mr-2 h-4 w-4" />
                  {label}
                </Link>
              </Button>
            ))}
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
