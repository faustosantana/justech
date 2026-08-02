"use client";

import type { ChartDatum, AnalysisPresentation } from "@/lib/lottery-ux-present";
import { cn } from "@/lib/utils";

function Stat({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-xl border border-border/50 bg-muted/15 px-3 py-3">
      <p className="text-[11px] text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold tabular-nums">{value}</p>
    </div>
  );
}

function topLabel(items: ChartDatum[]): string {
  return items[0] ? `${items[0].label} (${items[0].value})` : "—";
}

export function StatisticsCards({
  presentation,
  className,
}: {
  presentation: AnalysisPresentation;
  className?: string;
}) {
  const { meta, ranking, barChart, yearly, timeline } = presentation;
  return (
    <section className={cn("space-y-3", className)} data-testid="statistics-cards">
      <h3 className="text-sm font-semibold">Estadísticas</h3>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Registros" value={String(meta.recordCount)} />
        <Stat label="Sujetos" value={meta.subjects.join(" · ") || "—"} />
        <Stat label="Top ranking" value={topLabel(ranking.length ? ranking : barChart)} />
        <Stat
          label="Pico anual"
          value={yearly.length ? topLabel([...yearly].sort((a, b) => b.value - a.value)) : "—"}
        />
        <Stat label="Eventos en timeline" value={String(timeline.length)} />
        <Stat label="Tipo" value={meta.investigationType} />
        <Stat
          label="Latencia total"
          value={meta.totalMs != null ? `${Math.round(meta.totalMs)} ms` : "—"}
        />
        <Stat label="Filtros activos" value={String(meta.activeFilters.length)} />
      </div>
    </section>
  );
}
