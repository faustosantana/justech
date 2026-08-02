"use client";

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

const ACTIONS: { id: string; label: string; run: (p: Props) => void }[] = [
  { id: "table", label: "Ver tabla", run: (p) => p.onTab("resultados") },
  { id: "summary", label: "Ver resumen", run: (p) => p.onTab("resumen") },
  { id: "charts", label: "Gráficos", run: (p) => p.onTab("graficos") },
  { id: "timeline", label: "Timeline", run: (p) => p.onTab("timeline") },
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
  return (
    <div className={cn("space-y-2", className)} data-testid="action-toolbar">
      <div className="flex flex-wrap gap-1.5">
        {ACTIONS.map((a) => {
          const tabMap: Record<string, AnalysisTab> = {
            table: "resultados",
            summary: "resumen",
            charts: "graficos",
            timeline: "timeline",
          };
          const isActive = tabMap[a.id] === activeTab;
          return (
            <Button
              key={a.id}
              type="button"
              size="sm"
              variant={isActive ? "default" : "outline"}
              className="h-8 text-[11px]"
              onClick={() => a.run(props)}
            >
              {a.label}
            </Button>
          );
        })}
      </div>
      {status ? (
        <p className="text-[11px] text-muted-foreground" role="status">
          {status}
        </p>
      ) : null}
    </div>
  );
}
