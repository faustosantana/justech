"use client";

import {
  AlertTriangle,
  ArrowLeft,
  Bell,
  Brain,
  ClipboardList,
  ExternalLink,
  FileStack,
  FileText,
  History,
  Landmark,
  Lightbulb,
  ListChecks,
  Loader2,
  Package,
  PenLine,
  ShoppingCart,
  Wrench,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { DgcpCommercialOdooPanel } from "@/components/dgcp/dgcp-commercial-odoo-panel";
import {
  DgcpExpedienteContextProvider,
  ExpedienteContextStatusBanner,
} from "@/components/dgcp/dgcp-expediente-context";
import { DGCPHistoricalAwardsPanel } from "@/components/dgcp/dgcp-historical-awards-panel";
import { DGCPIntelligencePanel } from "@/components/dgcp/dgcp-intelligence-panel";
import { OpportunityBidSection } from "@/components/dgcp/opportunity-bid-section";
import { DgcpFunnelHeader } from "@/components/dgcp/dgcp-funnel-header";
import { CreateTaskButton } from "@/components/work/create-task-button";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import { applyDGCPOpportunityAction } from "@/lib/dgcp-apply-action";
import { useAssistantContext } from "@/lib/assistant-context";
import { usePlatformAccess } from "@/hooks/use-platform-access";
import {
  ACTION_LABELS,
  STATUS_LABELS,
  COMPANY_LABELS,
  formatCurrency,
  formatDate,
  formatDateTime,
  EXPEDIENTE_STATUS_LABELS,
  PRIORITY_LABELS,
  sanitizeClassificationReason,
  priorityColor,
  scoreColor,
  isDGCPOperationalInterest,
  hasJaiosIntelligence,
  type DGCPOpportunity,
  type DGCPOpportunityHistory,
  type OpportunityAction,
} from "@/lib/dgcp";
import type { Task } from "@/lib/tasks";
import { cn } from "@/lib/utils";
import { dgcpAutofillPrimaryTabEnabled, dgcpProcessUpdatesEnabled, dgcpTechSheetsEnabled } from "@/lib/dgcp-feature-flags";

interface OpportunityDetailProps {
  opportunity: DGCPOpportunity;
}

const BASE_TABS = [
  { id: "resumen", label: "Resumen", icon: Brain },
  { id: "requisitos", label: "Requisitos", icon: FileText },
  { id: "documentos-proceso", label: "Docs. Proceso", icon: FileStack },
  { id: "documentos", label: "Documentos Justech", icon: FileText },
  { id: "checklist", label: "Checklist", icon: ListChecks },
  { id: "alertas", label: "Alertas", icon: Bell },
  { id: "riesgos", label: "Riesgos", icon: AlertTriangle },
  { id: "autollenado", label: "Autollenado", icon: PenLine, secondaryOnly: true },
  ...(dgcpTechSheetsEnabled()
    ? [{ id: "fichas-tecnicas" as const, label: "Fichas Técnicas", icon: Wrench }]
    : []),
  { id: "expediente", label: "Expediente", icon: Package },
  { id: "tareas", label: "Tareas", icon: ClipboardList },
  { id: "historico", label: "Adjudicaciones", icon: Landmark },
  { id: "comercial", label: "Comercial Odoo", icon: ShoppingCart },
  { id: "historial", label: "Registro", icon: History },
] as const;

function buildVisibleTabs() {
  const showAutofillPrimary = dgcpAutofillPrimaryTabEnabled();
  return BASE_TABS.filter((t) => !("secondaryOnly" in t && t.secondaryOnly) || showAutofillPrimary);
}

type TabId = (typeof BASE_TABS)[number]["id"];

export function OpportunityDetail({ opportunity: initial }: OpportunityDetailProps) {
  const searchParams = useSearchParams();
  const visibleTabs = buildVisibleTabs();
  const autofillSecondary = !dgcpAutofillPrimaryTabEnabled();
  const [opportunity, setOpportunity] = useState(initial);
  const { access } = usePlatformAccess();
  const [history, setHistory] = useState<DGCPOpportunityHistory[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [activeTab, setActiveTab] = useState<TabId>("resumen");
  const [autofillFormTypeHint, setAutofillFormTypeHint] = useState<string | undefined>();
  const [updating, setUpdating] = useState(false);
  const [execBid, setExecBid] = useState<import("@/lib/dgcp").DGCPBidPackage | null>(null);
  const [execChecklist, setExecChecklist] = useState<import("@/lib/dgcp").DGCPChecklist | null>(null);
  const [execStatus, setExecStatus] = useState<string | null>(null);
  const [processUpdatesPending, setProcessUpdatesPending] = useState(0);
  const [analysisJob, setAnalysisJob] = useState<import("@/lib/dgcp").DGCPAnalysisJob | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const { setContext } = useAssistantContext();

  const handleIntelligenceUpdated = useCallback((intel: import("@/lib/dgcp").DGCPIntelligence) => {
    setOpportunity((prev) => ({
      ...prev,
      jaios_intelligence: intel,
      score: intel.premium_score,
    }));
  }, []);

  useEffect(() => {
    const tabParam = searchParams.get("tab");
    if (tabParam && BASE_TABS.some((t) => t.id === tabParam)) {
      setActiveTab(tabParam as TabId);
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
      setProcessUpdatesPending(updates?.meta.pending_count ?? 0);
    });
    (apiClient.getDGCPAnalysisStatus ? apiClient.getDGCPAnalysisStatus(opportunity.id) : Promise.resolve({ job: null })).then((s) => {
      if (s.job?.status === "in_progress") setAnalysisJob(s.job);
      else setAnalysisJob(null);
    }).catch(() => {});
  }, [opportunity.id, opportunity.status]);

  useEffect(() => {
    if (!analysisJob || analysisJob.status !== "in_progress") return;
    const timer = window.setInterval(() => {
      void (apiClient.getDGCPAnalysisStatus ? apiClient.getDGCPAnalysisStatus(opportunity.id) : Promise.resolve({ job: null })).then(async (s) => {
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
      }).catch(() => {});
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
        .then((r) =>
          setTasks(r.items.filter((t) => t.dgcp_process_id === opportunity.id)),
        )
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
      {(activeTab === "historico" || activeTab === "comercial") && <ExpedienteContextStatusBanner />}
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
        </div>
      </div>

      {odooContinueUrl ? (
        <div className="mb-4 flex flex-wrap items-center gap-3 rounded-md border p-3">
          <span className="text-sm">Expediente en Odoo Bid Center{bidCenter?.odoo_tender_reference ? ` (${bidCenter.odoo_tender_reference})` : ""}.</span>
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
        {autofillSecondary && (
          <button
            type="button"
            onClick={() => setActiveTab("autollenado")}
            className={cn(
              "flex items-center gap-1.5 rounded-t-lg px-3 py-2 text-sm font-medium transition-colors whitespace-nowrap ml-auto sm:ml-0",
              activeTab === "autollenado"
                ? "bg-muted text-foreground border-b-2 border-muted-foreground/40"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/50",
            )}
            title="Formularios y borradores generados (acceso secundario)"
          >
            <PenLine className="h-3.5 w-3.5" />
            Formularios
          </button>
        )}
      </div>

      {activeTab === "resumen" && (
        <>
          <DGCPIntelligencePanel
            opportunityId={opportunity.id}
            initial={hasJaiosIntelligence(opportunity.jaios_intelligence) ? opportunity.jaios_intelligence : null}
            onUpdated={handleIntelligenceUpdated}
          />
          <ResumenTab
            opportunity={opportunity}
            execBid={execBid}
            execChecklist={execChecklist}
            execStatus={execStatus}
          />
        </>
      )}

      <OpportunityBidSection
        opportunity={opportunity}
        activeTab={activeTab}
        interested={isDGCPOperationalInterest(opportunity.status)}
        autofillFormTypeHint={autofillFormTypeHint}
        onNavigateTab={(tab, opts) => {
          setActiveTab(tab as TabId);
          if (opts?.formType) setAutofillFormTypeHint(opts.formType);
        }}
        onOpportunityUpdated={setOpportunity}
        onAnalysisUpdate={(bid, checklist, status) => {
          setExecBid(bid);
          setExecChecklist(checklist);
          setExecStatus(status);
        }}
      />

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
                    <p className="text-xs text-muted-foreground">{t.status} · {t.priority}</p>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === "historico" && <DGCPHistoricalAwardsPanel opportunity={opportunity} />}

      {activeTab === "comercial" && <DgcpCommercialOdooPanel />}

      {activeTab === "historial" && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <History className="h-4 w-4 text-primary" />
              Historial de acciones
            </CardTitle>
          </CardHeader>
          <CardContent>
            {history.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Sin acciones registradas. Los cambios de estado y análisis aparecerán aquí automáticamente.
              </p>
            ) : (
              <ul className="space-y-3">
                {history.map((entry) => (
                  <li key={entry.id} className="rounded-lg border border-border/50 p-3 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium capitalize">
                        {ACTION_LABELS[entry.action as OpportunityAction] ?? entry.action}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {formatDateTime(entry.created_at)}
                      </span>
                    </div>
                    {entry.from_status && entry.to_status && (
                      <p className="text-xs text-muted-foreground mt-1">
                        {STATUS_LABELS[entry.from_status as keyof typeof STATUS_LABELS] ?? entry.from_status}
                        {" → "}
                        {STATUS_LABELS[entry.to_status as keyof typeof STATUS_LABELS] ?? entry.to_status}
                      </p>
                    )}
                    {entry.notes && (
                      <p className="text-xs text-muted-foreground mt-1">{entry.notes}</p>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}
    </div>
    </DgcpExpedienteContextProvider>
  );
}


function IntelligenceSummaryCards({ opportunity }: { opportunity: DGCPOpportunity }) {
  const intel = hasJaiosIntelligence(opportunity.jaios_intelligence)
    ? opportunity.jaios_intelligence
    : null;
  const exec = intel?.executive;
  const missing = (intel?.expediente?.missing as string[] | undefined)
    || (exec?.questions?.missing_documents?.answer as string[] | undefined)
    || [];
  const nextActions = exec?.next_actions || opportunity.ai_recommendations || [];
  const risks = (exec?.risks && exec.risks.length
    ? exec.risks.map((r) => (typeof r === "string" ? r : String(r)))
    : (opportunity.risks || []).map((r) => (typeof r === "string" ? r : r.descripcion || JSON.stringify(r))));

  if (!intel && nextActions.length === 0 && risks.length === 0 && missing.length === 0) {
    return (
      <Card>
        <CardContent className="py-4 text-sm text-muted-foreground">
          Sin análisis de pliego todavía. En Requisitos o Docs. Proceso, ejecute «Analizar pliego con IA».
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {exec?.summary && (
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">Resumen ejecutivo del pliego</CardTitle></CardHeader>
          <CardContent className="text-sm space-y-2">
            <p>{exec.summary}</p>
            {exec.recommendation && (
              <p className="text-xs text-muted-foreground">
                Decisión sugerida: <strong>{exec.recommendation}</strong>
                {exec.recommendation_reason ? ` — ${exec.recommendation_reason}` : ""}
                {intel?.premium_score != null ? ` · Confianza/score ${intel.premium_score}/100` : ""}
              </p>
            )}
          </CardContent>
        </Card>
      )}
      {missing.length > 0 && (
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">Documentos solicitados / pendientes</CardTitle></CardHeader>
          <CardContent>
            <ul className="space-y-1 text-sm">
              {missing.slice(0, 20).map((m, i) => (
                <li key={`${m}-${i}`} className="rounded border px-3 py-1.5 flex justify-between gap-2">
                  <span>{m}</span>
                  <span className="text-xs text-amber-600">Pendiente</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
      {nextActions.length > 0 && (
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">Recomendaciones accionables</CardTitle></CardHeader>
          <CardContent>
            <ul className="list-disc pl-5 space-y-1 text-sm">
              {nextActions.slice(0, 12).map((a, i) => (
                <li key={i}>{typeof a === "string" ? a : JSON.stringify(a)}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
      {risks.length > 0 && (
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">Riesgos</CardTitle></CardHeader>
          <CardContent>
            <ul className="space-y-1 text-sm">
              {risks.slice(0, 12).map((r, i) => (
                <li key={i} className="rounded border px-3 py-1.5">{r}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function ResumenTab({
  opportunity,
  execBid,
  execChecklist,
  execStatus,
}: {
  opportunity: DGCPOpportunity;
  execBid: import("@/lib/dgcp").DGCPBidPackage | null;
  execChecklist: import("@/lib/dgcp").DGCPChecklist | null;
  execStatus: string | null;
}) {
  const notReady =
    execChecklist &&
    execBid &&
    (execChecklist.pending_count > 0 ||
      execChecklist.incomplete_count > 0 ||
      (execChecklist.review_count ?? 0) > 0 ||
      execChecklist.expired_count > 0 ||
      (execChecklist.unanalyzed_count ?? 0) > 0);

  return (
    <>
      <IntelligenceSummaryCards opportunity={opportunity} />

      {execBid && execChecklist && (
        <Card className={notReady ? "border-warning/30 bg-warning/10" : "border-success/30 bg-success/10"}>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Preparación del expediente</CardTitle>
          </CardHeader>
          <CardContent className="text-sm space-y-2">
            <p className="font-medium">
              {EXPEDIENTE_STATUS_LABELS[execStatus ?? "sin_preparar"] ?? "Sin preparar"} — avance por
              áreas {(execBid.area_preparation_pct ?? 0).toFixed(1)}% · checklist{" "}
              {execChecklist.compliant_count ?? execChecklist.ready_count}/
              {execChecklist.mandatory_total ?? execChecklist.total}
            </p>
            {notReady ? (
              <p className="text-muted-foreground">
                Esta licitación NO está lista para presentar. Hay {execChecklist.pending_count} faltante(s),{" "}
                {execChecklist.incomplete_count} formulario(s) por completar y{" "}
                {(execChecklist.review_count ?? 0) + (execChecklist.unanalyzed_count ?? 0)} documento(s) sin
                vigencia verificada o pendientes de análisis.
              </p>
            ) : (
              <p className="text-muted-foreground">
                Requisitos cumplidos: {execChecklist.compliant_count ?? execChecklist.ready_count}/
                {execChecklist.mandatory_total ?? execChecklist.total}. Revise checklist antes de presentar.
              </p>
            )}
            {execBid.recommended_tasks.length > 0 && (
              <ul className="list-disc pl-5 text-xs text-muted-foreground">
                {execBid.recommended_tasks.map((t) => (
                  <li key={t}>{t}</li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}
      {!isDGCPOperationalInterest(opportunity.status) && (
        <Card className="border-warning/30 bg-amber-500/10">
          <CardContent className="py-4 text-sm">
            Use el botón <strong>Marcar interés</strong> en la cabecera para habilitar análisis, checklist y
            expediente.
          </CardContent>
        </Card>
      )}
      <div className="flex flex-wrap gap-2">
        {isDGCPOperationalInterest(opportunity.status) && (
          <>
            <CreateTaskButton
              eventType="licitacion"
              title={`Revisar licitación ${opportunity.code}`}
              description={opportunity.title}
              dgcpProcessId={opportunity.id}
              source="dgcp_opportunity"
              label="Crear tarea de revisión"
            />
            <CreateTaskButton
              eventType="licitacion"
              title={`Preparar licitación ${opportunity.code}`}
              description={`Preparar oferta: ${opportunity.title}`}
              dgcpProcessId={opportunity.id}
              source="dgcp_opportunity"
              label="Crear tarea para preparar licitación"
            />
          </>
        )}
      </div>

      {opportunity.classification_reason && (
        <p className="text-sm text-muted-foreground rounded-lg border border-border/50 p-3">
          <span className="font-medium text-foreground">Clasificación: </span>
          {sanitizeClassificationReason(opportunity.classification_reason)}
        </p>
      )}

      {opportunity.source_url && (
        <Button variant="outline" size="sm" asChild>
          <a href={opportunity.source_url} target="_blank" rel="noopener noreferrer">
            <ExternalLink className="mr-2 h-4 w-4" />
            Ver en DGCP
          </a>
        </Button>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <MetricCard label="Monto" value={formatCurrency(opportunity.amount, opportunity.currency)} />
        <MetricCard
          label="Score IA"
          value={String(opportunity.score)}
          className={scoreColor(opportunity.score)}
        />
        <MetricCard
          label="Prioridad"
          value={PRIORITY_LABELS[opportunity.priority]}
          className={priorityColor(opportunity.priority)}
        />
      </div>

      {opportunity.description && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Descripción</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground leading-relaxed">
            {opportunity.description}
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Brain className="h-4 w-4 text-primary" />
              Datos DGCP
            </CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="space-y-2 text-sm">
              {[
                ["Modalidad", opportunity.modalidad],
                ["Objeto", opportunity.objeto_proceso],
                ["Estado DGCP", opportunity.dgcp_status],
                ["Fecha límite", formatDate(opportunity.deadline)],
                ["Sincronizado", opportunity.synced_at ? formatDateTime(opportunity.synced_at) : "—"],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between gap-4 border-b border-border/50 py-2">
                  <dt className="text-muted-foreground">{label}</dt>
                  <dd className="font-medium text-right">{value ?? "—"}</dd>
                </div>
              ))}
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Lightbulb className="h-4 w-4 text-primary" />
              Recomendaciones IA
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {opportunity.ai_recommendations?.length ? (
                opportunity.ai_recommendations.map((rec, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                    {rec}
                  </li>
                ))
              ) : (
                <li className="text-sm text-muted-foreground">
                  Sin recomendaciones aún. Marque interés y ejecute el análisis de requisitos para obtener sugerencias IA.
                </li>
              )}
            </ul>
          </CardContent>
        </Card>
      </div>
    </>
  );
}

function MetricCard({
  label,
  value,
  className = "",
}: {
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-xs text-muted-foreground">{label}</CardTitle>
      </CardHeader>
      <CardContent className={`text-xl font-bold tabular-nums ${className}`}>{value}</CardContent>
    </Card>
  );
}

function SummaryMetric({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: string | number;
  highlight?: boolean;
}) {
  return (
    <div className="rounded-lg border bg-background/80 px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={cn("text-lg font-semibold tabular-nums", highlight && "text-primary")}>{value}</p>
    </div>
  );
}
