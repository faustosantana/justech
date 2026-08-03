"use client";

import type { SummaryCardItem } from "@/lib/lottery-ux-present";
import { cn } from "@/lib/utils";

export function SummaryCards({
  items,
  className,
}: {
  items: SummaryCardItem[];
  className?: string;
}) {
  if (!items.length) return null;
  return (
    <div
      className={cn(
        "grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4",
        className,
      )}
      data-testid="summary-cards"
    >
      {items.map((item) => (
        <div
          key={item.id}
          className="rounded-2xl border border-border/60 bg-gradient-to-b from-card to-muted/30 px-4 py-3.5 shadow-sm"
        >
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            {item.label}
          </p>
          <p className="mt-1.5 text-2xl font-semibold tracking-tight text-foreground tabular-nums">
            {item.value}
          </p>
          {item.hint ? (
            <p className="mt-1 text-xs text-muted-foreground">{item.hint}</p>
          ) : null}
        </div>
      ))}
    </div>
  );
}
