"use client";

import { Fragment, type ReactNode } from "react";

import { ExplorerNumberChip } from "@/components/lottery/explorer/number-chip";
import { Button } from "@/components/ui/button";
import { smartActionButtons, type ExplorerAction } from "@/lib/lottery-explorer";

const NUM_RE = /\b(100|[1-9]\d?)\b/g;

type Props = {
  content: string;
  activeNumber?: string | number | null;
  onAction?: (action: ExplorerAction, number?: string) => void;
};

/** Render assistant text with clickable lottery numbers + smart action buttons. */
export function InteractiveContent({ content, activeNumber, onAction }: Props) {
  const parts: ReactNode[] = [];
  let last = 0;
  const text = content || "";
  const re = new RegExp(NUM_RE.source, "g");
  let m: RegExpExecArray | null;
  let idx = 0;
  while ((m = re.exec(text)) !== null) {
    const raw = m[1];
    const n = Number(raw);
    if (n < 1 || n > 100) continue;
    if (m.index > last) {
      parts.push(<Fragment key={`t-${idx}`}>{text.slice(last, m.index)}</Fragment>);
    }
    parts.push(
      <ExplorerNumberChip
        key={`n-${idx}-${n}-${m.index}`}
        number={n}
        size="sm"
        active={activeNumber != null && String(activeNumber) === String(n)}
        onAction={(a, num) => onAction?.(a, num)}
        className="mx-0.5 align-middle"
      />,
    );
    last = m.index + raw.length;
    idx += 1;
  }
  if (last < text.length) {
    parts.push(<Fragment key={`t-end`}>{text.slice(last)}</Fragment>);
  }

  const buttons = smartActionButtons(text, activeNumber);

  return (
    <div className="space-y-2">
      <div className="whitespace-pre-wrap text-sm leading-relaxed text-foreground/90">
        {parts.length ? parts : text}
      </div>
      {buttons.length > 0 && onAction && (
        <div className="flex flex-wrap gap-1.5">
          {buttons.map((b) => (
            <Button
              key={b.id}
              type="button"
              size="sm"
              variant="outline"
              className="h-7 text-[11px]"
              onClick={() =>
                onAction(b.id, activeNumber != null ? String(activeNumber) : undefined)
              }
            >
              {b.label}
            </Button>
          ))}
        </div>
      )}
    </div>
  );
}
