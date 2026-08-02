"use client";

import type { AnalysisPresentation, ChartDatum } from "@/lib/lottery-ux-present";
import { EmptyState } from "@/components/lottery/ux/empty-state";
import { cn } from "@/lib/utils";

function BarChart({ title, items }: { title: string; items: ChartDatum[] }) {
  if (!items.length) return null;
  const max = Math.max(1, ...items.map((i) => i.value));
  return (
    <div className="rounded-2xl border border-border/60 bg-card/80 p-4">
      <h4 className="text-sm font-semibold">{title}</h4>
      <div className="mt-3 space-y-2" role="img" aria-label={title}>
        {items.map((item) => (
          <div
            key={item.label}
            className="grid grid-cols-[minmax(4rem,7rem)_1fr_3rem] items-center gap-2 text-xs"
          >
            <span className="truncate text-muted-foreground" title={item.label}>
              {item.label}
            </span>
            <div className="h-2.5 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary/80 transition-all"
                style={{ width: `${Math.max(item.value ? 4 : 0, (100 * item.value) / max)}%` }}
              />
            </div>
            <span className="text-right tabular-nums font-medium">{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function PieChart({ title, items }: { title: string; items: ChartDatum[] }) {
  if (!items.length) return null;
  const total = items.reduce((a, b) => a + b.value, 0) || 1;
  const colors = [
    "hsl(var(--primary))",
    "hsl(217 70% 60%)",
    "hsl(199 80% 45%)",
    "hsl(160 50% 40%)",
    "hsl(35 85% 50%)",
    "hsl(280 40% 55%)",
  ];
  let acc = 0;
  const segments = items.map((item, i) => {
    const start = (acc / total) * 360;
    acc += item.value;
    const end = (acc / total) * 360;
    return { ...item, start, end, color: colors[i % colors.length] };
  });
  const gradient = segments
    .map((s) => `${s.color} ${s.start}deg ${s.end}deg`)
    .join(", ");

  return (
    <div className="rounded-2xl border border-border/60 bg-card/80 p-4">
      <h4 className="text-sm font-semibold">{title}</h4>
      <div className="mt-4 flex flex-col items-center gap-4 sm:flex-row">
        <div
          className="h-36 w-36 shrink-0 rounded-full"
          style={{ background: `conic-gradient(${gradient})` }}
          role="img"
          aria-label={title}
        />
        <ul className="w-full space-y-1.5 text-xs">
          {segments.map((s) => (
            <li key={s.label} className="flex items-center justify-between gap-2">
              <span className="flex items-center gap-2 truncate">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: s.color }} />
                {s.label}
              </span>
              <span className="tabular-nums text-muted-foreground">
                {s.value} · {Math.round((100 * s.value) / total)}%
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function Heatmap({
  cells,
}: {
  cells: AnalysisPresentation["heatmap"];
}) {
  if (!cells.length) return null;
  const rows = Array.from(new Set(cells.map((c) => c.row))).slice(0, 8);
  const cols = Array.from(new Set(cells.map((c) => c.col))).slice(0, 6);
  const max = Math.max(1, ...cells.map((c) => c.value));
  const lookup = new Map(cells.map((c) => [`${c.row}|||${c.col}`, c.value]));

  return (
    <div className="overflow-x-auto rounded-2xl border border-border/60 bg-card/80 p-4">
      <h4 className="text-sm font-semibold">Heatmap lotería × posición</h4>
      <table className="mt-3 min-w-full border-separate border-spacing-1 text-xs">
        <thead>
          <tr>
            <th className="p-1 text-left font-medium text-muted-foreground" />
            {cols.map((c) => (
              <th key={c} className="p-1 text-center font-medium text-muted-foreground">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r}>
              <td className="max-w-[8rem] truncate p-1 text-muted-foreground" title={r}>
                {r}
              </td>
              {cols.map((c) => {
                const v = lookup.get(`${r}|||${c}`) || 0;
                const alpha = v ? 0.15 + (0.75 * v) / max : 0.04;
                return (
                  <td
                    key={c}
                    className="rounded-md p-2 text-center tabular-nums"
                    style={{ background: `hsl(var(--primary) / ${alpha})` }}
                    title={`${r} · ${c}: ${v}`}
                  >
                    {v || ""}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Ranking({ items }: { items: ChartDatum[] }) {
  if (!items.length) return null;
  return (
    <div className="rounded-2xl border border-border/60 bg-card/80 p-4">
      <h4 className="text-sm font-semibold">Ranking</h4>
      <ol className="mt-3 space-y-2">
        {items.slice(0, 10).map((item, i) => (
          <li
            key={item.label}
            className="flex items-center justify-between gap-2 rounded-xl bg-muted/25 px-3 py-2 text-sm"
          >
            <span className="flex items-center gap-2">
              <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-[11px] font-semibold text-primary">
                {i + 1}
              </span>
              {item.label}
            </span>
            <span className="tabular-nums font-medium">{item.value}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

export function ChartsView({
  presentation,
  className,
}: {
  presentation: AnalysisPresentation;
  className?: string;
}) {
  const { barChart, pieChart, ranking, heatmap, yearly } = presentation;
  const hasAny =
    barChart.length || pieChart.length || ranking.length || heatmap.length || yearly.length;

  if (!hasAny) {
    return (
      <EmptyState
        title="Sin datos suficientes para gráficos"
        body="Cuando haya más registros, aquí aparecerán barras, pastel, ranking y heatmap."
      />
    );
  }

  return (
    <div className={cn("grid gap-4 lg:grid-cols-2", className)} data-testid="charts-view">
      <BarChart title="Distribución" items={barChart} />
      <PieChart title="Participación" items={pieChart} />
      <BarChart title="Distribución temporal (años)" items={yearly} />
      <Ranking items={ranking} />
      <div className="lg:col-span-2">
        <Heatmap cells={heatmap} />
      </div>
    </div>
  );
}
