"use client";

import { AssistantActionButtons } from "@/components/assistant/assistant-action-buttons";
import {
  normalizeTableRow,
  type AssistantDataTableDef,
  type QuickViewTarget,
} from "@/lib/assistant-types";
import { cn } from "@/lib/utils";

interface AssistantDataTableProps {
  table: AssistantDataTableDef;
  wide?: boolean;
  onQuickView?: (target: QuickViewTarget) => void;
  onNavigate?: () => void;
}

function CellContent({ value }: { value: string }) {
  const long = value.length > 48;
  return (
    <span
      className={cn("break-words", long && "line-clamp-2")}
      title={long ? value : undefined}
    >
      {value}
    </span>
  );
}

export function AssistantDataTable({
  table,
  wide = false,
  onQuickView,
  onNavigate,
}: AssistantDataTableProps) {
  if (!table.rows.length) return null;

  const normalized = table.rows.map(normalizeTableRow);

  return (
    <div className="rounded-md border border-border">
      <p className="border-b border-border bg-muted/40 px-3 py-1.5 text-xs font-medium">
        {table.title}
      </p>

      {/* Mobile: cards */}
      <div className={cn("divide-y divide-border md:hidden", wide ? "p-1" : "")}>
        {normalized.map((row, ri) => (
          <div key={ri} className="space-y-1.5 p-3">
            {row.cells.map((cell, ci) => (
              <div key={ci} className="grid grid-cols-[minmax(0,38%)_1fr] gap-2 text-xs">
                <span className="text-muted-foreground">{table.columns[ci] ?? ""}</span>
                <CellContent value={cell} />
              </div>
            ))}
            {row.actions && row.actions.length > 0 && (
              <AssistantActionButtons
                actions={row.actions}
                compact
                onNavigate={onNavigate}
                onQuickView={(entityType, entityId) =>
                  onQuickView?.({ entity_type: entityType, entity_id: entityId })
                }
              />
            )}
          </div>
        ))}
      </div>

      {/* Desktop: table with internal scroll */}
      <div className="hidden max-w-full overflow-x-auto md:block">
        <table className="w-full table-fixed text-left text-xs">
          <thead className="sticky top-0 z-[1] bg-muted/30">
            <tr className="border-b border-border">
              {table.columns.map((col) => (
                <th
                  key={col}
                  className="px-2 py-1.5 font-medium text-muted-foreground break-words"
                >
                  {col}
                </th>
              ))}
              <th className="w-[140px] px-2 py-1.5 font-medium text-muted-foreground">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {normalized.map((row, ri) => (
              <tr key={ri} className="border-b border-border/60 align-top last:border-0">
                {row.cells.map((cell, ci) => (
                  <td key={ci} className="px-2 py-1.5 break-words">
                    <CellContent value={cell} />
                  </td>
                ))}
                <td className="px-2 py-1.5">
                  {row.actions && row.actions.length > 0 ? (
                    <AssistantActionButtons
                      actions={row.actions}
                      compact
                      onNavigate={onNavigate}
                      onQuickView={(entityType, entityId) =>
                        onQuickView?.({ entity_type: entityType, entity_id: entityId })
                      }
                    />
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
