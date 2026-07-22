"use client";

import Link from "next/link";

import { AssistantActionButtons } from "@/components/assistant/assistant-action-buttons";
import { CopilotModeSelector, type BriefingMode } from "@/components/assistant/copilot-mode-selector";
import type { CopilotBriefingResponse } from "@/lib/assistant";

interface CopilotExecutivePanelProps {
  briefing: CopilotBriefingResponse | null;
  loading?: boolean;
  mode: BriefingMode;
  onModeChange: (mode: BriefingMode) => void;
  onAsk: (question: string) => void;
}

function SectionBlock({
  title,
  items,
  onAsk,
}: {
  title: string;
  items: CopilotBriefingResponse["priorities"]["items"];
  onAsk: (q: string) => void;
}) {
  if (!items.length) return null;
  return (
    <div className="space-y-2">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">{title}</p>
      <ul className="space-y-1.5">
        {items.map((item, i) => (
          <li key={`${title}-${i}`} className="rounded-lg border border-border/60 bg-background/80 px-3 py-2 text-xs">
            <p className="font-medium text-foreground">{item.label}</p>
            {item.detail && <p className="mt-0.5 text-muted-foreground">{item.detail}</p>}
            <div className="mt-2 flex flex-wrap gap-1">
              {item.question && (
                <button
                  type="button"
                  onClick={() => onAsk(item.question!)}
                  className="rounded-md border border-primary/30 px-2 py-0.5 text-[10px] text-primary hover:bg-primary/5"
                >
                  Preguntar
                </button>
              )}
              {item.href && (
                <Link
                  href={item.href}
                  className="rounded-md border border-border px-2 py-0.5 text-[10px] hover:bg-muted/50"
                >
                  Abrir
                </Link>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function CopilotExecutivePanel({
  briefing,
  loading,
  mode,
  onModeChange,
  onAsk,
}: CopilotExecutivePanelProps) {
  if (loading) {
    return <p className="text-sm text-muted-foreground">Preparando briefing…</p>;
  }
  if (!briefing) return null;

  return (
    <div className="space-y-4">
      <CopilotModeSelector mode={mode} onChange={onModeChange} />
      {briefing.company_name && (
        <p className="text-[10px] text-muted-foreground">
          {briefing.company_name}
          {briefing.updated_at ? ` · actualizado ${new Date(briefing.updated_at).toLocaleTimeString("es-DO", { hour: "2-digit", minute: "2-digit" })}` : ""}
        </p>
      )}
      <div className="brand-surface-accent rounded-xl p-4 text-sm whitespace-pre-wrap">
        <p className="font-medium text-foreground">{briefing.greeting}</p>
        {briefing.quick_actions.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {briefing.quick_actions.map((a) => (
              <button
                key={a.label}
                type="button"
                onClick={() => {
                  if (a.question) onAsk(a.question);
                  else if (a.href) window.location.href = a.href;
                }}
                className="brand-chip cursor-pointer border-border/80 bg-background px-3 py-1 normal-case tracking-normal hover:border-primary/40"
              >
                {a.label}
              </button>
            ))}
          </div>
        )}
      </div>

      <SectionBlock title={briefing.priorities.title} items={briefing.priorities.items} onAsk={onAsk} />
      <SectionBlock title={briefing.alerts.title} items={briefing.alerts.items} onAsk={onAsk} />
      <SectionBlock title={briefing.opportunities.title} items={briefing.opportunities.items} onAsk={onAsk} />
      <SectionBlock title={briefing.recommendations.title} items={briefing.recommendations.items} onAsk={onAsk} />
      <SectionBlock title={briefing.recent_activity.title} items={briefing.recent_activity.items} onAsk={onAsk} />
    </div>
  );
}
