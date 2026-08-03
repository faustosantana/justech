"use client";

import { ExplorerNumberChip } from "@/components/lottery/explorer/number-chip";
import { ExplorerBreadcrumbs } from "@/components/lottery/explorer/breadcrumbs";
import { ExplorerSmartCard } from "@/components/lottery/explorer/smart-card";
import { ExplorerTableView } from "@/components/lottery/explorer/table-explorer";
import { ExplorerCompareBoard } from "@/components/lottery/explorer/compare-board";
import { Button } from "@/components/ui/button";
import {
  formatAnalyzingDuration,
  formatStartedAt,
  type CompareBoard,
  type ExplorerAction,
  type ExplorerNav,
  type NumberCard,
  type TableExplorerPayload,
} from "@/lib/lottery-explorer";
import type { LotteryChatSendResponse } from "@/lib/lottery";

type ActiveContext = NonNullable<LotteryChatSendResponse["active_context"]>;

type Props = {
  activeContext: ActiveContext | null;
  nav: ExplorerNav | null;
  card: NumberCard | null;
  table: TableExplorerPayload | null;
  compare: CompareBoard | null;
  onAction: (action: ExplorerAction, number?: string, extra?: { crumb_id?: string }) => void;
};

export function ExplorerSidePanel({
  activeContext,
  nav,
  card,
  table,
  compare,
  onAction,
}: Props) {
  const number = activeContext?.number ?? nav?.current?.number ?? null;
  const status = String(activeContext?.investigation_status || "");
  const crumbs = (activeContext?.breadcrumbs as ExplorerNav["breadcrumbs"]) ||
    nav?.breadcrumbs ||
    [{ id: "home", label: "Inicio" }];
  const recent = (activeContext?.recent_numbers as string[]) || nav?.recent_numbers || [];
  const favorites = (activeContext?.favorites as string[]) || nav?.favorites || [];
  const compareNums = (activeContext?.compare as string[]) || nav?.compare || [];
  const history = (nav?.stack || []).slice().reverse().slice(0, 8);

  return (
    <aside className="flex h-full flex-col gap-3 overflow-y-auto p-3 text-xs">
      <div>
        <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
          Investigación activa
        </p>
        <div className="space-y-1 rounded-xl border border-border/50 bg-muted/20 p-2">
          <p>
            <span className="text-muted-foreground">Número:</span>{" "}
            <span className="font-semibold tabular-nums">
              {number != null ? String(number).padStart(2, "0") : "—"}
            </span>
          </p>
          <p>
            <span className="text-muted-foreground">Tabla:</span>{" "}
            {(activeContext?.tables_label as string) || "1 y 2"}
          </p>
          <p>
            <span className="text-muted-foreground">Estado:</span>{" "}
            {status === "closed" ? "Cerrada" : status === "expired" ? "Expirada" : status ? "Activa" : "—"}
          </p>
          <p>
            <span className="text-muted-foreground">Inicio:</span>{" "}
            {formatStartedAt(activeContext?.started_at as string | undefined)}
          </p>
          <p>
            <span className="text-muted-foreground">Tiempo:</span>{" "}
            {formatAnalyzingDuration(activeContext?.analyzing_seconds as number | undefined)}
          </p>
          <p>
            <span className="text-muted-foreground">Origen:</span>{" "}
            {(activeContext?.origin as string) || nav?.origin || "—"}
          </p>
        </div>
      </div>

      <ExplorerBreadcrumbs
        crumbs={crumbs}
        canBack={Boolean(nav?.can_back ?? (activeContext?.explorer as ExplorerNav | undefined)?.can_back)}
        canForward={Boolean(nav?.can_forward ?? (activeContext?.explorer as ExplorerNav | undefined)?.can_forward)}
        onBack={() => onAction("back")}
        onForward={() => onAction("forward")}
        onCrumb={(id) => onAction("breadcrumb", undefined, { crumb_id: id })}
      />

      {card && (
        <ExplorerSmartCard
          card={card}
          activeNumber={number}
          onAction={(a, n) => onAction(a, n)}
        />
      )}

      {table && (
        <ExplorerTableView
          table={table}
          highlight={number}
          onAction={(a, n) => onAction(a, n)}
        />
      )}

      {compare && compare.cards?.length > 0 && (
        <ExplorerCompareBoard board={compare} onAction={(a, n) => onAction(a, n)} />
      )}

      <section>
        <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
          Historial
        </p>
        <div className="flex flex-wrap gap-1">
          {history.length === 0 && (
            <span className="text-muted-foreground">Sin navegación aún</span>
          )}
          {history.map((h) => (
            <Button
              key={h.id}
              type="button"
              size="sm"
              variant="ghost"
              className="h-7 px-2 text-[11px]"
              onClick={() => onAction("breadcrumb", h.number || undefined, { crumb_id: h.id })}
            >
              {h.label}
            </Button>
          ))}
        </div>
      </section>

      <section>
        <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
          Comparaciones abiertas
        </p>
        <div className="flex flex-wrap gap-1.5">
          {compareNums.length === 0 && (
            <span className="text-muted-foreground">Ninguna</span>
          )}
          {compareNums.map((n) => (
            <ExplorerNumberChip
              key={`cmp-${n}`}
              number={n}
              size="sm"
              onAction={(a, num) => onAction(a, num)}
            />
          ))}
        </div>
      </section>

      <section>
        <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
          Favoritos
        </p>
        <div className="flex flex-wrap gap-1.5">
          {favorites.length === 0 && (
            <span className="text-muted-foreground">Ninguno</span>
          )}
          {favorites.map((n) => (
            <ExplorerNumberChip
              key={`fav-${n}`}
              number={n}
              size="sm"
              onAction={(a, num) => onAction(a, num)}
            />
          ))}
          {number != null && (
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-7 text-[11px]"
              onClick={() => onAction("toggle_favorite", String(number))}
            >
              ★ Guardar actual
            </Button>
          )}
        </div>
      </section>

      <section>
        <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
          Últimos números visitados
        </p>
        <div className="flex flex-wrap gap-1.5">
          {recent.length === 0 && (
            <span className="text-muted-foreground">—</span>
          )}
          {recent.map((n) => (
            <ExplorerNumberChip
              key={`rec-${n}`}
              number={n}
              size="sm"
              active={String(number) === String(n)}
              onAction={(a, num) => onAction(a, num)}
            />
          ))}
        </div>
      </section>
    </aside>
  );
}
