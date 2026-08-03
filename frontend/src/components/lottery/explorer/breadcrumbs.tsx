"use client";

import { Button } from "@/components/ui/button";
import type { ExplorerCrumb } from "@/lib/lottery-explorer";
import { cn } from "@/lib/utils";

type Props = {
  crumbs: ExplorerCrumb[];
  canBack?: boolean;
  canForward?: boolean;
  onCrumb?: (crumbId: string) => void;
  onBack?: () => void;
  onForward?: () => void;
};

export function ExplorerBreadcrumbs({
  crumbs,
  canBack,
  canForward,
  onCrumb,
  onBack,
  onForward,
}: Props) {
  return (
    <div className="flex flex-wrap items-center gap-1 text-[11px]">
      <div className="mr-1 flex gap-0.5">
        <Button
          type="button"
          size="sm"
          variant="ghost"
          className="h-6 px-1.5 text-[11px]"
          disabled={!canBack}
          onClick={onBack}
          title="Atrás"
        >
          ←
        </Button>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          className="h-6 px-1.5 text-[11px]"
          disabled={!canForward}
          onClick={onForward}
          title="Adelante"
        >
          →
        </Button>
      </div>
      {crumbs.map((c, i) => (
        <span key={c.id || `${c.label}-${i}`} className="inline-flex items-center gap-1">
          {i > 0 && <span className="text-muted-foreground/60">›</span>}
          <button
            type="button"
            className={cn(
              "rounded px-1.5 py-0.5 transition hover:bg-muted/60",
              i === crumbs.length - 1
                ? "font-medium text-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
            onClick={() => onCrumb?.(c.id)}
          >
            {c.label}
          </button>
        </span>
      ))}
    </div>
  );
}
