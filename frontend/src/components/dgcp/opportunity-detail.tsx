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
  Lightbulb,
  ListChecks,
  Package,
  PenLine,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { OpportunityBidSection } from "@/components/dgcp/opportunity-bid-section";
import { StatusBadge } from "@/components/dgcp/status-badge";
import { CreateTaskButton } from "@/components/work/create-task-button";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import { useAssistantContext } from "@/lib/assistant-context";
import {
  ACTION_LABELS,
  COMPANY_LABELS,
  formatCurrency,
  formatDate,
  formatDateTime,
  EXPEDIENTE_STATUS_LABELS,
  PRIORITY_LABELS,
  priorityColor,
  scoreColor,
  STATUS_LABELS,
  isDGCPOperationalInterest,
  type DGCPOpportunity,
  type DGCPOpportunityHistory,
  type OpportunityAction,
} from "@/lib/dgcp";
import type { Task } from "@/lib/tasks";
import { cn } from "@/lib/utils";

interface OpportunityDetailProps {
  opportunity: DGCPOpportunity;
}

const ACTIONS: OpportunityAction[] = ["mostrar_interes", "licitar", "revisar", "descartar", "ganada", "perdida"];

const TABS = [
  { id: "resumen", label: "Resumen", icon: Brain },
  { id: "requisitos", label: "Requisitos", icon: FileText },
  { id: "documentos-proceso", label: "Docs. Proceso", icon: FileStack },
  { id: "documentos", label: "Documentos Justech", icon: FileText },
  { id: "checklist", label: "Checklist", icon: ListChecks },
  { id: "alertas", label: "Alertas", icon: Bell },
  { id: "riesgos", label: "Riesgos", icon: AlertTriangle },
  { id: "autollenado", label: "Autollenado", icon: PenLine },
  { id: "expediente", label: "Expediente", icon: Package },
  { id: "tareas", label: "Tareas", icon: ClipboardList },
  { id: "historial", label: "Historial", icon: History },
] as const;

type TabId = (typeof TABS)[number]["id"];

export function OpportunityDetail({ opportunity: initial }: OpportunityDetailProps) {
  const [opportunity, setOpportunity] = useState(initial);
  const [history, setHistory] = useState<DGCPOpportunityHistory[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [activeTab, setActiveTab] = useState<TabId>("resumen");
  const [updating, setUpdating] = useState(false);
  const [execBid, setExecBid] = useState<import("@/lib/dgcp").DGCPBidPackage | null>(null);
  const [execChecklist, setExecChecklist] = useState<import("@/lib/dgcp").DGCPChecklist | null>(null);
  const [execStatus, setExecStatus] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const { setContext } = useAssistantContext();

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
    ]).then(([bid, checklist, status]) => {
      if (bid?.analyzed_at) setExecBid(bid);
      if (checklist?.total) setExecChecklist(checklist);
      if (status?.expediente_status) setExecStatus(status.expediente_status);
    });
  }, [opportunity.id, opportunity.status]);

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

  async function applyAction(action: OpportunityAction) {
    setUpdating(true);
    setFlash(null);
    try {
      const updated = await apiClient.applyDGCPAction(opportunity.id, action);
      setOpportunity(updated);
      const hist = await apiClient.getDGCPOpportunityHistory(opportunity.id);
      setHistory(hist);
      if (action === "mostrar_interes") {
        setFlash("Interés marcado — análisis, checklist y documentos habilitados.");
      } else if (action === "revisar" && opportunity.status === "interested") {
        setFlash("Interés descartado — la oportunidad volvió a revisión.");
      } else {
        setFlash(`${ACTION_LABELS[action]} — guardado.`);
      }
    } catch {
      setFlash("No se pudo aplicar la acción.");
    } finally {
      setUpdating(false);
    }
  }

  const showInterestCta =
    opportunity.status === "detected" || opportunity.status === "to_review";
  const interestMarked = opportunity.status === "interested";

  return (
    <div className="space-y-6">
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
          {showInterestCta && (
            <Button size="sm" disabled={updating} onClick={() => void applyAction("mostrar_interes")}>
              {ACTION_LABELS.mostrar_interes}
            </Button>
          )}
          {interestMarked && (
            <>
              <Badge variant="warning">Interés marcado</Badge>
              <Button
                size="sm"
                variant="outline"
                disabled={updating}
                onClick={() => void applyAction("revisar")}
              >
                Descartar interés
              </Button>
            </>
          )}
          <Badge variant="muted">{COMPANY_LABELS[opportunity.company]}</Badge>
          {opportunity.confidence_score > 0 && (
            <Badge variant="outline">{opportunity.confidence_score}% confianza</Badge>
          )}
          <StatusBadge status={opportunity.status} />
        </div>
      </div>

      {flash && (
        <p className="text-sm text-success rounded-lg border border-success/30 px-3 py-2">
          {flash}
        </p>
      )}

      {execBid && execChecklist && isDGCPOperationalInterest(opportunity.status) && (
        <Card className="border-primary/25 bg-primary/5">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Estado de la licitación</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              <SummaryMetric label="Requisitos detectados" value={execChecklist.total} />
              <SummaryMetric label="Cumplidos" value={execChecklist.compliant_count ?? execChecklist.ready_count} />
              <SummaryMetric
                label="Pendientes"
                value={
                  (execChecklist.incomplete_count ?? 0) +
                  (execChecklist.review_count ?? 0) +
                  (execChecklist.expired_count ?? 0)
                }
              />
              <SummaryMetric label="Faltantes" value={execChecklist.pending_count} />
              <SummaryMetric label="Revisión requerida" value={execChecklist.review_count ?? 0} />
              <SummaryMetric label="Vencidos" value={execChecklist.expired_count} />
              <SummaryMetric
                label="Preparación"
                value={`${execBid.preparation_pct.toFixed(0)}%`}
                highlight
              />
              <SummaryMetric
                label="Estado"
                value={EXPEDIENTE_STATUS_LABELS[execStatus ?? "sin_preparar"] ?? "Sin preparar"}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              {execChecklist.compliant_count ?? execChecklist.ready_count}/
              {execChecklist.mandatory_total ?? execChecklist.total} requisitos obligatorios cumplidos — el
              porcentaje se calcula solo contra requisitos extraídos del proceso, no contra documentos
              encontrados.
            </p>
          </CardContent>
        </Card>
      )}

      <div className="flex flex-wrap gap-1 border-b border-border pb-1 overflow-x-auto">
        {TABS.map(({ id, label, icon: Icon }) => (
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
          </button>
        ))}
      </div>

      {activeTab === "resumen" && (
        <ResumenTab
          opportunity={opportunity}
          updating={updating}
          onAction={applyAction}
          execBid={execBid}
          execChecklist={execChecklist}
          execStatus={execStatus}
        />
      )}

      <OpportunityBidSection
        opportunity={opportunity}
        activeTab={activeTab}
        interested={isDGCPOperationalInterest(opportunity.status)}
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
              <p className="text-sm text-muted-foreground">Sin acciones registradas.</p>
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
  );
}

function ResumenTab({
  opportunity,
  updating,
  onAction,
  execBid,
  execChecklist,
  execStatus,
}: {
  opportunity: DGCPOpportunity;
  updating: boolean;
  onAction: (a: OpportunityAction) => void;
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
      {execBid && execChecklist && (
        <Card className={notReady ? "border-warning/30 bg-warning/10" : "border-success/30 bg-success/10"}>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Estado del expediente</CardTitle>
          </CardHeader>
          <CardContent className="text-sm space-y-2">
            <p className="font-medium">
              {EXPEDIENTE_STATUS_LABELS[execStatus ?? "sin_preparar"] ?? "Sin preparar"} —{" "}
              {execBid.preparation_pct.toFixed(0)}% preparación
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
            Pulse <strong>Mostrar interés</strong> para habilitar análisis profundo, documentos del
            proceso, checklist operativo, validaciones, notas y tareas de esta licitación.
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
          {opportunity.classification_reason}
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

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <MetricCard label="Monto" value={formatCurrency(opportunity.amount, opportunity.currency)} />
        <MetricCard
          label="Potencial"
          value={formatCurrency(opportunity.justech_potential_amount)}
          className="text-primary"
        />
        <MetricCard label="Probabilidad" value={`${opportunity.probability}%`} />
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
              {opportunity.ai_recommendations.map((rec, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                  {rec}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      <Card className="border-primary/30 bg-primary/5">
        <CardHeader>
          <CardTitle className="text-base">Acciones</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {(opportunity.status === "detected" || opportunity.status === "to_review") && (
            <Button size="sm" disabled={updating} onClick={() => onAction("mostrar_interes")}>
              {ACTION_LABELS.mostrar_interes}
            </Button>
          )}
          {ACTIONS.filter(
            (action) =>
              action !== "mostrar_interes" &&
              (action !== "licitar" || isDGCPOperationalInterest(opportunity.status)),
          ).map((action) => (
            <Button
              key={action}
              size="sm"
              variant={action === "descartar" || action === "perdida" ? "outline" : "default"}
              disabled={updating}
              onClick={() => onAction(action)}
            >
              {ACTION_LABELS[action]}
            </Button>
          ))}
        </CardContent>
      </Card>
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
