"use client";

import type { ReactNode } from "react";

import type { QueryMeta } from "@/lib/lottery-ux-present";
import { cn } from "@/lib/utils";

function Row({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="grid grid-cols-[1fr_1.2fr] gap-2 border-b border-border/40 py-2 text-xs last:border-0">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="break-words font-medium text-foreground">{value || "—"}</dd>
    </div>
  );
}

export function QueryInfo({
  meta,
  className,
}: {
  meta: QueryMeta;
  className?: string;
}) {
  return (
    <aside
      className={cn(
        "rounded-2xl border border-border/60 bg-card/90 p-4 shadow-sm",
        className,
      )}
      data-testid="query-info"
    >
      <h3 className="text-sm font-semibold">Contexto de la consulta</h3>
      <dl className="mt-2">
        <Row label="Consulta original" value={meta.query || "—"} />
        <Row label="Sujetos" value={meta.subjects.join(" · ") || "—"} />
        <Row label="Tipo de investigación" value={meta.investigationType} />
        <Row
          label="Filtros activos"
          value={meta.activeFilters.length ? meta.activeFilters.join(" · ") : "Ninguno"}
        />
        <Row label="Cantidad de registros" value={String(meta.recordCount)} />
        <Row label="Workspace activo" value={meta.workspace} />
        <Row label="Proveedor IA" value={meta.provider} />
        <Row label="Modelo utilizado" value={meta.model} />
        <Row
          label="Tiempo SQL"
          value={meta.sqlMs != null ? `${Math.round(meta.sqlMs)} ms` : null}
        />
        <Row
          label="Tiempo IA"
          value={meta.aiMs != null ? `${Math.round(meta.aiMs)} ms` : null}
        />
        <Row
          label="Latencia total"
          value={meta.totalMs != null ? `${Math.round(meta.totalMs)} ms` : null}
        />
        <Row label="Prompt Runtime" value={meta.promptRuntime} />
        <Row label="Versión Prompt Studio" value={meta.promptStudioVersion} />
        <Row label="Hash Prompt" value={meta.promptHash} />
      </dl>
    </aside>
  );
}
