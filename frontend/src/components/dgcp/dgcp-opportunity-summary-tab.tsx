"use client";

import { useCallback, useEffect, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

import { DgcpOdooProductMatchPanel } from "@/components/dgcp/dgcp-odoo-product-match-panel";
import { DgcpOdooSyncCard } from "@/components/dgcp/dgcp-odoo-sync-card";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api";
import {
  COMPANY_LABELS,
  formatDate,
  formatDateTime,
  isDGCPOperationalInterest,
  type DGCPOpportunity,
} from "@/lib/dgcp";
import type { PrepChecklistResponse } from "@/lib/dgcp-my-work";
import { trafficDot } from "@/lib/dgcp-my-work";
import { resolveOpportunityGuidance } from "@/lib/dgcp-funnel";
import type { DgcpDetailTabId } from "@/lib/dgcp-detail-tabs";
import { cn } from "@/lib/utils";

type Props = {
  opportunity: DGCPOpportunity;
  onUpdated?: (opp: DGCPOpportunity) => void;
  onNavigateTab: (tab: DgcpDetailTabId) => void;
  docsCount?: number | null;
  checklistDone?: number | null;
  checklistTotal?: number | null;
};

export function DgcpOpportunitySummaryTab({
  opportunity,
  onUpdated,
  onNavigateTab,
  docsCount,
  checklistDone,
  checklistTotal,
}: Props) {
  const guidance = resolveOpportunityGuidance(opportunity);
  const interested = isDGCPOperationalInterest(opportunity.status);
  const [prep, setPrep] = useState<PrepChecklistResponse | null>(null);
  const [odooOpen, setOdooOpen] = useState(false);
  const [loadingPrep, setLoadingPrep] = useState(false);

  const loadPrep = useCallback(async () => {
    if (!interested) {
      setPrep(null);
      return;
    }
    setLoadingPrep(true);
    try {
      setPrep(await apiClient.getDGCPPrepChecklist(opportunity.id));
    } catch {
      setPrep(null);
    } finally {
      setLoadingPrep(false);
    }
  }, [opportunity.id, interested]);

  useEffect(() => {
    void loadPrep();
  }, [loadPrep]);

  const responsible =
    prep?.responsible_name ||
    opportunity.responsible_name ||
    (typeof opportunity.full_info?.responsible_name === "string"
      ? opportunity.full_info.responsible_name
      : null);

  const overdue =
    prep?.items.filter((t) => t.traffic_light === "black" || t.traffic_light === "red").length ?? 0;
  const upcoming =
    prep?.items.filter(
      (t) =>
        (t.status === "pending" || t.status === "in_progress") &&
        (t.traffic_light === "orange" || t.traffic_light === "yellow"),
    ).length ?? 0;

  const sync = (opportunity.full_info?.odoo_sync || undefined) as Record<string, unknown> | undefined;
  const crmStatus = sync ? String(sync.status || "—") : "No vinculado";

  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <section className="rounded-lg border bg-card p-3 sm:p-4">
        <div className="mb-2 flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold">Preparación</h2>
          {prep ? (
            <span className="text-xs text-muted-foreground">
              {prep.progress.completed}/{prep.progress.applicable} · {prep.progress.pct}%
            </span>
          ) : null}
        </div>
        {!interested ? (
          <p className="text-sm text-muted-foreground">
            Marque interés para activar el checklist operativo de preparación.
          </p>
        ) : loadingPrep && !prep ? (
          <p className="text-sm text-muted-foreground">Cargando preparación…</p>
        ) : prep ? (
          <div className="space-y-3">
            <div className="h-1.5 overflow-hidden rounded bg-muted">
              <div
                className="h-full rounded bg-emerald-500"
                style={{ width: `${Math.min(100, prep.progress.pct)}%` }}
              />
            </div>
            <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
              <span>
                <strong className="text-foreground">{overdue}</strong> urgentes
              </span>
              <span>
                <strong className="text-foreground">{upcoming}</strong> próximos
              </span>
              <span>
                <strong className="text-foreground">{prep.open_tasks_assigned_to_responsible ?? 0}</strong>{" "}
                abiertos del responsable
              </span>
            </div>
            {prep.next_pending ? (
              <div className="rounded-md border border-amber-200/80 bg-amber-50/70 px-3 py-2 text-sm">
                <p className="text-[11px] font-medium uppercase tracking-wide text-amber-800">
                  Próximo pendiente
                </p>
                <p className="mt-0.5 font-medium text-amber-950">
                  {trafficDot(prep.next_pending.traffic_light)} {prep.next_pending.title}
                </p>
                <p className="text-xs text-amber-800/80">
                  {formatDateTime(prep.next_pending.due_at)}
                </p>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Sin pendientes abiertos.</p>
            )}
            <Button size="sm" variant="outline" onClick={() => onNavigateTab("tareas")}>
              Ver preparación y pendientes
            </Button>
          </div>
        ) : (
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">Sin checklist de preparación aún.</p>
            <Button size="sm" variant="outline" onClick={() => onNavigateTab("tareas")}>
              Ir a preparación
            </Button>
          </div>
        )}
      </section>

      <section className="rounded-lg border bg-card p-3 sm:p-4">
        <h2 className="mb-2 text-sm font-semibold">Proceso</h2>
        <dl className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">Estado</dt>
            <dd className="font-medium">{guidance.funnelStageLabel}</dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">Deadline</dt>
            <dd className="font-medium">{formatDate(opportunity.deadline)}</dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">Responsable</dt>
            <dd className="font-medium">{responsible || "Sin asignar"}</dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">Empresa</dt>
            <dd className="font-medium">
              {COMPANY_LABELS[opportunity.company] || opportunity.company}
            </dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">Monto</dt>
            <dd className="font-medium">
              {opportunity.amount != null
                ? `${opportunity.currency || "DOP"} ${Number(opportunity.amount).toLocaleString("es-DO")}`
                : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">Siguiente</dt>
            <dd className="text-muted-foreground">{guidance.nextAction || "—"}</dd>
          </div>
        </dl>
      </section>

      <section className="rounded-lg border bg-card p-3 sm:p-4">
        <h2 className="mb-2 text-sm font-semibold">Documentos y checklist</h2>
        <div className="flex flex-wrap gap-4 text-sm">
          <div>
            <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Documentos</p>
            <p className="font-medium">
              {docsCount != null ? `${docsCount} en expediente` : "—"}
            </p>
            <Button
              size="sm"
              variant="link"
              className="h-auto px-0 py-1"
              onClick={() => onNavigateTab("documentos")}
            >
              Abrir documentos
            </Button>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Checklist</p>
            <p className="font-medium">
              {checklistTotal != null
                ? `${checklistDone ?? 0}/${checklistTotal}`
                : "—"}
            </p>
            <Button
              size="sm"
              variant="link"
              className="h-auto px-0 py-1"
              onClick={() => onNavigateTab("checklist")}
            >
              Abrir checklist
            </Button>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Análisis IA</p>
            <Button
              size="sm"
              variant="link"
              className="h-auto px-0 py-1"
              onClick={() => onNavigateTab("analisis-ia")}
            >
              Ver análisis
            </Button>
          </div>
        </div>
      </section>

      <section className="rounded-lg border bg-card p-3 sm:p-4">
        <button
          type="button"
          className="flex w-full items-center justify-between gap-2 text-left"
          onClick={() => setOdooOpen((v) => !v)}
        >
          <div>
            <h2 className="text-sm font-semibold">Integración Odoo</h2>
            <p className="text-xs text-muted-foreground">
              CRM: {crmStatus === "synced" ? "Vinculado" : crmStatus === "sync_pending" ? "Pendiente" : "—"}
              {" · "}Matching en detalle
            </p>
          </div>
          {odooOpen ? (
            <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
          )}
        </button>
        <div className={cn("mt-3 space-y-3", !odooOpen && "hidden")}>
          <DgcpOdooSyncCard opportunity={opportunity} onUpdated={onUpdated} compact />
          <DgcpOdooProductMatchPanel opportunityId={opportunity.id} compact />
        </div>
        {!odooOpen ? (
          <div className="mt-2 flex flex-wrap gap-2">
            <Button size="sm" variant="outline" onClick={() => setOdooOpen(true)}>
              Expandir integración
            </Button>
          </div>
        ) : null}
      </section>
    </div>
  );
}
