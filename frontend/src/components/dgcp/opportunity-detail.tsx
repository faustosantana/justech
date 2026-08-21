"use client";

import { ArrowLeft, ExternalLink, History } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { DgcpAnalisisIaTab } from "@/components/dgcp/dgcp-analisis-ia-tab";
import {
  DgcpExpedienteContextProvider,
  ExpedienteContextStatusBanner,
} from "@/components/dgcp/dgcp-expediente-context";
import { DGCPHistoricalAwardsPanel } from "@/components/dgcp/dgcp-historical-awards-panel";
import { OpportunityBidSection } from "@/components/dgcp/opportunity-bid-section";
import { DgcpFunnelHeader } from "@/components/dgcp/dgcp-funnel-header";
import { DgcpOdooSyncCard } from "@/components/dgcp/dgcp-odoo-sync-card";
import { DgcpOdooProductMatchPanel } from "@/components/dgcp/dgcp-odoo-product-match-panel";
import { DgcpTechnicalSheetsPanel } from "@/components/dgcp/dgcp-technical-sheets-panel";
import { DGCPPrepPanel } from "@/components/modules/licitaciones/licitaciones-my-work-sections";
import { CreateTaskButton } from "@/components/work/create-task-button";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import { applyDGCPOpportunityAction } from "@/lib/dgcp-apply-action";
import { useAssistantContext } from "@/lib/assistant-context";
import { usePlatformAccess } from "@/hooks/use-platform-access";
import {
  DGCP_DETAIL_TABS,
  resolveDgcpDetailTab,
  type DgcpDetailTabId,
} from "@/lib/dgcp-detail-tabs";
import {
  ACTION_LABELS,
  COMPANY_LABELS,
  STATUS_LABELS,
  formatDateTime,
  isDGCPOperationalInterest,
  type DGCPOpportunity,
  type DGCPOpportunityHistory,
  type OpportunityAction,
} from "@/lib/dgcp";
import type { Task } from "@/lib/tasks";
import { cn } from "@/lib/utils";
import { dgcpProcessUpdatesEnabled } from "@/lib/dgcp-feature-flags";

interface OpportunityDetailProps {
  opportunity: DGCPOpportunity;
}

type TabId = DgcpDetailTabId;

export function OpportunityDetail({ opportunity: initial }: OpportunityDetailProps) {
  const searchParams = useSearchParams();
  const visibleTabs = DGCP_DETAIL_TABS;
  const [opportunity, setOpportunity] = useState(initial);
  const { access } = usePlatformAccess();
  const [history, setHistory] = useState<DGCPOpportunityHistory[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [activeTab, setActiveTab] = useState<TabId>("analisis-ia");
  const [autofillFormTypeHint, setAutofillFormTypeHint] = useState<string | undefined>();
  const [updating, setUpdating] = useState(false);
  const [execBid, setExecBid] = useState<import("@/lib/dgcp").DGCPBidPackage | null>(null);
  const [execChecklist, setExecChecklist] = useState<import("@/lib/dgcp").DGCPChecklist | null>(null);
  const [execStatus, setExecStatus] = useState<string | null>(null);
  const [processUpdatesPending, setProcessUpdatesPending] = useState(0);
  const [analysisJob, setAnalysisJob] = useState<{ status?: string } | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const { setContext } = useAssistantContext();

  const refreshAnalysisSnapshot = useCallback(() => {
    if (!isDGCPOperationalInterest(opportunity.status)) return;
    void Promise.all([
      apiClient.getDGCPBidPackage(opportunity.id).catch(() => null),
      apiClient.getDGCPChecklist(opportunity.id).catch(() => null),
      apiClient.getDGCPExpedienteStatus(opportunity.id).catch(() => null),
    ]).then(([bid, checklist, status]) => {
      if (bid?.analyzed_at) setExecBid(bid);
      if (checklist?.total) setExecChecklist(checklist);
      if (status?.expediente_status) setExecStatus(status.expediente_status);
    });
  }, [opportunity.id, opportunity.status]);

  useEffect(() => {
    const tabParam = searchParams.get("tab");
    if (tabParam) {
      setActiveTab(resolveDgcpDetailTab(tabParam));
    }
  }, [searchParams]);

  useEffect(() => {
    if (!isDGCPOperationalInterest(opportunity.status)) {
      setExecBid(null);
      setExecChecklist(null);
      setExecStatus(null);
      return;
    }
    void Promise.all([
      apiClient.getDGCPBidPackage(opportunity.id).catch(() => null),
      apiClient.getDGCPChecklist(opportunity.id).catch(() => null),
      apiClient.getDGCPExpedienteStatus(opportunity.id).catch(() => null),
      dgcpProcessUpdatesEnabled()
        ? apiClient.getDGCPProcessUpdates(opportunity.id).catch(() => null)
        : Promise.resolve(null),
    ]).then(([bid, checklist, status, updates]) => {
      if (bid?.analyzed_at) setExecBid(bid);
      if (checklist?.total) setExecChecklist(checklist);
      if (status?.expediente_status) setExecStatus(status.expediente_status);
      setProcessUpdatesPending(updates?.meta?.pending_count ?? 0);
    });
    (apiClient.getDGCPAnalysisStatus
      ? apiClient.getDGCPAnalysisStatus(opportunity.id)
      : Promise.resolve({ job: null })
    )
      .then((s) => {
        if (s.job?.status === "in_progress") setAnalysisJob(s.job);
        else setAnalysisJob(null);
      })
      .catch(() => {});
  }, [opportunity.id, opportunity.status]);

  useEffect(() => {
    if (!analysisJob || analysisJob.status !== "in_progress") return;
    const timer = window.setInterval(() => {
      void (apiClient.getDGCPAnalysisStatus
        ? apiClient.getDGCPAnalysisStatus(opportunity.id)
        : Promise.resolve({ job: null })
      )
        .then(async (s) => {
          if (!s.job || s.job.status !== "in_progress") {
            if (analysisJob) {
              const [bid, checklist, expStatus] = await Promise.all([
                apiClient.getDGCPBidPackage(opportunity.id).catch(() => null),
                apiClient.getDGCPChecklist(opportunity.id).catch(() => null),
                apiClient.getDGCPExpedienteStatus(opportunity.id).catch(() => null),
              ]);
              if (bid?.analyzed_at) setExecBid(bid);
              if (checklist?.total) setExecChecklist(checklist);
              if (expStatus?.expediente_status) setExecStatus(expStatus.expediente_status);
              if (!s.job) {
                setFlash("Análisis completado — métricas actualizadas.");
              }
            }
            setAnalysisJob(null);
            return;
          }
          setAnalysisJob(s.job);
        })
        .catch(() => {});
    }, 2500);
    return () => window.clearInterval(timer);
  }, [analysisJob, opportunity.id]);

  useEffect(() => {
    setContext({
      recordType: "dgcp",
      recordId: opportunity.id,
    });
    return () => {
      setContext({ recordType: null, recordId: null });
    };
  }, [opportunity.id, setContext]);

  useEffect(() => {
    apiClient.getDGCPOpportunityHistory(opportunity.id).then(setHistory).catch(() => {});
  }, [opportunity.id]);

  useEffect(() => {
    if (activeTab === "tareas") {
      apiClient
        .getTasks({ limit: 200 })
        .then((r) => setTasks(r.items.filter((t) => t.dgcp_process_id === opportunity.id)))
        .catch(() => setTasks([]));
    }
  }, [activeTab, opportunity.id]);

  const bidCenter = (opportunity.full_info as any)?.bid_center as
    | { odoo_url?: string; odoo_tender_id?: number; odoo_tender_reference?: string }
    | undefined;
  const odooContinueUrl = bidCenter?.odoo_url;

  async function applyAction(action: OpportunityAction) {
    setUpdating(true);
    setFlash(null);
    try {
      const { opportunity: updated, reconciled } = await applyDGCPOpportunityAction(
        opportunity.id,
        action,
      );
      setOpportunity(updated);
      try {
        const hist = await apiClient.getDGCPOpportunityHistory(opportunity.id);
        setHistory(hist);
      } catch {
        /* historial no bloquea la transición */
      }
      setFlash(
        reconciled
          ? `${ACTION_LABELS[action]} — guardado (confirmado en servidor).`
          : `${ACTION_LABELS[action]} — guardado.`,
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : "No se pudo aplicar la acción.";
      setFlash(msg);
    } finally {
      setUpdating(false);
    }
  }

  return (
    <DgcpExpedienteContextProvider opportunityId={opportunity.id}>
      <div className="space-y-6">
        {activeTab === "adjudicaciones" && <ExpedienteContextStatusBanner />}
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/dgcp">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Volver
            </Link>
          </Button>
          <div className="flex-1 min-w-0">
            <p className="font-mono text-sm text-primary">{opportunity.code}</p>
            <h2 className="text-xl font-bold truncate">{opportunity.title}</h2>
            <p className="text-sm text-muted-foreground">{opportunity.institution}</p>
          </div>
          <div className="flex items-center gap-2 shrink-0 flex-wrap justify-end">
            <Badge variant="muted">{COMPANY_LABELS[opportunity.company]}</Badge>
            {opportunity.confidence_score > 0 && (
              <Badge variant="outline">{opportunity.confidence_score}% confianza</Badge>
            )}
            {opportunity.source_url ? (
              <Button variant="outline" size="sm" asChild>
                <a href={opportunity.source_url} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="mr-1 h-3.5 w-3.5" />
                  DGCP
                </a>
              </Button>
            ) : null}
          </div>
        </div>

        {odooContinueUrl ? (
          <div className="mb-4 flex flex-wrap items-center gap-3 rounded-md border p-3">
            <span className="text-sm">
              Expediente en Odoo Bid Center
              {bidCenter?.odoo_tender_reference ? ` (${bidCenter.odoo_tender_reference})` : ""}.
            </span>
            <a className="underline font-medium" href={odooContinueUrl} target="_blank" rel="noreferrer">
              Continuar en Odoo
            </a>
          </div>
        ) : null}

        <DgcpFunnelHeader
          opportunity={opportunity}
          access={access}
          updating={updating}
          onAction={(a) => void applyAction(a)}
          variant="card"
        />

        {isDGCPOperationalInterest(opportunity.status) ? (
          <div className="mt-3">
            <DGCPPrepPanel opportunityId={opportunity.id} />
          </div>
        ) : null}

        <DgcpOdooSyncCard opportunity={opportunity} onUpdated={setOpportunity} />
        <div className="mt-3">
          <DgcpOdooProductMatchPanel opportunityId={opportunity.id} />
        </div>

        {flash && (
          <p
            className={cn(
              "text-sm rounded-lg border px-3 py-2",
              flash.includes("No se puede") || flash.includes("Solo puede")
                ? "text-destructive border-destructive/30"
                : "text-success border-success/30",
            )}
          >
            {flash}
          </p>
        )}

        <div className="flex flex-wrap items-center gap-1 border-b border-border pb-1 overflow-x-auto">
          {visibleTabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => setActiveTab(id)}
              className={cn(
                "flex items-center gap-1.5 rounded-t-lg px-3 py-2 text-sm font-medium transition-colors whitespace-nowrap",
                activeTab === id
                  ? "bg-primary/10 text-primary border-b-2 border-primary"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50",
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              {label}
              {id === "expediente" && processUpdatesPending > 0 ? (
                <span className="rounded-full bg-destructive px-1.5 py-0 text-[9px] text-destructive-foreground">
                  {processUpdatesPending}
                </span>
              ) : null}
            </button>
          ))}
        </div>

        {activeTab === "analisis-ia" && (
          <DgcpAnalisisIaTab
            opportunity={opportunity}
            execBid={execBid}
            execChecklist={execChecklist}
            execStatus={execStatus}
            onGoDocumentos={() => setActiveTab("documentos")}
            onAnalyzed={refreshAnalysisSnapshot}
          />
        )}

        <OpportunityBidSection
          opportunity={opportunity}
          activeTab={activeTab}
          interested={isDGCPOperationalInterest(opportunity.status)}
          autofillFormTypeHint={autofillFormTypeHint}
          onNavigateTab={(tab, opts) => {
            setActiveTab(resolveDgcpDetailTab(tab));
            if (opts?.formType) setAutofillFormTypeHint(opts.formType);
          }}
          onOpportunityUpdated={setOpportunity}
          onAnalysisUpdate={(bid, checklist, status) => {
            setExecBid(bid);
            setExecChecklist(checklist);
            setExecStatus(status);
          }}
        />

        {activeTab === "fichas" && isDGCPOperationalInterest(opportunity.status) && (
          <DgcpTechnicalSheetsPanel opportunityId={opportunity.id} />
        )}

        {activeTab === "tareas" && isDGCPOperationalInterest(opportunity.status) && (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">Tareas de esta licitación</CardTitle>
              <CreateTaskButton
                eventType="licitacion"
                title={`Preparar licitación ${opportunity.code}`}
                description={opportunity.title}
                dgcpProcessId={opportunity.id}
                source="dgcp_opportunity"
                label="Nueva tarea"
              />
            </CardHeader>
            <CardContent>
              {tasks.length === 0 ? (
                <p className="text-sm text-muted-foreground">No hay tareas vinculadas a este proceso.</p>
              ) : (
                <ul className="divide-y">
                  {tasks.map((t) => (
                    <li key={t.id} className="py-2">
                      <Link href={`/tasks/${t.id}`} className="text-sm font-medium text-primary hover:underline">
                        {t.title}
                      </Link>
                      <p className="text-xs text-muted-foreground">
                        {t.status} · {t.priority}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        )}

        {activeTab === "adjudicaciones" && <DGCPHistoricalAwardsPanel opportunity={opportunity} />}

        {activeTab === "expediente" && history.length > 0 ? (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <History className="h-4 w-4 text-primary" />
                Registro de acciones
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-3 max-h-56 overflow-y-auto">
                {history.slice(0, 25).map((entry) => (
                  <li key={entry.id} className="rounded-lg border border-border/50 p-3 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium capitalize">
                        {ACTION_LABELS[entry.action as OpportunityAction] ?? entry.action}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {formatDateTime(entry.created_at)}
                      </span>
                    </div>
                    {entry.from_status && entry.to_status ? (
                      <p className="text-xs text-muted-foreground mt-1">
                        {STATUS_LABELS[entry.from_status as keyof typeof STATUS_LABELS] ??
                          entry.from_status}
                        {" → "}
                        {STATUS_LABELS[entry.to_status as keyof typeof STATUS_LABELS] ?? entry.to_status}
                      </p>
                    ) : null}
                    {entry.notes ? (
                      <p className="text-xs text-muted-foreground mt-1">{entry.notes}</p>
                    ) : null}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        ) : null}
      </div>
    </DgcpExpedienteContextProvider>
  );
}
