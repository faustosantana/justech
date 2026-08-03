"use client";

import { ExplorerNumberChip } from "@/components/lottery/explorer/number-chip";
import { Button } from "@/components/ui/button";
import {
  formatAnalyzingDuration,
  formatStartedAt,
  type ExplorerAction,
  type ExplorerNav,
} from "@/lib/lottery-explorer";
import type { LotteryChatSendResponse } from "@/lib/lottery";

type ActiveContext = NonNullable<LotteryChatSendResponse["active_context"]>;

type Props = {
  activeContext: ActiveContext;
  onChange?: () => void;
  onClose?: () => void;
  onBack?: () => void;
  onAction?: (action: ExplorerAction, number?: string) => void;
};

export function InvestigationBanner({
  activeContext,
  onChange,
  onClose,
  onBack,
  onAction,
}: Props) {
  const nums = (activeContext.numbers as Array<string | number> | undefined) || [];
  const numberLabel =
    nums.length >= 2
      ? nums.slice(0, 4).map((n) => String(n).padStart(2, "0")).join(" · ")
      : String(activeContext.number ?? nums[0] ?? "—").padStart(2, "0");
  const status = String(activeContext.investigation_status || "active");
  const statusLabel =
    status === "closed" ? "Cerrada" : status === "expired" ? "Expirada" : "Activa";
  const tables =
    (activeContext.tables_label as string | undefined) ||
    ((activeContext.tables as string[] | undefined) || []).join(" y ") ||
    "1 y 2";
  const explorer = activeContext.explorer as ExplorerNav | undefined;
  const canBack = Boolean(explorer?.can_back);

  return (
    <div className="flex flex-wrap items-start justify-between gap-2 border-b border-border/60 bg-muted/15 px-3 py-2 text-[11px]">
      <div className="space-y-1 text-muted-foreground">
        <p className="font-medium text-foreground/90">Investigación Activa</p>
        <div className="flex flex-wrap items-center gap-2">
          <span>
            <span className="font-medium text-foreground/80">Número:</span> {numberLabel}
          </span>
          {activeContext.number != null && (
            <ExplorerNumberChip
              number={activeContext.number}
              size="sm"
              active
              onAction={(a, n) => onAction?.(a, n)}
            />
          )}
        </div>
        <p>
          <span className="font-medium text-foreground/80">Tabla:</span> {tables}
        </p>
        <p>
          <span className="font-medium text-foreground/80">Estado:</span> {statusLabel}
        </p>
        <p>
          <span className="font-medium text-foreground/80">Fecha inicio:</span>{" "}
          {formatStartedAt(activeContext.started_at as string | undefined)}
        </p>
        <p>
          <span className="font-medium text-foreground/80">Tiempo analizando:</span>{" "}
          {formatAnalyzingDuration(activeContext.analyzing_seconds as number | undefined)}
        </p>
        <p>
          <span className="font-medium text-foreground/80">Origen:</span>{" "}
          {(activeContext.origin as string) || "—"}
        </p>
      </div>
      <div className="flex flex-wrap gap-1">
        {canBack && (
          <Button size="sm" variant="ghost" onClick={onBack}>
            Volver anterior
          </Button>
        )}
        <Button size="sm" variant="ghost" onClick={onChange}>
          Cambiar investigación
        </Button>
        <Button size="sm" variant="ghost" onClick={onClose}>
          Cerrar investigación
        </Button>
      </div>
    </div>
  );
}
