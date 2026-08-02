"use client";

import { AnalysisResponse } from "@/components/lottery/ux/analysis-response";
import type { LotteryChatSendResponse } from "@/lib/lottery";

type Structured = NonNullable<LotteryChatSendResponse["message"]["structured_content"]>;

/**
 * Compatibility wrapper — all structured lottery results render through UX 2.0.
 * Preserves data-testid hooks via AnalysisResponse / ExportPanel.
 */
export function LotteryStructuredRenderer({
  structured,
  content = "",
  query,
  activeContext,
  toolTrace,
  latencyMs,
  sessionContext,
}: {
  structured?: Structured | null;
  content?: string;
  query?: string;
  activeContext?: LotteryChatSendResponse["active_context"];
  toolTrace?: LotteryChatSendResponse["message"]["tool_trace"];
  latencyMs?: number | null;
  sessionContext?: Record<string, unknown> | null;
}) {
  if (!structured) return null;
  return (
    <AnalysisResponse
      content={content}
      structured={structured}
      query={query}
      activeContext={activeContext}
      toolTrace={toolTrace}
      latencyMs={latencyMs}
      sessionContext={sessionContext}
      showSidePanel={false}
    />
  );
}
