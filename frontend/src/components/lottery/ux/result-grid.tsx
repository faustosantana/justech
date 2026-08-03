"use client";

import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/lottery/ux/empty-state";
import { cn } from "@/lib/utils";

const PAGE_SIZES = [10, 25, 50, 100];
const ROW_H = 36;
const VIEWPORT_ROWS = 12;

export function ResultGrid({
  columns,
  rows,
  className,
  externalSearch,
  externalSortKey,
  externalSortDir,
}: {
  columns: string[];
  rows: Record<string, unknown>[];
  className?: string;
  externalSearch?: string;
  externalSortKey?: string;
  externalSortDir?: "asc" | "desc";
}) {
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const effectiveSearch = externalSearch ?? search;
  const effectiveSortKey = externalSortKey || sortKey;
  const effectiveSortDir = externalSortDir || sortDir;
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(25);
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [filterCol, setFilterCol] = useState<string>("");
  const [filterVal, setFilterVal] = useState("");
  const [scrollTop, setScrollTop] = useState(0);
  const [copied, setCopied] = useState<string | null>(null);

  const visibleCols = useMemo(
    () => columns.filter((c) => !hidden.has(c)),
    [columns, hidden],
  );

  const filtered = useMemo(() => {
    const q = effectiveSearch.trim().toLowerCase();
    const fv = filterVal.trim().toLowerCase();
    return rows.filter((r) => {
      if (filterCol && fv && !String(r[filterCol] ?? "").toLowerCase().includes(fv)) {
        return false;
      }
      if (!q) return true;
      return visibleCols.some((c) => String(r[c] ?? "").toLowerCase().includes(q));
    });
  }, [rows, effectiveSearch, filterCol, filterVal, visibleCols]);

  const sorted = useMemo(() => {
    if (!effectiveSortKey) return filtered;
    const copy = [...filtered];
    copy.sort((a, b) => {
      const av = String(a[effectiveSortKey] ?? "");
      const bv = String(b[effectiveSortKey] ?? "");
      const an = Number(av);
      const bn = Number(bv);
      let cmp = 0;
      if (Number.isFinite(an) && Number.isFinite(bn) && av.trim() !== "" && bv.trim() !== "") {
        cmp = an - bn;
      } else {
        cmp = av.localeCompare(bv, "es", { numeric: true });
      }
      return effectiveSortDir === "asc" ? cmp : -cmp;
    });
    return copy;
  }, [filtered, effectiveSortKey, effectiveSortDir]);

  const pageCount = Math.max(1, Math.ceil(sorted.length / pageSize));
  const safePage = Math.min(page, pageCount - 1);
  const pageRows = sorted.slice(safePage * pageSize, safePage * pageSize + pageSize);

  // Window virtualization within the current page for large page sizes
  const useVirtual = pageRows.length > VIEWPORT_ROWS;
  const start = useVirtual ? Math.max(0, Math.floor(scrollTop / ROW_H) - 2) : 0;
  const end = useVirtual
    ? Math.min(pageRows.length, start + VIEWPORT_ROWS + 4)
    : pageRows.length;
  const windowRows = pageRows.slice(start, end);
  const topPad = start * ROW_H;
  const bottomPad = (pageRows.length - end) * ROW_H;

  const toggleSort = (col: string) => {
    if (sortKey === col) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(col);
      setSortDir("asc");
    }
  };

  const copyRow = async (row: Record<string, unknown>, idx: number) => {
    const text = visibleCols.map((c) => String(row[c] ?? "")).join("\t");
    try {
      await navigator.clipboard.writeText(text);
      setCopied(`row-${idx}`);
      setTimeout(() => setCopied(null), 1200);
    } catch {
      /* ignore */
    }
  };

  if (!columns.length || !rows.length) {
    return (
      <EmptyState
        title="Sin filas para explorar"
        body="La tabla aparece cuando la consulta devuelve registros estructurados."
      />
    );
  }

  return (
    <div className={cn("space-y-3", className)} data-testid="result-grid">
      <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
        <Input
          value={effectiveSearch}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(0);
          }}
          placeholder="Buscar en la tabla…"
          className="max-w-sm"
          aria-label="Buscar en resultados"
        />
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <select
            className="h-9 rounded-md border bg-background px-2"
            value={filterCol}
            onChange={(e) => {
              setFilterCol(e.target.value);
              setPage(0);
            }}
            aria-label="Columna de filtro"
          >
            <option value="">Filtrar por columna</option>
            {columns.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <Input
            value={filterVal}
            disabled={!filterCol}
            onChange={(e) => {
              setFilterVal(e.target.value);
              setPage(0);
            }}
            placeholder="Valor filtro"
            className="h-9 max-w-[10rem]"
          />
          <select
            className="h-9 rounded-md border bg-background px-2"
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setPage(0);
            }}
            aria-label="Filas por página"
          >
            {PAGE_SIZES.map((n) => (
              <option key={n} value={n}>
                {n} / pág.
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {columns.map((c) => {
          const on = !hidden.has(c);
          return (
            <button
              key={c}
              type="button"
              className={cn(
                "rounded-full border px-2.5 py-0.5 text-[11px] transition",
                on
                  ? "border-primary/30 bg-primary/10 text-foreground"
                  : "border-border bg-muted/40 text-muted-foreground line-through",
              )}
              onClick={() =>
                setHidden((prev) => {
                  const next = new Set(prev);
                  if (next.has(c)) next.delete(c);
                  else next.add(c);
                  return next;
                })
              }
            >
              {c}
            </button>
          );
        })}
      </div>

      <div className="overflow-hidden rounded-2xl border border-border/60">
        <div
          className="max-h-[min(28rem,60vh)] overflow-auto"
          onScroll={(e) => setScrollTop(e.currentTarget.scrollTop)}
        >
          <table
            className="w-full min-w-[36rem] border-collapse text-sm md:min-w-[640px]"
            data-testid="workspace-result-table"
          >
            <thead className="sticky top-0 z-[1] bg-muted/95 backdrop-blur">
              <tr>
                <th className="w-10 px-2 py-2 text-left text-[11px] font-medium text-muted-foreground">
                  #
                </th>
                {visibleCols.map((c) => (
                  <th key={c} className="px-2 py-2 text-left">
                    <button
                      type="button"
                      className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground hover:text-foreground"
                      onClick={() => toggleSort(c)}
                    >
                      {c}
                      {effectiveSortKey === c
                        ? effectiveSortDir === "asc"
                          ? " ↑"
                          : " ↓"
                        : ""}
                    </button>
                  </th>
                ))}
                <th className="px-2 py-2 text-[11px] font-medium text-muted-foreground">
                  Copiar
                </th>
              </tr>
            </thead>
            <tbody>
              {useVirtual && topPad > 0 ? (
                <tr aria-hidden>
                  <td colSpan={visibleCols.length + 2} style={{ height: topPad }} />
                </tr>
              ) : null}
              {windowRows.map((row, i) => {
                const abs = start + i;
                const globalIdx = safePage * pageSize + abs;
                return (
                  <tr
                    key={globalIdx}
                    className="border-t border-border/50 hover:bg-muted/30"
                    style={useVirtual ? { height: ROW_H } : undefined}
                  >
                    <td className="px-2 py-1.5 text-xs tabular-nums text-muted-foreground">
                      {globalIdx + 1}
                    </td>
                    {visibleCols.map((c) => (
                      <td
                        key={c}
                        className="max-w-[12rem] truncate px-2 py-1.5 font-mono text-xs"
                        title={String(row[c] ?? "")}
                      >
                        {String(row[c] ?? "")}
                      </td>
                    ))}
                    <td className="px-2 py-1.5">
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        className="h-7 px-2 text-[11px]"
                        onClick={() => void copyRow(row, globalIdx)}
                      >
                        {copied === `row-${globalIdx}` ? "OK" : "Copiar"}
                      </Button>
                    </td>
                  </tr>
                );
              })}
              {useVirtual && bottomPad > 0 ? (
                <tr aria-hidden>
                  <td colSpan={visibleCols.length + 2} style={{ height: bottomPad }} />
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        <p>
          {sorted.length} fila(s) · página {safePage + 1}/{pageCount}
        </p>
        <div className="flex gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={safePage <= 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            Anterior
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={safePage >= pageCount - 1}
            onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
          >
            Siguiente
          </Button>
        </div>
      </div>
    </div>
  );
}
