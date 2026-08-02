"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export type GridFilters = {
  search: string;
  sortKey: string;
  sortDir: "asc" | "desc";
};

export function FiltersPanel({
  open,
  onClose,
  columns,
  filters,
  onChange,
  lotteryValue,
  onLotteryChange,
  onApplyWorkspaceFilter,
  onApplyWorkspaceSort,
  className,
}: {
  open: boolean;
  onClose: () => void;
  columns: string[];
  filters: GridFilters;
  onChange: (next: GridFilters) => void;
  lotteryValue?: string;
  onLotteryChange?: (v: string) => void;
  onApplyWorkspaceFilter?: () => void;
  onApplyWorkspaceSort?: () => void;
  className?: string;
}) {
  if (!open) return null;

  return (
    <div
      className={cn(
        "fixed inset-y-0 right-0 z-40 w-full max-w-sm border-l border-border bg-background p-4 shadow-xl",
        className,
      )}
      data-testid="filters-panel"
      role="dialog"
      aria-label="Panel de filtros"
    >
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">Filtrar y ordenar</h3>
        <Button type="button" size="sm" variant="ghost" onClick={onClose}>
          Cerrar
        </Button>
      </div>
      <div className="mt-4 space-y-3">
        <label className="block space-y-1 text-xs">
          <span className="text-muted-foreground">Lotería (workspace)</span>
          <Input
            value={lotteryValue || ""}
            onChange={(e) => onLotteryChange?.(e.target.value)}
            placeholder="Ej. Loteka"
          />
        </label>
        <Button
          type="button"
          className="w-full"
          onClick={() => onApplyWorkspaceFilter?.()}
        >
          Aplicar filtro en workspace
        </Button>
        <Button
          type="button"
          className="w-full"
          variant="secondary"
          onClick={() => onApplyWorkspaceSort?.()}
        >
          Ordenar por fecha más reciente
        </Button>
        <hr className="border-border/60" />
        <label className="block space-y-1 text-xs">
          <span className="text-muted-foreground">Búsqueda local (página actual)</span>
          <Input
            value={filters.search}
            onChange={(e) => onChange({ ...filters, search: e.target.value })}
            placeholder="Texto a buscar…"
          />
        </label>
        <label className="block space-y-1 text-xs">
          <span className="text-muted-foreground">Ordenar columnas locales</span>
          <select
            className="h-9 w-full rounded-md border bg-background px-2"
            value={filters.sortKey}
            onChange={(e) => onChange({ ...filters, sortKey: e.target.value })}
          >
            <option value="">Sin orden</option>
            {columns.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <label className="block space-y-1 text-xs">
          <span className="text-muted-foreground">Dirección</span>
          <select
            className="h-9 w-full rounded-md border bg-background px-2"
            value={filters.sortDir}
            onChange={(e) =>
              onChange({ ...filters, sortDir: e.target.value as "asc" | "desc" })
            }
          >
            <option value="asc">Ascendente</option>
            <option value="desc">Descendente</option>
          </select>
        </label>
        <Button
          type="button"
          className="w-full"
          variant="ghost"
          onClick={() => {
            onChange({ search: "", sortKey: "", sortDir: "asc" });
            onLotteryChange?.("");
            onClose();
          }}
        >
          Limpiar filtros locales
        </Button>
      </div>
    </div>
  );
}
