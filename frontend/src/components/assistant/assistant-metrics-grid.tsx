"use client";

import type { SalesReportMetric } from "@/lib/assistant-types";

interface AssistantMetricsGridProps {
  metrics: SalesReportMetric[];
  wide?: boolean;
}

export function AssistantMetricsGrid({ metrics, wide = false }: AssistantMetricsGridProps) {
  if (!metrics.length) return null;
  return (
    <div
      className={
        wide
          ? "grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5"
          : "grid grid-cols-2 gap-2"
      }
    >
      {metrics.map((metric) => (
        <div
          key={metric.label}
          className="rounded-md border border-border bg-background px-2.5 py-2"
        >
          <p className="text-[10px] text-muted-foreground">{metric.label}</p>
          <p className="mt-0.5 break-words text-sm font-medium leading-snug">{metric.value}</p>
        </div>
      ))}
    </div>
  );
}
