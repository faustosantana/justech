"use client";

import { cn } from "@/lib/utils";

export type BriefingMode = "managerial" | "operational" | "bidding";

const MODES: { id: BriefingMode; label: string }[] = [
  { id: "managerial", label: "Gerencial" },
  { id: "operational", label: "Operativo" },
  { id: "bidding", label: "Licitaciones" },
];

interface CopilotModeSelectorProps {
  mode: BriefingMode;
  onChange: (mode: BriefingMode) => void;
}

export function CopilotModeSelector({ mode, onChange }: CopilotModeSelectorProps) {
  return (
    <div className="flex flex-wrap gap-1 rounded-lg border border-border/60 bg-muted/30 p-1">
      {MODES.map((m) => (
        <button
          key={m.id}
          type="button"
          onClick={() => onChange(m.id)}
          className={cn(
            "rounded-md px-2.5 py-1 text-[10px] font-medium transition",
            mode === m.id
              ? "bg-primary text-primary-foreground shadow-sm"
              : "text-muted-foreground hover:bg-background hover:text-foreground",
          )}
        >
          {m.label}
        </button>
      ))}
    </div>
  );
}

export const BRIEFING_MODE_STORAGE_KEY = "jaios_briefing_mode";

export function loadBriefingMode(): BriefingMode {
  if (typeof window === "undefined") return "managerial";
  const v = localStorage.getItem(BRIEFING_MODE_STORAGE_KEY);
  if (v === "operational" || v === "bidding" || v === "managerial") return v;
  return "managerial";
}

export function saveBriefingMode(mode: BriefingMode): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(BRIEFING_MODE_STORAGE_KEY, mode);
}
