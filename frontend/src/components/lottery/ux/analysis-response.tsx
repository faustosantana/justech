"use client";

import { useMemo, useState } from "react";

import { ActionToolbar } from "@/components/lottery/ux/action-toolbar";
import { ChartsView } from "@/components/lottery/ux/charts-view";
import { EmptyState } from "@/components/lottery/ux/empty-state";
import { ExportPanel, toCsv, toExcelXml, downloadBlob } from "@/components/lottery/ux/export-panel";
import { FiltersPanel, type GridFilters } from "@/components/lottery/ux/filters-panel";
import { InsightPanel } from "@/components/lottery/ux/insight-panel";
import { QueryInfo } from "@/components/lottery/ux/query-info";
import { ResultGrid } from "@/components/lottery/ux/result-grid";
import { StatisticsCards } from "@/components/lottery/ux/statistics-cards";
import { SummaryCards } from "@/components/lottery/ux/summary-cards";
import { TimelineView } from "@/components/lottery/ux/timeline-view";
import { Badge } from "@/components/ui/badge";
import {
  buildAnalysisPresentation,
  type AnalysisTab,
  type Structured,
} from "@/lib/lottery-ux-present";
import { markUxShared, saveUxQuery } from "@/lib/lottery-ux-history";
import type { LotteryChatSendResponse } from "@/lib/lottery";
import { cn } from "@/lib/utils";

const TABS: { id: AnalysisTab; label: string }[] = [
  { id: "resumen", label: "Resumen" },
  { id: "resultados", label: "Resultados" },
  { id: "graficos", label: "Gráficos" },
  { id: "estadisticas", label: "Estadísticas" },
  { id: "timeline", label: "Timeline" },
  { id: "exportar", label: "Exportar" },
];

export function AnalysisResponse({
  content,
  structured,
  query,
  activeContext,
  toolTrace,
  latencyMs,
  sessionContext,
  showSidePanel = true,
  className,
}: {
  content: string;
  structured?: Structured | null;
  query?: string;
  activeContext?: LotteryChatSendResponse["active_context"];
  toolTrace?: LotteryChatSendResponse["message"]["tool_trace"];
  latencyMs?: number | null;
  sessionContext?: Record<string, unknown> | null;
  showSidePanel?: boolean;
  className?: string;
}) {
  const presentation = useMemo(
    () =>
      buildAnalysisPresentation({
        content,
        structured,
        query,
        activeContext,
        toolTrace,
        latencyMs,
        sessionContext,
      }),
    [content, structured, query, activeContext, toolTrace, latencyMs, sessionContext],
  );

  const [tab, setTab] = useState<AnalysisTab>("resumen");
  const [status, setStatus] = useState<string | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [gridFilters, setGridFilters] = useState<GridFilters>({
    search: "",
    sortKey: "",
    sortDir: "asc",
  });

  const flash = (msg: string) => {
    setStatus(msg);
    window.setTimeout(() => setStatus(null), 2200);
  };

  const exportCsv = () => {
    const { columns, rows, title } = presentation;
    if (!rows.length) {
      flash("No hay filas para exportar");
      return;
    }
    const blob = new Blob([toCsv(columns, rows)], { type: "text/csv;charset=utf-8" });
    downloadBlob(blob, `${title.replace(/\s+/g, "-").toLowerCase()}.csv`);
    flash("CSV descargado");
  };

  const exportExcel = () => {
    if (presentation.downloadUrl) {
      window.open(presentation.downloadUrl, "_blank", "noopener,noreferrer");
      flash("Descarga del workspace iniciada");
      return;
    }
    const { columns, rows, title } = presentation;
    if (!rows.length) {
      flash("No hay filas para exportar");
      return;
    }
    const blob = new Blob([toExcelXml(columns, rows)], {
      type: "application/vnd.ms-excel",
    });
    downloadBlob(blob, `${title.replace(/\s+/g, "-").toLowerCase()}.xls`);
    flash("Excel descargado");
  };

  const copyQuery = async () => {
    const text = presentation.meta.query || content.slice(0, 500);
    try {
      await navigator.clipboard.writeText(text);
      flash("Consulta copiada");
    } catch {
      flash("No se pudo copiar");
    }
  };

  const saveQuery = () => {
    const text = presentation.meta.query || content.slice(0, 120);
    if (!text.trim()) {
      flash("Nada que guardar");
      return;
    }
    saveUxQuery(text, { favorite: true });
    flash("Consulta guardada en favoritas");
  };

  const share = async () => {
    const text = presentation.meta.query || "";
    const url = new URL(window.location.href);
    if (text) url.searchParams.set("q", text);
    try {
      await navigator.clipboard.writeText(url.toString());
      const saved = saveUxQuery(text || url.toString(), { shared: true });
      markUxShared(saved.id);
      flash("Enlace de compartir copiado");
    } catch {
      flash("No se pudo compartir");
    }
  };

  if (presentation.isError) {
    return (
      <div className={cn("space-y-3", className)} data-testid="analysis-response-error">
        <EmptyState
          title={
            structured?.type === "lottery_ambiguity"
              ? "Aclaración requerida"
              : structured?.type === "lottery_no_results"
                ? "Sin resultados"
                : "Aviso"
          }
          body={presentation.narrative}
        />
      </div>
    );
  }

  return (
    <div
      className={cn(
        "w-full max-w-none space-y-4 rounded-2xl border border-border/50 bg-gradient-to-b from-card via-card to-muted/20 p-3 sm:p-4",
        className,
      )}
      data-testid="analysis-response"
    >
      <header className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary" className="rounded-full">
            Lottery IA
          </Badge>
          <Badge variant="outline" className="rounded-full font-normal">
            {presentation.meta.investigationType}
          </Badge>
          {presentation.meta.recordCount > 0 ? (
            <Badge variant="outline" className="rounded-full font-normal tabular-nums">
              {presentation.meta.recordCount} registros
            </Badge>
          ) : null}
        </div>
        <h2 className="text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
          {presentation.title}
        </h2>
      </header>

      <ActionToolbar
        activeTab={tab}
        onTab={setTab}
        onFilter={() => {
          setFiltersOpen(true);
          setTab("resultados");
        }}
        onSort={() => {
          setFiltersOpen(true);
          setTab("resultados");
        }}
        onExportCsv={exportCsv}
        onExportExcel={exportExcel}
        onCopyQuery={() => void copyQuery()}
        onSaveQuery={saveQuery}
        onShare={() => void share()}
        status={status}
      />

      <div className="flex gap-1 overflow-x-auto border-b border-border/50 pb-px">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={cn(
              "shrink-0 rounded-t-lg px-3 py-2 text-xs font-medium transition",
              tab === t.id
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:text-foreground",
            )}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div
        className={cn(
          "grid gap-4",
          showSidePanel ? "xl:grid-cols-[minmax(0,1fr)_280px]" : "",
        )}
      >
        <div className="min-w-0 space-y-4">
          {tab === "resumen" && (
            <>
              <SummaryCards items={presentation.summaryCards} />
              <section className="rounded-2xl border border-border/50 bg-background/60 p-4">
                <h3 className="text-sm font-semibold">Explicación</h3>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-foreground/90">
                  {presentation.narrative}
                </p>
              </section>
              <InsightPanel items={presentation.insights} />
              {presentation.barChart.length > 0 || presentation.timeline.length > 0 ? (
                <div className="grid gap-4 lg:grid-cols-2">
                  {presentation.barChart.length > 0 ? (
                    <div className="rounded-2xl border border-border/60 bg-card/80 p-4">
                      <div className="mb-2 flex items-center justify-between gap-2">
                        <h4 className="text-sm font-semibold">Vista previa</h4>
                        <button
                          type="button"
                          className="text-xs text-primary"
                          onClick={() => setTab("graficos")}
                        >
                          Ver gráficos
                        </button>
                      </div>
                      <ChartsView
                        presentation={{
                          ...presentation,
                          pieChart: [],
                          heatmap: [],
                          ranking: [],
                          yearly: [],
                          barChart: presentation.barChart.slice(0, 6),
                        }}
                      />
                    </div>
                  ) : null}
                  {presentation.timeline.length > 0 ? (
                    <div>
                      <div className="mb-2 flex items-center justify-between gap-2">
                        <h4 className="text-sm font-semibold">Timeline reciente</h4>
                        <button
                          type="button"
                          className="text-xs text-primary"
                          onClick={() => setTab("timeline")}
                        >
                          Ver todo
                        </button>
                      </div>
                      <TimelineView items={presentation.timeline.slice(0, 6)} />
                    </div>
                  ) : null}
                </div>
              ) : null}
              {presentation.rows.length > 0 ? (
                <p className="text-xs text-muted-foreground">
                  La tabla completa está en Resultados ({presentation.rows.length} filas) — nunca
                  antes del resumen.
                </p>
              ) : null}
            </>
          )}

          {tab === "resultados" && (
            <ResultGrid
              columns={presentation.columns}
              rows={presentation.rows}
              externalSearch={gridFilters.search || undefined}
              externalSortKey={gridFilters.sortKey || undefined}
              externalSortDir={gridFilters.sortDir}
            />
          )}

          {tab === "graficos" && <ChartsView presentation={presentation} />}

          {tab === "estadisticas" && <StatisticsCards presentation={presentation} />}

          {tab === "timeline" && <TimelineView items={presentation.timeline} />}

          {tab === "exportar" && (
            <ExportPanel presentation={presentation} onStatus={flash} />
          )}
        </div>

        {showSidePanel ? (
          <div className="space-y-3 xl:sticky xl:top-2 xl:self-start">
            <QueryInfo meta={presentation.meta} />
          </div>
        ) : null}
      </div>

      <FiltersPanel
        open={filtersOpen}
        onClose={() => setFiltersOpen(false)}
        columns={presentation.columns}
        filters={gridFilters}
        onChange={(next) => {
          setGridFilters(next);
          flash(
            next.search || next.sortKey
              ? `Filtros: ${next.search || "—"} · orden ${next.sortKey || "—"}`
              : "Filtros limpios",
          );
        }}
      />

      {/* keep test id used by workspace exports */}
      {presentation.downloadUrl ? (
        <a
          className="sr-only"
          href={presentation.downloadUrl}
          data-testid="workspace-excel-download"
        >
          download
        </a>
      ) : null}
    </div>
  );
}
