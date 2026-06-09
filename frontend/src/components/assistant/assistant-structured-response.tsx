"use client";

import { AssistantActionButtons } from "@/components/assistant/assistant-action-buttons";
import { AssistantDataTable } from "@/components/assistant/assistant-data-table";
import { AssistantLinks } from "@/components/assistant/assistant-links";
import { AssistantMetricsGrid } from "@/components/assistant/assistant-metrics-grid";
import { AssistantWarnings } from "@/components/assistant/assistant-warnings";
import {
  isBusinessAnswer,
  type BusinessAnswer,
  type QuickViewTarget,
  type SalesReport,
  type StructuredAnswerBase,
} from "@/lib/assistant-types";

interface AssistantStructuredResponseProps {
  data: SalesReport | BusinessAnswer;
  wide?: boolean;
  onQuickView?: (target: QuickViewTarget) => void;
  onNavigate?: () => void;
}

export function AssistantStructuredResponse({
  data,
  wide = false,
  onQuickView,
  onNavigate,
}: AssistantStructuredResponseProps) {
  const base = data as StructuredAnswerBase;

  return (
    <div className="mt-2 max-w-full space-y-3 overflow-hidden text-xs">
      {base.summary && (
        <p className="break-words text-sm font-medium leading-snug text-foreground">
          {base.summary}
        </p>
      )}

      <AssistantMetricsGrid metrics={base.metrics} wide={wide} />

      {base.tables.map((table) => (
        <AssistantDataTable
          key={table.title}
          table={table}
          wide={wide}
          onQuickView={onQuickView}
          onNavigate={onNavigate}
        />
      ))}

      <AssistantWarnings warnings={base.warnings} />

      {base.actions && base.actions.length > 0 && (
        <AssistantActionButtons
          actions={base.actions}
          onQuickView={(entityType, entityId) =>
            onQuickView?.({ entity_type: entityType, entity_id: entityId })
          }
          onNavigate={onNavigate}
        />
      )}

      {isBusinessAnswer(data) && data.links.length > 0 && (
        <AssistantLinks links={data.links} onNavigate={onNavigate} />
      )}
    </div>
  );
}
