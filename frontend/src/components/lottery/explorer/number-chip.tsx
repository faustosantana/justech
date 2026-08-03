"use client";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { NUMBER_ACTIONS, type ExplorerAction } from "@/lib/lottery-explorer";
import { cn } from "@/lib/utils";

type Props = {
  number: number | string;
  className?: string;
  size?: "sm" | "md" | "lg";
  active?: boolean;
  onAction?: (action: ExplorerAction, number: string) => void;
};

/** Clickable number chip with quick-action menu (in-chat explorer). */
export function ExplorerNumberChip({
  number,
  className,
  size = "md",
  active,
  onAction,
}: Props) {
  const n = String(number).replace(/\D/g, "");
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  if (!n) return <span className={className}>—</span>;

  const sizeCls =
    size === "lg"
      ? "min-h-11 min-w-11 text-lg font-bold"
      : size === "sm"
        ? "min-h-7 min-w-7 text-xs font-semibold"
        : "min-h-9 min-w-9 text-sm font-bold";

  return (
    <div ref={ref} className="relative inline-flex">
      <button
        type="button"
        title={`Explorar ${n.padStart(2, "0")}`}
        className={cn(
          "inline-flex cursor-pointer items-center justify-center rounded-full shadow-sm transition hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400",
          active
            ? "bg-sky-700 text-white ring-2 ring-sky-300"
            : "bg-sky-600 text-white hover:bg-sky-700",
          sizeCls,
          className,
        )}
        onClick={() => {
          if (onAction) onAction("focus", n);
          setOpen((v) => !v);
        }}
        onContextMenu={(e) => {
          e.preventDefault();
          setOpen(true);
        }}
      >
        {n.padStart(2, "0")}
      </button>
      {open && (
        <div className="absolute left-0 top-full z-40 mt-1 min-w-[11rem] rounded-xl border border-border/70 bg-background p-1.5 shadow-lg">
          <p className="px-2 pb-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            {n.padStart(2, "0")}
          </p>
          {NUMBER_ACTIONS.map((a) => (
            <Button
              key={a.id}
              type="button"
              size="sm"
              variant="ghost"
              className="h-7 w-full justify-start text-xs"
              onClick={() => {
                setOpen(false);
                onAction?.(a.id, n);
              }}
            >
              {a.label}
            </Button>
          ))}
        </div>
      )}
    </div>
  );
}
