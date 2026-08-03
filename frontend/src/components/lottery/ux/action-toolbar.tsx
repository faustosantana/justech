"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import type { AnalysisTab } from "@/lib/lottery-ux-present";
import { cn } from "@/lib/utils";

type Props = {
  activeTab: AnalysisTab;
  onTab: (tab: AnalysisTab) => void;
  onFilter: () => void;
  onSort: () => void;
  onExportCsv: () => void;
  onExportExcel: () => void;
  onCopyQuery: () => void;
  onSaveQuery: () => void;
  onShare: () => void;
  className?: string;
  status?: string | null;
};

const PRIMARY: { id: string; label: string; run: (p: Props) => void }[] = [
  { id: "table", label: "Ver tabla", run: (p) => p.onTab("resultados") },
  { id: "summary", label: "Ver resumen", run: (p) => p.onTab("resumen") },
  { id: "charts", label: "Gráficos", run: (p) => p.onTab("graficos") },
  { id: "timeline", label: "Timeline", run: (p) => p.onTab("timeline") },
];

const SECONDARY: { id: string; label: string; run: (p: Props) => void }[] = [
  { id: "filter", label: "Filtrar", run: (p) => p.onFilter() },
  { id: "sort", label: "Ordenar", run: (p) => p.onSort() },
  { id: "xlsx", label: "Exportar Excel", run: (p) => p.onExportExcel() },
  { id: "csv", label: "Exportar CSV", run: (p) => p.onExportCsv() },
  { id: "copy", label: "Copiar consulta", run: (p) => p.onCopyQuery() },
  { id: "save", label: "Guardar consulta", run: (p) => p.onSaveQuery() },
  { id: "share", label: "Compartir", run: (p) => p.onShare() },
];

export function ActionToolbar(props: Props) {
  const { className, status, activeTab } = props;
  const [moreOpen, setMoreOpen] = useState(false);
  const tabMap: Record<string, AnalysisTab> = {
    table: "resultados",
    summary: "resumen",
    charts: "graficos",
    timeline: "timeline",
  };

  const renderBtn = (a: { id: string; label: string; run: (p: Props) => void }, compact = false) => {
    const isActive = tabMap[a.id] === activeTab;
    return (
      <Button
        key={a.id}
        type="button"
        size="sm"
        variant={isActive ? "default" : "outline"}
        className={cn("h-8 text-[11px]", compact && "shrink-0")}
        onClick={() => a.run(props)}
      >
        {a.label}
      </Button>
    );
  };

  return (
    <div className={cn("space-y-2", className)} data-testid="action-toolbar">
      <div className="flex flex-wrap gap-1.5">
        {PRIMARY.map((a) => renderBtn(a, true))}
        {/* Desktop: show all secondary */}
        <div className="hidden flex-wrap gap-1.5 md:flex">
          {SECONDARY.map((a) => renderBtn(a))}
        </div>
        {/* Mobile: Más menu */}
        <div className="relative md:hidden">
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-8 text-[11px]"
            onClick={() => setMoreOpen((v) => !v)}
          >
            Más
          </Button>
          {moreOpen ? (
            <div className="absolute right-0 z-20 mt-1 w-48 rounded-xl border bg-background p-1 shadow-lg">
              {SECONDARY.map((a) => (
                <button
                  key={a.id}
                  type="button"
                  className="block w-full rounded-lg px-3 py-2 text-left text-xs hover:bg-muted"
                  onClick={() => {
                    setMoreOpen(false);
                    a.run(props);
                  }}
                >
                  {a.label}
                </button>
              ))}
            </div>
          ) : null}
        </div>
      </div>
      {status ? (
        <p className="text-[11px] text-muted-foreground" role="status">
          {status}
        </p>
      ) : null}
    </div>
  );
}
