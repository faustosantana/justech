"use client";

import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import {
  AlertTriangle,
  ArrowRight,
  Briefcase,
  ClipboardList,
  Database,
  FileSearch,
  FileStack,
  LineChart,
  Plus,
  Search,
  TrendingUp,
  Upload,
} from "lucide-react";

import { AssistantPromptCard } from "@/components/assistant/assistant-prompt-card";
import { Button } from "@/components/ui/button";
import type { ExecutiveDashboard, ExecutiveKpi } from "@/lib/dashboard";
import { cn } from "@/lib/utils";

const KPI_ICONS: Record<string, LucideIcon> = {
  sales_month: TrendingUp,
  receivables: Database,
  overdue_invoices: AlertTriangle,
  dgcp_active: FileSearch,
  tasks_overdue: ClipboardList,
  price_products: LineChart,
};

interface CommandCenterViewProps {
  data: ExecutiveDashboard;
  onOpenCopilot?: (message?: string) => void;
}

function formatDateEs(iso: string) {
  try {
    return new Intl.DateTimeFormat("es-DO", {
      weekday: "long",
      day: "numeric",
      month: "long",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function KpiPremium({ kpi }: { kpi: ExecutiveKpi }) {
  const Icon = KPI_ICONS[kpi.id] ?? Briefcase;
  const body = (
    <div className="cc-kpi group h-full">
      <div className="flex items-start justify-between gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Icon className="h-5 w-5" />
        </div>
        {kpi.href && (
          <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 transition group-hover:opacity-100" />
        )}
      </div>
      <p className="mt-4 text-3xl font-bold tabular-nums tracking-tight text-foreground">{kpi.value}</p>
      <p className="mt-1 text-sm font-medium text-foreground">{kpi.label}</p>
      {kpi.delta && <p className="mt-1 text-xs text-muted-foreground">{kpi.delta}</p>}
      <p className="mt-2 text-[10px] uppercase tracking-wide text-muted-foreground">Fuente: {kpi.source}</p>
    </div>
  );
  if (kpi.href) return <Link href={kpi.href}>{body}</Link>;
  return body;
}

export function CommandCenterView({ data, onOpenCopilot }: CommandCenterViewProps) {
  const today = formatDateEs(data.updated_at);
  const heroKpis = data.kpis.slice(0, 8);
  const priorityAlerts = data.alerts.slice(0, 6);

  const quickActions = [
    { href: "/prices/drafts", label: "Crear cotización", icon: ClipboardList },
    { href: "/prices", label: "Buscar producto", icon: Search },
    { href: "/odoo", label: "Consultar Odoo", icon: Database },
    { href: "/tasks", label: "Crear tarea", icon: Plus },
    { href: "/dgcp", label: "Preparar licitación", icon: FileSearch },
    { href: "/documents", label: "Subir documento", icon: Upload },
    { href: "/empresas", label: "Buscar proveedor", icon: FileStack },
  ];

  return (
    <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-6 pb-8">
      <section className="cc-hero">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm capitalize text-muted-foreground">{today}</p>
            <h1 className="mt-1 text-3xl font-bold tracking-tight text-foreground md:text-4xl">
              Buenos días, {data.user_name}
            </h1>
            <p className="mt-2 max-w-2xl text-base text-muted-foreground">
              Resumen ejecutivo de {data.company_name || data.tenant_name}. Centro de operaciones JAIOS.
            </p>
          </div>
          <Button
            type="button"
            size="lg"
            className="shrink-0"
            onClick={() => onOpenCopilot?.(data.proactive_message)}
          >
            Ver briefing del Assistant
          </Button>
        </div>
      </section>

      <AssistantPromptCard message={data.proactive_message} suggestions={data.assistant_suggestions} />

      <section>
        <div className="mb-4 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-foreground">Indicadores operativos</h2>
            <p className="text-sm text-muted-foreground">Datos consolidados en tiempo real desde Odoo, DGCP, documentos y tareas</p>
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {heroKpis.map((kpi) => (
            <KpiPremium key={kpi.id} kpi={kpi} />
          ))}
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-5">
        <section className="rounded-2xl border border-border bg-card p-5 xl:col-span-3">
          <h2 className="text-lg font-semibold">Lo que requiere atención hoy</h2>
          <p className="mt-1 text-sm text-muted-foreground">Prioridades con acción directa</p>
          <div className="mt-4 space-y-2">
            {priorityAlerts.length === 0 ? (
              <p className="rounded-xl border border-dashed border-border bg-muted/30 p-6 text-center text-sm text-muted-foreground">
                Sin alertas críticas registradas en este momento.
              </p>
            ) : (
              priorityAlerts.map((alert) => (
                <div key={alert.id} className="cc-priority-item">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-foreground">{alert.title}</p>
                    <p className="text-xs text-muted-foreground">Fuente: {alert.source}</p>
                  </div>
                  <Button size="sm" variant="outline" asChild>
                    <Link href={alert.href}>Atender</Link>
                  </Button>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="rounded-2xl border border-border bg-card p-5 xl:col-span-2">
          <h2 className="text-lg font-semibold">Acciones rápidas</h2>
          <div className="mt-4 grid gap-2">
            {quickActions.map(({ href, label, icon: Icon }) => (
              <Button key={href} variant="outline" className="h-11 justify-start" asChild>
                <Link href={href}>
                  <Icon className="mr-2 h-4 w-4 text-primary" />
                  {label}
                </Link>
              </Button>
            ))}
          </div>
        </section>
      </div>

      <section className="rounded-2xl border border-border bg-card p-5">
        <h2 className="text-lg font-semibold">Actividad reciente</h2>
        <div className="mt-4 space-y-4">
          {data.activity.length === 0 ? (
            <p className="text-sm text-muted-foreground">Sin actividad reciente en el timeline operativo.</p>
          ) : (
            data.activity.map((item, idx) => (
              <div key={item.id} className="cc-timeline-item">
                <div className="absolute left-0 top-1 flex h-6 w-6 items-center justify-center rounded-full border border-primary/30 bg-primary/10 text-[10px] font-bold text-primary">
                  {idx + 1}
                </div>
                <div className="rounded-xl border border-border bg-background/80 px-4 py-3">
                  {item.href ? (
                    <Link href={item.href} className="font-medium hover:text-primary">
                      {item.title}
                    </Link>
                  ) : (
                    <p className="font-medium">{item.title}</p>
                  )}
                  <p className="text-sm text-muted-foreground">{item.subtitle}</p>
                </div>
              </div>
            ))
          )}
        </div>
      </section>

      <section className="rounded-2xl border border-border bg-card p-5">
        <h2 className="text-lg font-semibold">Estado de módulos</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {data.modules.map((mod) => (
            <Link
              key={mod.id}
              href={mod.href}
              className="rounded-xl border border-border p-4 transition hover:border-primary/25 hover:shadow-sm"
            >
              <div className="flex items-center justify-between gap-2">
                <h3 className="font-semibold">{mod.label}</h3>
                <span
                  className={cn(
                    "rounded-full px-2 py-0.5 text-[10px] font-medium",
                    mod.status.toLowerCase().includes("no conectado")
                      ? "bg-warning/10 text-warning"
                      : "bg-success/10 text-success",
                  )}
                >
                  {mod.status}
                </span>
              </div>
              <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                {mod.metrics.map((m) => (
                  <li key={m}>{m}</li>
                ))}
              </ul>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
