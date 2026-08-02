"use client";

import type { InsightItem } from "@/lib/lottery-ux-present";
import { cn } from "@/lib/utils";

export function InsightPanel({
  items,
  className,
}: {
  items: InsightItem[];
  className?: string;
}) {
  if (!items.length) return null;
  return (
    <section
      className={cn("rounded-2xl border border-border/60 bg-card/80 p-4", className)}
      data-testid="insight-panel"
    >
      <h3 className="text-sm font-semibold text-foreground">Insights automáticos</h3>
      <ul className="mt-3 space-y-2.5">
        {items.map((item) => (
          <li
            key={item.id}
            className="rounded-xl border border-border/50 bg-muted/20 px-3 py-2.5"
          >
            <p className="text-xs font-medium text-primary">{item.title}</p>
            <p className="mt-0.5 text-sm leading-relaxed text-foreground/90">{item.body}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
