"use client";

import { ExplorerNumberChip } from "@/components/lottery/explorer/number-chip";
import { Button } from "@/components/ui/button";
import type { ExplorerAction, NumberCard } from "@/lib/lottery-explorer";

type Props = {
  card: NumberCard;
  activeNumber?: string | number | null;
  onAction?: (action: ExplorerAction, number: string) => void;
  onNumber?: (action: ExplorerAction, number: string) => void;
};

export function ExplorerSmartCard({ card, activeNumber, onAction, onNumber }: Props) {
  const n = String(card.number);
  const handle = onNumber || onAction;

  return (
    <div className="space-y-3 rounded-2xl border border-border/60 bg-gradient-to-br from-sky-50/80 via-background to-emerald-50/40 p-3 dark:from-sky-950/30 dark:to-emerald-950/20">
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Número</p>
          <p className="text-3xl font-bold tabular-nums tracking-tight text-foreground">
            {card.label || n.padStart(2, "0")}
          </p>
        </div>
        <ExplorerNumberChip number={card.number} size="lg" active={String(activeNumber) === n} onAction={handle} />
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-xl bg-background/70 p-2">
          <p className="text-[10px] text-muted-foreground">Código Tabla 1</p>
          <p className="text-lg font-semibold tabular-nums">
            {card.table1.code != null ? String(card.table1.code).padStart(2, "0") : "—"}
          </p>
        </div>
        <div className="rounded-xl bg-background/70 p-2">
          <p className="text-[10px] text-muted-foreground">Código Tabla 2</p>
          <p className="text-lg font-semibold tabular-nums">
            {card.table2.code != null ? String(card.table2.code).padStart(2, "0") : "—"}
          </p>
        </div>
        <div className="rounded-xl bg-background/70 p-2">
          <p className="text-[10px] text-muted-foreground">Compañeros</p>
          <p className="text-lg font-semibold tabular-nums">{card.table1.companions_count}</p>
        </div>
        <div className="rounded-xl bg-background/70 p-2">
          <p className="text-[10px] text-muted-foreground">Vecinos</p>
          <p className="text-lg font-semibold tabular-nums">{card.table2.neighbors_count}</p>
        </div>
      </div>

      {card.table1.companions.length > 0 && (
        <div>
          <p className="mb-1 text-[10px] font-medium uppercase text-muted-foreground">Compañeros</p>
          <div className="flex flex-wrap gap-1.5">
            {card.table1.companions.map((c) => (
              <ExplorerNumberChip key={`c-${c}`} number={c} size="sm" onAction={handle} />
            ))}
          </div>
        </div>
      )}

      {card.table2.neighbors.length > 0 && (
        <div>
          <p className="mb-1 text-[10px] font-medium uppercase text-muted-foreground">Vecinos</p>
          <div className="flex flex-wrap gap-1.5">
            {card.table2.neighbors.map((c) => (
              <ExplorerNumberChip key={`v-${c}`} number={c} size="sm" onAction={handle} />
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-1.5">
        {(
          [
            ["analizar", "Analizar"],
            ["toggle_compare", "Comparar"],
            ["historico", "Histórico"],
            ["tabla1", "Tabla 1"],
            ["tabla2", "Tabla 2"],
          ] as const
        ).map(([id, label]) => (
          <Button
            key={id}
            type="button"
            size="sm"
            variant="outline"
            className="h-7 text-[11px]"
            onClick={() => handle?.(id, n)}
          >
            {label}
          </Button>
        ))}
      </div>
    </div>
  );
}
