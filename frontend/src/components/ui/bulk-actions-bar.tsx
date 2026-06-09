"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { useCompanyContext } from "@/lib/company-context";

type BulkAction = {
  id: string;
  label: string;
  onRun: (selectedIds: string[]) => Promise<string | void>;
  variant?: "default" | "destructive" | "outline";
  disabled?: boolean;
};

type BulkActionsBarProps = {
  selectedIds: string[];
  allIds: string[];
  onSelectAll: () => void;
  onClearSelection: () => void;
  actions: BulkAction[];
};

export function BulkActionsBar({
  selectedIds,
  allIds,
  onSelectAll,
  onClearSelection,
  actions,
}: BulkActionsBarProps) {
  const [busy, setBusy] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(
    null,
  );
  const count = selectedIds.length;

  const visibleActions = useMemo(() => actions.filter((a) => Boolean(a.onRun)), [actions]);

  if (allIds.length === 0) return null;

  return (
    <div className="space-y-2" data-testid="bulk-actions-bar">
    <div className="flex flex-wrap items-center gap-2 rounded-xl border border-border/80 bg-muted/30 px-3 py-2 text-sm">
      <label className="flex items-center gap-2 text-muted-foreground">
        <input
          type="checkbox"
          data-testid="bulk-select-all"
          checked={count > 0 && count === allIds.length}
          onChange={(e) => (e.target.checked ? onSelectAll() : onClearSelection())}
        />
        Seleccionar todos ({allIds.length})
      </label>
      {count > 0 && (
        <>
          <span className="text-muted-foreground">·</span>
          <span data-testid="bulk-selected-count">{count} seleccionado(s)</span>
          <Button type="button" size="sm" variant="ghost" data-testid="bulk-clear" onClick={onClearSelection}>
            Limpiar
          </Button>
          {visibleActions.map((action) => (
            <Button
              key={action.id}
              type="button"
              size="sm"
              variant={action.variant ?? "outline"}
              data-testid={`bulk-action-${action.id}`}
              disabled={busy !== null || action.disabled}
              onClick={async () => {
                setBusy(action.id);
                setFeedback(null);
                try {
                  const message = await action.onRun(selectedIds);
                  if (message) {
                    setFeedback({ type: "success", message });
                  }
                } catch (err) {
                  setFeedback({
                    type: "error",
                    message: err instanceof Error ? err.message : "Error en acción masiva",
                  });
                } finally {
                  setBusy(null);
                }
              }}
            >
              {busy === action.id ? "…" : action.label}
            </Button>
          ))}
        </>
      )}
    </div>
    {feedback && (
      <div
        data-testid="bulk-feedback"
        data-feedback-type={feedback.type}
        className={
          feedback.type === "success"
            ? "rounded-xl border border-success/40 bg-success/10 px-3 py-2 text-sm text-success"
            : "rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
        }
      >
        {feedback.message}
      </div>
    )}
    </div>
  );
}

export function CompanyScopeBadge({ compact = false }: { compact?: boolean }) {
  const { scopeLabel, loading } = useCompanyContext();
  if (loading) return null;
  return (
    <span
      className={
        compact
          ? "hidden text-xs text-muted-foreground lg:inline"
          : "text-xs text-muted-foreground"
      }
    >
      {scopeLabel}
    </span>
  );
}
