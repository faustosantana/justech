"use client";

import type { TimelineItem } from "@/lib/lottery-ux-present";
import { EmptyState } from "@/components/lottery/ux/empty-state";
import { cn } from "@/lib/utils";

export function TimelineView({
  items,
  className,
}: {
  items: TimelineItem[];
  className?: string;
}) {
  if (!items.length) {
    return (
      <EmptyState
        title="Sin línea temporal"
        body="Cuando existan fechas en los resultados, verás aquí la secuencia reciente."
      />
    );
  }

  return (
    <div className={cn("relative space-y-0", className)} data-testid="timeline-view">
      <div className="absolute bottom-2 left-[11px] top-2 w-px bg-border" aria-hidden />
      <ul className="space-y-3">
        {items.map((item) => (
          <li key={item.id} className="relative flex gap-3 pl-1">
            <span className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full border-2 border-primary bg-background" />
            <div className="min-w-0 flex-1 rounded-xl border border-border/50 bg-card/70 px-3 py-2">
              <p className="text-xs font-medium text-primary">{item.date}</p>
              <p className="truncate text-sm text-foreground">{item.label}</p>
              {item.meta ? (
                <p className="text-xs text-muted-foreground">{item.meta}</p>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
