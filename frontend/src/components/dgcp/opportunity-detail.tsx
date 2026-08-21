"use client";

import { History } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { DgcpAnalisisIaTab } from "@/components/dgcp/dgcp-analisis-ia-tab";
import {
  DgcpExpedienteContextProvider,
  ExpedienteContextStatusBanner,
} from "@/components/dgcp/dgcp-expediente-context";
import { DGCPHistoricalAwardsPanel } from "@/components/dgcp/dgcp-historical-awards-panel";
import { OpportunityBidSection } from "@/components/dgcp/opportunity-bid-section";
import { DgcpOpportunitySummaryTab } from "@/components/dgcp/dgcp-opportunity-summary-tab";
import { DgcpOpportunityWorkspaceHeader } from "@/components/dgcp/dgcp-opportunity-workspace-header";
import { DgcpTechnicalSheetsPanel } from "@/components/dgcp/dgcp-technical-sheets-panel";
import { DGCPPrepPanel } from "@/components/modules/licitaciones/licitaciones-my-work-sections";
import { CreateTaskButton } from "@/components/work/create-task-button";
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
  formatDateTime,
  isDGCPOperationalInterest,
  STATUS_LABELS,
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
  const router = useRouter();
  const pathname = usePathname();
  const visibleTabs = DGCP_DETAIL_TABS;
  const [opportunity, setOpportunity] = useState(initial);
  const { access } = usePlatformAccess();
  const [history, setHistory] = useState<DGCPOpportunityHistory[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [activeTab, setActiveTab] = useState<TabId>(() =>
    resolveDgcpDetailTab(searchParams.get("tab")),
  );
  const [autofillFormTypeHint, setAutofillFormTypeHint] = useState<string | undefined>();
  const [updating, setUpdating] = useState(false);
  const [execBid, setExecBid] = useState<import("@/lib/dgcp").DGCPBidPackage | null>(null);
  const [execChecklist, setExecChecklist] = useState<import("@/lib/dgcp").DGCPChecklist | null>(null);
  const [execStatus, setExecStatus] = useState<string | null>(null);
  const [processUpdatesPending, setProcessUpdatesPending] = useState(0);
  const [analysisJob, setAnalysisJob] = useState<{ status?: string } | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const [prepBadge, setPrepBadge] = useState<string | null>(null);
  const { setContext } = useAssistantContext();

  const selectTab = useCallback(
    (id: TabId) => {
      setActiveTab(id);
      const params = new URLSearchParams(searchParams.toString());
      params.set("tab", id);
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [pathname, router, searchParams],
  );

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
      setPrepBadge(null);
      return;
    }
    void Promise.all([
      apiClient.getDGCPBidPackage(opportunity.id).catch(() => null),
      apiClient.getDGCPChecklist(opportunity.id).catch(() => null),
      apiClient.getDGCPExpedienteStatus(opportunity.id).catch(() => null),
      dgcpProcessUpdatesEnabled()
        ? apiClient.getDGCPProcessUpdates(opportunity.id).catch(() => null)
        : Promise.resolve(null),
      apiClient.getDGCPPrepChecklist(opportunity.id).catch(() => null),
    ]).then(([bid, checklist, status, updates, prep]) => {
      if (bid?.analyzed_at) setExecBid(bid);
      if (checklist?.total) setExecChecklist(checklist);
      if (status?.expediente_status) setExecStatus(status.expediente_status);
      setProcessUpdatesPending(updates?.meta?.pending_count ?? 0);
      if (prep?.progress) {
        setPrepBadge(`${prep.progress.completed}/${prep.progress.applicable}`);
      }
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

  const bidCenter = (opportunity.full_info as Record<string, unknown> | undefined)?.bid_center as
    | { odoo_url?: string; odoo_tender_id?: number; odoo_tender_reference?: string }
    | undefined;
  const odooContinueUrl = bidCenter?.odoo_url;

  const docsCount = useMemo(() => {
    if (execBid?.found_documents != null) return execBid.found_documents;
    return null;
  }, [execBid]);

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

  function tabBadge(id: TabId): string | null {
    if (id === "documentos" && docsCount != null) return String(docsCount);
    if (id === "checklist" && execChecklist?.total) {
      const done = execChecklist.ready_count ?? execChecklist.compliant_count ?? 0;
      return `${done}/${execChecklist.total}`;
    }
    if (id === "tareas" && prepBadge) return prepBadge;
    if (id === "expediente" && processUpdatesPending > 0) return String(processUpdatesPending);
    return null;
  }

  return (
    <DgcpExpedienteContextProvider opportunityId={opportunity.id}>
      <div className="space-y-3 pb-16 md:pb-8">
        {activeTab === "adjudicaciones" && <ExpedienteContextStatusBanner />}

        <DgcpOpportunityWorkspaceHeader
          opportunity={opportunity}
          access={access}
          updating={updating}
          onAction={(a) => void applyAction(a)}
        />

        {odooContinueUrl ? (
          <div className="flex flex-wrap items-center gap-2 rounded-md border px-3 py-1.5 text-xs">
            <span>
              Bid Center
              {bidCenter?.odoo_tender_reference ? ` (${bidCenter.odoo_tender_reference})` : ""}
            </span>
            <a className="font-medium underline" href={odooContinueUrl} target="_blank" rel="noreferrer">
              Continuar en Odoo
            </a>
          </div>
        ) : null}

        {flash && (
          <p
            className={cn(
              "rounded-md border px-3 py-1.5 text-sm",
              flash.includes("No se puede") || flash.includes("Solo puede")
                ? "border-destructive/30 text-destructive"
                : "border-success/30 text-success",
            )}
          >
            {flash}
          </p>
        )}

        {/* Sticky expediente nav — sticky relative to AppShell <main> scroll */}
        <nav
          className={cn(
            "sticky top-0 z-20 -mx-1 border-b border-border/80 bg-background/95 px-1 backdrop-blur supports-[backdrop-filter]:bg-background/80",
          )}
          aria-label="Navegación del expediente"
        >
          <div className="flex gap-0.5 overflow-x-auto py-1.5 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {visibleTabs.map(({ id, label, icon: Icon }) => {
              const badge = tabBadge(id);
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => selectTab(id)}
                  className={cn(
                    "flex shrink-0 items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors sm:text-sm",
                    activeTab === id
                      ? "bg-primary/10 text-primary ring-1 ring-primary/25"
                      : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                  )}
                >
                  <Icon className="h-3.5 w-3.5 opacity-80" />
                  <span className="whitespace-nowrap">{label}</span>
                  {badge ? (
                    <span
                      className={cn(
                        "rounded-full px-1.5 py-0 text-[10px] tabular-nums",
                        id === "expediente" && processUpdatesPending > 0
                          ? "bg-destructive text-destructive-foreground"
                          : "bg-muted text-muted-foreground",
                      )}
                    >
                      {badge}
                    </span>
                  ) : null}
                </button>
              );
            })}
          </div>
        </nav>

        <div className="min-h-[40vh] pt-1">
          {activeTab === "resumen" && (
            <DgcpOpportunitySummaryTab
              opportunity={opportunity}
              onUpdated={setOpportunity}
              onNavigateTab={selectTab}
              docsCount={docsCount}
              checklistDone={execChecklist?.ready_count ?? execChecklist?.compliant_count ?? null}
              checklistTotal={execChecklist?.total ?? null}
            />
          )}

          {activeTab === "analisis-ia" && (
            <DgcpAnalisisIaTab
              opportunity={opportunity}
              execBid={execBid}
              execChecklist={execChecklist}
              execStatus={execStatus}
              onGoDocumentos={() => selectTab("documentos")}
              onAnalyzed={refreshAnalysisSnapshot}
            />
          )}

          <OpportunityBidSection
            opportunity={opportunity}
            activeTab={activeTab}
            interested={isDGCPOperationalInterest(opportunity.status)}
            autofillFormTypeHint={autofillFormTypeHint}
            onNavigateTab={(tab, opts) => {
              selectTab(resolveDgcpDetailTab(tab));
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
            <div className="space-y-4">
              <DGCPPrepPanel opportunityId={opportunity.id} />
              <Card>
                <CardHeader className="flex flex-row items-center justify-between py-3">
                  <CardTitle className="text-base">Tareas del work hub</CardTitle>
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
                    <p className="text-sm text-muted-foreground">
                      No hay tareas del work hub vinculadas a este proceso.
                    </p>
                  ) : (
                    <ul className="divide-y">
                      {tasks.map((t) => (
                        <li key={t.id} className="py-2">
                          <Link
                            href={`/tasks/${t.id}`}
                            className="text-sm font-medium text-primary hover:underline"
                          >
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
            </div>
          )}

          {activeTab === "adjudicaciones" && (
            <DGCPHistoricalAwardsPanel opportunity={opportunity} />
          )}

          {activeTab === "expediente" && history.length > 0 ? (
            <Card className="mt-4">
              <CardHeader className="py-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <History className="h-4 w-4 text-primary" />
                  Registro de acciones
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="max-h-56 space-y-3 overflow-y-auto">
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
                        <p className="mt-1 text-xs text-muted-foreground">
                          {STATUS_LABELS[entry.from_status as keyof typeof STATUS_LABELS] ??
                            entry.from_status}
                          {" → "}
                          {STATUS_LABELS[entry.to_status as keyof typeof STATUS_LABELS] ??
                            entry.to_status}
                        </p>
                      ) : null}
                      {entry.notes ? (
                        <p className="mt-1 text-xs text-muted-foreground">{entry.notes}</p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ) : null}
        </div>
      </div>
    </DgcpExpedienteContextProvider>
  );
}
