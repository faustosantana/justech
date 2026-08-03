"use client";

import { ExplorerNumberChip } from "@/components/lottery/explorer/number-chip";
import type { ExplorerAction, TableExplorerPayload } from "@/lib/lottery-explorer";

type Props = {
  table: TableExplorerPayload;
  highlight?: string | number | null;
  onAction?: (action: ExplorerAction, number: string) => void;
};

export function ExplorerTableView({ table, highlight, onAction }: Props) {
  const hl = highlight != null ? String(highlight) : null;
  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between">
        <p className="text-xs font-medium text-foreground">
          Explorador Tabla {table.table}
        </p>
        <p className="text-[10px] text-muted-foreground">{table.row_count} filas</p>
      </div>
      <div className="max-h-64 space-y-1 overflow-y-auto rounded-xl border border-border/50 p-1.5">
        {table.rows.map((row) => {
          const active = hl != null && String(row.number) === hl;
          return (
            <div
              key={`${table.table}-${row.number}`}
              className={`flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs ${
                active ? "bg-sky-100/80 dark:bg-sky-950/40" : "hover:bg-muted/40"
              }`}
            >
              <ExplorerNumberChip
                number={row.number}
                size="sm"
                active={active}
                onAction={onAction}
              />
              <div className="min-w-0 flex-1">
                <p className="font-medium tabular-nums">
                  Código {String(row.code).padStart(2, "0")}
                </p>
                <div className="mt-0.5 flex flex-wrap gap-1">
                  {(row.group_numbers || [])
                    .filter((g) => g !== row.number)
                    .slice(0, 8)
                    .map((g) => (
                      <ExplorerNumberChip
                        key={`${row.number}-g-${g}`}
                        number={g}
                        size="sm"
                        onAction={onAction}
                      />
                    ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
