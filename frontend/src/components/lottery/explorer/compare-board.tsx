"use client";

import { ExplorerSmartCard } from "@/components/lottery/explorer/smart-card";
import type { CompareBoard, ExplorerAction } from "@/lib/lottery-explorer";

type Props = {
  board: CompareBoard;
  onAction?: (action: ExplorerAction, number: string) => void;
};

export function ExplorerCompareBoard({ board, onAction }: Props) {
  if (!board.cards?.length) {
    return (
      <p className="text-xs text-muted-foreground">
        Añade números con «Comparar» para abrir una comparación.
      </p>
    );
  }
  return (
    <div className="space-y-2">
      <p className="text-xs font-medium">
        Comparación{" "}
        <span className="tabular-nums text-muted-foreground">
          {board.numbers.map((n) => String(n).padStart(2, "0")).join(" · vs · ")}
        </span>
      </p>
      <div className="grid gap-2 sm:grid-cols-2">
        {board.cards.map((card) => (
          <ExplorerSmartCard key={card.number} card={card} onAction={onAction} />
        ))}
      </div>
    </div>
  );
}
