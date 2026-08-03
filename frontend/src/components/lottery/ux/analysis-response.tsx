"use client";

import { useMemo, useState } from "react";

import { ActionToolbar } from "@/components/lottery/ux/action-toolbar";
import { ChartsView } from "@/components/lottery/ux/charts-view";
import { EmptyState } from "@/components/lottery/ux/empty-state";
import { ExportPanel, toCsv, downloadBlob } from "@/components/lottery/ux/export-panel";
import { FiltersPanel, type GridFilters } from "@/components/lottery/ux/filters-panel";
import { InsightPanel } from "@/components/lottery/ux/insight-panel";
import { QueryInfo } from "@/components/lottery/ux/query-info";
import { ResultGrid } from "@/components/lottery/ux/result-grid";
import { StatisticsCards } from "@/components/lottery/ux/statistics-cards";
import { SummaryCards } from "@/components/lottery/ux/summary-cards";
import { TimelineView } from "@/components/lottery/ux/timeline-view";
import { InteractiveContent } from "@/components/lottery/explorer/interactive-content";
import { ExplorerSmartCard } from "@/components/lottery/explorer/smart-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  mapLotteryChatResponseToAnalysisViewModel,
} from "@/lib/lottery-ux-adapter";
import type { AnalysisTab, Structured } from "@/lib/lottery-ux-present";
import { markUxShared, saveUxQuery } from "@/lib/lottery-ux-history";
import {
  downloadAuthenticatedBlob,
  fetchAuthenticatedFile,
  normalizeApiPath,
} from "@/lib/authenticated-file";
import type { ExplorerAction, NumberCard } from "@/lib/lottery-explorer";
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

export type WorkspaceUiAction =
  | { type: "filter_lottery"; lottery: string }
  | { type: "sort_recent" }
  | { type: "breakdown_positions" }
  | { type: "export_excel" }
  | { type: "next_page" }
  | { type: "custom"; text: string };

export function AnalysisResponse({
  content,
  structured,
  query,
  activeContext,
  toolTrace,
  latencyMs,
  sessionContext,
  suggestions,
  response,
  showSidePanel = true,
  onWorkspaceAction,
  onExplorerAction,
  className,
}: {
  content: string;
  structured?: Structured | null;
  query?: string;
  activeContext?: LotteryChatSendResponse["active_context"];
  toolTrace?: LotteryChatSendResponse["message"]["tool_trace"];
  latencyMs?: number | null;
  sessionContext?: Record<string, unknown> | null;
  suggestions?: string[];
  response?: LotteryChatSendResponse | null;
  showSidePanel?: boolean;
  onWorkspaceAction?: (action: WorkspaceUiAction) => void | Promise<void>;
  onExplorerAction?: (action: ExplorerAction, number?: string) => void | Promise<void>;
  className?: string;
}) {
  const presentation = useMemo(
    () =>
      mapLotteryChatResponseToAnalysisViewModel({
        response,
        content,
        structured,
        query,
        activeContext,
        toolTrace,
        latencyMs,
        sessionContext,
        suggestions,
      }),
    [
      response,
      content,
      structured,
      query,
      activeContext,
      toolTrace,
      latencyMs,
      sessionContext,
      suggestions,
    ],
  );

  const [tab, setTab] = useState<AnalysisTab>("resumen");
  const [status, setStatus] = useState<string | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [gridFilters, setGridFilters] = useState<GridFilters>({
    search: "",
    sortKey: "",
    sortDir: "asc",
  });
  const [lotteryFilter, setLotteryFilter] = useState("");

  const flash = (msg: string) => {
    setStatus(msg);
    window.setTimeout(() => setStatus(null), 2200);
  };

  const runWorkspace = async (action: WorkspaceUiAction) => {
    if (!onWorkspaceAction) {
      flash("Acción no conectada al chat");
      return;
    }
    flash("Ejecutando en workspace…");
    await onWorkspaceAction(action);
  };

  const exportCsv = () => {
    const { columns, rows, title } = presentation;
    if (!rows.length) {
      flash("No hay filas para exportar");
      return;
    }
    const blob = new Blob([toCsv(columns, rows)], { type: "text/csv;charset=utf-8" });
    downloadBlob(blob, `${title.replace(/\s+/g, "-").toLowerCase()}.csv`);
    flash("CSV descargado (desde asset actual)");
  };

  const exportExcel = async () => {
    // Prefer live workspace export endpoint
    if (onWorkspaceAction && !presentation.rawDownloadUrl) {
      await runWorkspace({ type: "export_excel" });
      return;
    }
    if (presentation.rawDownloadUrl) {
      try {
        const path = normalizeApiPath(presentation.rawDownloadUrl);
        const file = await fetchAuthenticatedFile(path);
        downloadAuthenticatedBlob(
          file.blob,
          presentation.downloadFilename || file.filename || "export.xlsx",
        );
        flash("Excel descargado");
      } catch {
        flash("No se pudo descargar el Excel (¿sesión?)");
      }
      return;
    }
    flash("Solicitando exportación al workspace…");
    await runWorkspace({ type: "export_excel" });
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
    flash("Consulta guardada (local)");
  };

  const share = async () => {
    const text = presentation.meta.query || "";
    const url = new URL(window.location.href);
    if (text) url.searchParams.set("q", text);
    try {
      await navigator.clipboard.writeText(url.toString());
      const saved = saveUxQuery(text || url.toString(), { shared: true });
      markUxShared(saved.id);
      flash("URL de compartir copiada");
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
          void runWorkspace({ type: "sort_recent" });
          setTab("resultados");
        }}
        onExportCsv={exportCsv}
        onExportExcel={() => void exportExcel()}
        onCopyQuery={() => void copyQuery()}
        onSaveQuery={saveQuery}
        onShare={() => void share()}
        status={status}
      />

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="h-8 text-[11px]"
          onClick={() => void runWorkspace({ type: "breakdown_positions" })}
        >
          Ver por posiciones
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="h-8 text-[11px]"
          onClick={() => void runWorkspace({ type: "filter_lottery", lottery: "Loteka" })}
        >
          Filtrar Loteka
        </Button>
        {presentation.workspaceActionHints.nextPage ? (
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-8 text-[11px]"
            onClick={() => void runWorkspace({ type: "next_page" })}
          >
            Ver más
          </Button>
        ) : null}
      </div>

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
              {activeContext?.catalog_snapshot && (
                <ExplorerSmartCard
                  card={activeContext.catalog_snapshot as unknown as NumberCard}
                  activeNumber={activeContext.number}
                  onAction={(a, n) => void onExplorerAction?.(a, n)}
                />
              )}
              <section className="rounded-2xl border border-border/50 bg-background/60 p-4">
                <h3 className="text-sm font-semibold">Explicación</h3>
                <div className="mt-2">
                  {onExplorerAction ? (
                    <InteractiveContent
                      content={presentation.narrative}
                      activeNumber={activeContext?.number}
                      onAction={(a, n) => void onExplorerAction(a, n)}
                    />
                  ) : (
                    <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground/90">
                      {presentation.narrative}
                    </p>
                  )}
                </div>
              </section>
              <InsightPanel items={presentation.insights} />
              {presentation.barChart.length > 0 || presentation.timeline.length > 0 ? (
                <div className="grid gap-4 lg:grid-cols-2">
                  {presentation.barChart.length > 0 ? (
                    <div>
                      <div className="mb-2 flex items-center justify-between">
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
                      <div className="mb-2 flex items-center justify-between">
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
                  Tabla completa en Resultados ({presentation.meta.recordCount} filas
                  {presentation.pagination
                    ? ` · pág. ${presentation.pagination.page}/${presentation.pagination.totalPages}`
                    : ""}
                  ). Sin Markdown técnico.
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
            <ExportPanel
              presentation={presentation}
              onStatus={flash}
              onExportExcel={() => void exportExcel()}
            />
          )}
        </div>

        {showSidePanel ? (
          <div className="space-y-3 xl:sticky xl:top-2 xl:self-start">
            <QueryInfo meta={presentation.meta} />
            {presentation.pagination ? (
              <p className="text-[11px] text-muted-foreground">
                Página {presentation.pagination.page} de {presentation.pagination.totalPages} ·{" "}
                {presentation.pagination.pageSize} / pág.
              </p>
            ) : null}
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
              ? `Filtro local: ${next.search || "—"} · orden ${next.sortKey || "—"}`
              : "Filtros locales limpios",
          );
        }}
        lotteryValue={lotteryFilter}
        onLotteryChange={setLotteryFilter}
        onApplyWorkspaceFilter={() => {
          const lot = lotteryFilter.trim() || "Loteka";
          setFiltersOpen(false);
          void runWorkspace({ type: "filter_lottery", lottery: lot });
        }}
        onApplyWorkspaceSort={() => {
          setFiltersOpen(false);
          void runWorkspace({ type: "sort_recent" });
        }}
      />

      {presentation.rawDownloadUrl ? (
        <a
          className="sr-only"
          href={presentation.rawDownloadUrl}
          data-testid="workspace-excel-download"
        >
          download
        </a>
      ) : null}
    </div>
  );
}
