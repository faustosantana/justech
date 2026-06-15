"use client";

import Link from "next/link";

import type { ModuleActivity, ModuleKpi, QuickAction } from "@/lib/modules/types";
import { cn } from "@/lib/utils";

export function ModuleKpiGrid({ kpis }: { kpis: ModuleKpi[] }) {
  if (!kpis.length) return null;
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5">
      {kpis.map((kpi) => {
        const tone =
          kpi.tone === "danger"
            ? "border-destructive/30 bg-destructive/5"
            : kpi.tone === "warning"
              ? "border-amber-500/30 bg-amber-500/5"
              : kpi.tone === "success"
                ? "border-emerald-500/30 bg-emerald-500/5"
                : kpi.tone === "primary"
                  ? "border-primary/30 bg-primary/5"
                  : "border-border/60 bg-card/80";
        const body = (
          <div className={cn("rounded-2xl border p-4 transition hover:shadow-sm", tone)}>
            <p className="text-2xl font-semibold tabular-nums tracking-tight">{kpi.value}</p>
            <p className="mt-1 text-xs font-medium text-muted-foreground">{kpi.label}</p>
            {kpi.delta && <p className="mt-1 text-[10px] text-muted-foreground">{kpi.delta}</p>}
          </div>
        );
        return kpi.href ? (
          <Link key={kpi.id} href={kpi.href}>
            {body}
          </Link>
        ) : (
          <div key={kpi.id}>{body}</div>
        );
      })}
    </div>
  );
}

export function ModuleQuickActions({
  actions,
  onCopilot,
}: {
  actions: QuickAction[];
  onCopilot?: (prompt: string) => void;
}) {
  if (!actions.length) return null;
  return (
    <div className="flex flex-wrap gap-2">
      {actions.map((action) => {
        const Icon = action.icon;
        if (action.onClick === "copilot" && action.copilotPrompt) {
          return (
            <button
              key={action.id}
              type="button"
              onClick={() => onCopilot?.(action.copilotPrompt!)}
              className="inline-flex items-center gap-2 rounded-xl border border-border/60 bg-card px-3 py-2 text-sm font-medium transition hover:border-primary/30 hover:bg-primary/5"
            >
              <Icon className="h-4 w-4 text-primary" />
              {action.label}
            </button>
          );
        }
        if (!action.href) return null;
        return (
          <Link
            key={action.id}
            href={action.href}
            className="inline-flex items-center gap-2 rounded-xl border border-border/60 bg-card px-3 py-2 text-sm font-medium transition hover:border-primary/30 hover:bg-primary/5"
          >
            <Icon className="h-4 w-4 text-primary" />
            {action.label}
          </Link>
        );
      })}
    </div>
  );
}

export function ModuleActivityTimeline({
  items,
  emptyMessage = "Sin actividad reciente.",
}: {
  items: ModuleActivity[];
  emptyMessage?: string;
}) {
  if (!items.length) {
    return <p className="text-sm text-muted-foreground">{emptyMessage}</p>;
  }
  return (
    <ul className="space-y-3">
      {items.map((item) => {
        const row = (
          <div className="border-b border-border/40 pb-3 last:border-0">
            <p className="text-sm font-medium">{item.title}</p>
            {item.subtitle && <p className="text-xs text-muted-foreground">{item.subtitle}</p>}
          </div>
        );
        return (
          <li key={item.id}>
            {item.href ? (
              <Link href={item.href} className="block transition hover:text-primary">
                {row}
              </Link>
            ) : (
              row
            )}
          </li>
        );
      })}
    </ul>
  );
}

export function ModuleDashboard({
  title,
  subtitle,
  kpis,
  actions,
  activity,
  alerts,
  onCopilot,
  loading,
}: {
  title: string;
  subtitle?: string;
  kpis: ModuleKpi[];
  actions: QuickAction[];
  activity: ModuleActivity[];
  alerts?: ModuleActivity[];
  onCopilot?: (prompt: string) => void;
  loading?: boolean;
}) {
  if (loading) {
    return (
      <div className="mx-auto max-w-[1600px] space-y-6 animate-pulse">
        <div className="h-8 w-48 rounded-lg bg-muted" />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 rounded-2xl bg-muted" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1600px] space-y-8">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>}
      </header>

      <section className="space-y-3">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Indicadores</h2>
        <ModuleKpiGrid kpis={kpis} />
      </section>

      {actions.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Acciones rápidas</h2>
          <ModuleQuickActions actions={actions} onCopilot={onCopilot} />
        </section>
      )}

      {alerts && alerts.length > 0 && (
        <section className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-4">
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-amber-800">Alertas</h2>
          <ModuleActivityTimeline items={alerts} />
        </section>
      )}

      <section className="rounded-2xl border border-border/60 bg-card/80 p-5">
        <h2 className="mb-4 text-xs font-semibold uppercase tracking-widest text-muted-foreground">Actividad reciente</h2>
        <ModuleActivityTimeline
          items={activity}
          emptyMessage="No hay actividad reciente disponible para este módulo."
        />
      </section>
    </div>
  );
}

export function ModuleViewSwitcher({
  appId,
  sectionId,
  active,
  views,
}: {
  appId: string;
  sectionId: string;
  active: string;
  views: { id: string; label: string }[];
}) {
  return (
    <div className="flex flex-wrap gap-1 rounded-xl border border-border/60 bg-muted/30 p-1">
      {views.map((v) => (
        <Link
          key={v.id}
          href={
            v.id === "dashboard"
              ? `/apps/${appId}`
              : `/apps/${appId}/${sectionId}${v.id !== "list" ? `?view=${v.id}` : ""}`
          }
          className={cn(
            "rounded-lg px-3 py-1.5 text-xs font-medium transition",
            active === v.id ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
          )}
        >
          {v.label}
        </Link>
      ))}
    </div>
  );
}

export function ModuleSectionHeader({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-0.5 text-sm text-muted-foreground">{description}</p>}
      </div>
      {children}
    </div>
  );
}

export function ModuleEmptyState({ title, description }: { title: string; description?: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-border/60 bg-muted/20 px-6 py-16 text-center">
      <p className="text-sm font-medium">{title}</p>
      {description && <p className="mt-1 max-w-md text-sm text-muted-foreground">{description}</p>}
    </div>
  );
}
