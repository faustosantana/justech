"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Eye,
  FileSpreadsheet,
  FileText,
  Loader2,
  MessageSquare,
  ShieldCheck,
  UserRound,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api";
import type {
  DGCPComplianceMatrix,
  DGCPExpedienteDashboard,
  DGCPExpedienteFinalValidation,
  DGCPExpedientePreview,
  DGCPExpedienteScore,
  DGCPRequirementEvidenceDetail,
} from "@/lib/dgcp";
import { cn } from "@/lib/utils";


function userFacingError(err: unknown, fallback: string): string {
  const raw = err instanceof Error ? err.message : "";
  if (!raw || raw === "UNAUTHORIZED") return fallback;
  const technical =
    /is not a function|TypeError|undefined is not|Cannot read|ECONN|NetworkError|stack|at Object\.|\.tsx?:\d+/i.test(
      raw,
    ) || /^[a-zA-Z0-9_.$]+\.[a-zA-Z0-9_.$]+/.test(raw);
  if (technical) return fallback;
  if (raw.length > 240 || raw.includes("\n")) return fallback;
  return raw;
}

interface Props {
  opportunityId: string;
  refreshKey?: number;
  onValidated?: (result: DGCPExpedienteFinalValidation) => void;
  onChanged?: () => void;
}

export function ExpedienteDashboard({
  opportunityId,
  refreshKey = 0,
  onValidated,
  onChanged,
}: Props) {
  const [data, setData] = useState<DGCPExpedienteDashboard | null>(null);
  const [matrix, setMatrix] = useState<DGCPComplianceMatrix | null>(null);
  const [score, setScore] = useState<DGCPExpedienteScore | null>(null);
  const [preview, setPreview] = useState<DGCPExpedientePreview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [validating, setValidating] = useState(false);
  const [validation, setValidation] = useState<DGCPExpedienteFinalValidation | null>(null);
  const [assignDraft, setAssignDraft] = useState<Record<string, string>>({});
  const [commentDraft, setCommentDraft] = useState<Record<string, string>>({});
  const [askDraft, setAskDraft] = useState<Record<string, string>>({});
  const [askAnswer, setAskAnswer] = useState<Record<string, string>>({});
  const [evidence, setEvidence] = useState<DGCPRequirementEvidenceDetail | null>(null);
  const [busyItem, setBusyItem] = useState<string | null>(null);
  const [exportBusy, setExportBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dash, mat, sc, prev] = await Promise.all([
        apiClient.getDGCPExpedienteDashboard(opportunityId),
        apiClient.getDGCPComplianceMatrix(opportunityId).catch(() => null),
        apiClient.getDGCPExpedienteScore(opportunityId).catch(() => null),
        apiClient.getDGCPExpedientePreview(opportunityId).catch(() => null),
      ]);
      setData(dash);
      setMatrix(mat);
      setScore(sc ?? dash.score ?? null);
      setPreview(prev);
      if (dash.validacion_preview) setValidation(dash.validacion_preview);
    } catch (err) {
      setData(null);
      console.error("[ExpedienteDashboard] load failed", err);
      setError(userFacingError(err, "No se pudo cargar el centro de trabajo del expediente."));
    } finally {
      setLoading(false);
    }
  }, [opportunityId]);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  async function handleValidate() {
    setValidating(true);
    try {
      const result = await apiClient.validateDGCPExpedienteFinal(opportunityId);
      setValidation(result);
      onValidated?.(result);
      await load();
    } catch (err) {
      console.error("[ExpedienteDashboard] validate", err); setError(userFacingError(err, "No se pudo validar el expediente."));
    } finally {
      setValidating(false);
    }
  }

  async function handleAssign(itemId: string) {
    const name = (assignDraft[itemId] || "").trim();
    if (!name) return;
    setBusyItem(itemId);
    try {
      await apiClient.assignDGCPChecklistItem(opportunityId, itemId, name);
      setAssignDraft((d) => ({ ...d, [itemId]: "" }));
      onChanged?.();
      await load();
    } catch (err) {
      console.error("[ExpedienteDashboard] assign", err); setError(userFacingError(err, "No se pudo asignar el responsable."));
    } finally {
      setBusyItem(null);
    }
  }

  async function handleComment(itemId: string) {
    const note = (commentDraft[itemId] || "").trim();
    if (!note) return;
    setBusyItem(itemId);
    try {
      await apiClient.addDGCPChecklistNote(opportunityId, itemId, note);
      setCommentDraft((d) => ({ ...d, [itemId]: "" }));
      onChanged?.();
      await load();
    } catch (err) {
      console.error("[ExpedienteDashboard] comment", err); setError(userFacingError(err, "No se pudo guardar el comentario."));
    } finally {
      setBusyItem(null);
    }
  }

  async function handleEvidence(itemId: string) {
    setBusyItem(itemId);
    try {
      const ev = await apiClient.getDGCPRequirementEvidence(opportunityId, itemId);
      setEvidence(ev);
    } catch (err) {
      console.error("[ExpedienteDashboard] evidence", err); setError(userFacingError(err, "No se pudo cargar la evidencia."));
    } finally {
      setBusyItem(null);
    }
  }

  async function handleAsk(itemId: string) {
    const q = (askDraft[itemId] || "").trim() || "¿Cuál es el estado y qué falta para este requisito?";
    setBusyItem(itemId);
    try {
      const res = await apiClient.askDGCPRequirementAI(opportunityId, itemId, q);
      setAskAnswer((d) => ({ ...d, [itemId]: res.answer }));
    } catch (err) {
      console.error("[ExpedienteDashboard] ask", err); setError(userFacingError(err, "No se pudo consultar a la IA."));
    } finally {
      setBusyItem(null);
    }
  }

  async function exportMatrix(kind: "excel" | "pdf") {
    setExportBusy(true);
    try {
      if (kind === "excel") await apiClient.downloadDGCPComplianceMatrixExcel(opportunityId);
      else await apiClient.downloadDGCPComplianceMatrixPdf(opportunityId);
    } catch (err) {
      console.error("[ExpedienteDashboard] export", err); setError(userFacingError(err, "No se pudo exportar la matriz."));
    } finally {
      setExportBusy(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground py-6">
        <Loader2 className="h-4 w-4 animate-spin" />
        Cargando centro de trabajo del expediente…
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-md border border-amber-200 bg-amber-50/80 px-3 py-3 text-sm text-amber-950">
        <p className="font-medium">{error ? "No pudimos cargar el expediente" : "Expediente sin datos aún"}</p>
        <p className="mt-1 text-amber-900/80">
          {error ?? "Marque «Mostrar interés» e inicie el análisis de requisitos para generar el centro de trabajo."}
        </p>
        <Button size="sm" variant="outline" className="mt-2" onClick={() => void load()}>
          Reintentar
        </Button>
      </div>
    );
  }

  const p = data.progreso ?? {
    total_requisitos: data.kpis.total_requisitos,
    completados: data.kpis.documentos_aprobados,
    pendientes: data.kpis.requisitos_pendientes,
    en_revision: data.kpis.en_revision ?? 0,
    riesgos_criticos: data.kpis.riesgos_criticos ?? data.kpis.alertas_criticas,
    porcentaje_real: data.kpis.porcentaje_completado,
  };
  const ia = data.ia_proactiva;
  const requisitos = data.requisitos || [];
  const scoreTotal = score?.score_total ?? data.preparation_pct;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Centro de trabajo</p>
          <p className="text-lg font-semibold">{data.opportunity_code}</p>
        </div>
        <Button onClick={() => void handleValidate()} disabled={validating}>
          {validating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ShieldCheck className="mr-2 h-4 w-4" />}
          Validar Expediente
        </Button>
      </div>

      <Card className="border-primary/30 bg-primary/5">
        <CardContent className="flex flex-wrap items-end gap-6 py-4">
          <div>
            <p className="text-xs uppercase text-muted-foreground">Score del expediente</p>
            <p className="text-5xl font-bold tabular-nums text-primary">{Number(scoreTotal || 0).toFixed(0)}%</p>
          </div>
          <div className="grid flex-1 gap-2 sm:grid-cols-2 lg:grid-cols-3 text-sm">
            {(score?.desglose ?? []).map((a) => (
              <div key={a.key} className="rounded border bg-background/70 px-2 py-1">
                <p className="text-xs text-muted-foreground">{a.label}</p>
                <p className="font-semibold tabular-nums">
                  {a.pct == null ? "—" : `${a.pct.toFixed(0)}%`}
                </p>
              </div>
            ))}
          </div>
          {score?.explicacion && (
            <p className="w-full text-sm text-muted-foreground">{score.explicacion}</p>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <Kpi label="Total requisitos" value={p.total_requisitos} />
        <Kpi label="Completados" value={p.completados} icon={<CheckCircle2 className="h-3.5 w-3.5" />} tone="ok" />
        <Kpi label="Pendientes" value={p.pendientes} icon={<Clock3 className="h-3.5 w-3.5" />} tone="warn" />
        <Kpi label="En revisión" value={p.en_revision} />
        <Kpi
          label="Riesgos críticos"
          value={p.riesgos_criticos}
          icon={<AlertTriangle className="h-3.5 w-3.5" />}
          tone={p.riesgos_criticos > 0 ? "bad" : undefined}
        />
        <Kpi label="% real" value={`${Number(p.porcentaje_real || 0).toFixed(0)}%`} tone="primary" />
      </div>

      {(validation || data.validacion_preview) && (
        <Card
          className={cn(
            "border",
            (validation ?? data.validacion_preview)?.listo_para_presentar
              ? "border-emerald-500/40 bg-emerald-500/5"
              : "border-amber-500/40 bg-amber-500/5",
          )}
        >
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              {(validation ?? data.validacion_preview)?.listo_para_presentar ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              ) : (
                <XCircle className="h-4 w-4 text-amber-600" />
              )}
              {(validation ?? data.validacion_preview)?.estado}
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            <p>{(validation ?? data.validacion_preview)?.explicacion}</p>
          </CardContent>
        </Card>
      )}

      {ia && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">IA proactiva</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <ul className="list-disc pl-4 space-y-1">
              {ia.recomendaciones.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-2 flex flex-row items-center justify-between gap-2">
          <CardTitle className="text-sm font-medium">Matriz de cumplimiento</CardTitle>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" disabled={exportBusy} onClick={() => void exportMatrix("excel")}>
              <FileSpreadsheet className="mr-1 h-3.5 w-3.5" />
              Excel
            </Button>
            <Button size="sm" variant="outline" disabled={exportBusy} onClick={() => void exportMatrix("pdf")}>
              <FileText className="mr-1 h-3.5 w-3.5" />
              PDF
            </Button>
          </div>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full min-w-[800px] text-left text-xs">
            <thead>
              <tr className="border-b text-muted-foreground">
                {(matrix?.columns ?? [
                  "Requisito",
                  "Estado",
                  "Responsable",
                  "Documento asociado",
                  "Cumple",
                  "Riesgo",
                  "Observaciones IA",
                ]).map((c) => (
                  <th key={c} className="py-2 pr-3 font-medium">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(matrix?.rows ?? []).slice(0, 40).map((row) => (
                <tr key={row.id} className="border-b last:border-0 align-top">
                  <td className="py-2 pr-3 font-medium">{row.requisito}</td>
                  <td className="py-2 pr-3">{row.estado}</td>
                  <td className="py-2 pr-3">{row.responsable}</td>
                  <td className="py-2 pr-3">{row.documento_asociado}</td>
                  <td className="py-2 pr-3">{row.cumple}</td>
                  <td className="py-2 pr-3">{row.riesgo}</td>
                  <td className="py-2 pr-3 text-muted-foreground">{row.observaciones_ia}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!matrix?.rows?.length && (
            <p className="text-sm text-muted-foreground">Sin filas de matriz todavía.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Requisitos — trazabilidad, responsables e IA</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {requisitos.slice(0, 25).map((item) => {
            const id = String(item.id ?? "");
            return (
              <div key={id || String(item.requirement_key)} className="rounded-md border p-3 space-y-2">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="font-medium text-sm">{String(item.nombre ?? item.requirement ?? "—")}</p>
                    <p className="text-xs text-muted-foreground">
                      {String(item.obligatoriedad ?? "")}
                      {item.documento_asociado ? ` · ${String(item.documento_asociado)}` : ""}
                    </p>
                  </div>
                  <Badge variant="outline">{String(item.estado ?? item.ux_status ?? item.status ?? "—")}</Badge>
                </div>
                <div className="grid gap-2 sm:grid-cols-3 text-xs text-muted-foreground">
                  <p className="flex items-center gap-1">
                    <UserRound className="h-3 w-3" />
                    Resp: {String(item.responsable ?? item.assignee ?? "Sin asignar")}
                  </p>
                  <p>Límite: {String(item.fecha_limite ?? "—")}</p>
                  <p>Última mod.: {formatTs(String(item.ultima_modificacion ?? ""))}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="outline" disabled={!id || busyItem === id} onClick={() => void handleEvidence(id)}>
                    <Eye className="mr-1 h-3.5 w-3.5" />
                    Ver evidencia
                  </Button>
                  <Input
                    className="h-8 min-w-[180px] flex-1"
                    placeholder="Preguntar a la IA sobre este requisito…"
                    value={askDraft[id] ?? ""}
                    onChange={(e) => setAskDraft((d) => ({ ...d, [id]: e.target.value }))}
                  />
                  <Button size="sm" variant="secondary" disabled={!id || busyItem === id} onClick={() => void handleAsk(id)}>
                    <MessageSquare className="mr-1 h-3.5 w-3.5" />
                    Preguntar a la IA
                  </Button>
                </div>
                {askAnswer[id] && (
                  <p className="text-xs rounded bg-muted/50 px-2 py-2">{askAnswer[id]}</p>
                )}
                <div className="flex flex-wrap gap-2">
                  <Input
                    className="h-8 max-w-[180px]"
                    placeholder="Responsable"
                    value={assignDraft[id] ?? ""}
                    onChange={(e) => setAssignDraft((d) => ({ ...d, [id]: e.target.value }))}
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={!id || busyItem === id || !(assignDraft[id] || "").trim()}
                    onClick={() => void handleAssign(id)}
                  >
                    Asignar
                  </Button>
                  <Input
                    className="h-8 min-w-[200px] flex-1"
                    placeholder='Comentario (ej. "Falta firma.")'
                    value={commentDraft[id] ?? ""}
                    onChange={(e) => setCommentDraft((d) => ({ ...d, [id]: e.target.value }))}
                  />
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={!id || busyItem === id || !(commentDraft[id] || "").trim()}
                    onClick={() => void handleComment(id)}
                  >
                    Comentar
                  </Button>
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>

      {evidence && (
        <Card className="border-primary/20">
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium">
              Evidencia — {evidence.requirement ?? evidence.requirement_key}
            </CardTitle>
            <Button size="sm" variant="ghost" onClick={() => setEvidence(null)}>
              Cerrar
            </Button>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {!evidence.tiene_evidencia && (
              <p className="text-muted-foreground">Sin evidencia trazable del pliego para este requisito.</p>
            )}
            <p>
              <span className="text-muted-foreground">Documento origen:</span>{" "}
              {evidence.evidencia.documento_origen ?? "—"}
            </p>
            <p>
              <span className="text-muted-foreground">Página:</span>{" "}
              {evidence.evidencia.pagina ?? "—"}
            </p>
            <p>
              <span className="text-muted-foreground">Párrafo / sección:</span>{" "}
              {evidence.evidencia.parrafo ?? "—"}
            </p>
            <p className="rounded bg-muted/40 p-2 text-xs whitespace-pre-wrap">
              {evidence.evidencia.texto_original || "—"}
            </p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Previsualización del expediente</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p className="text-muted-foreground">{preview?.note}</p>
          <div className="flex flex-wrap gap-2 text-xs">
            <Badge variant="outline">PDF: {preview?.counts?.pdf ?? 0}</Badge>
            <Badge variant="outline">Word: {preview?.counts?.word ?? 0}</Badge>
            <Badge variant="outline">Excel: {preview?.counts?.excel ?? 0}</Badge>
            <Badge variant="outline">ZIP: {preview?.zip_available ? "sí" : "no"}</Badge>
          </div>
          <div className="max-h-56 overflow-y-auto space-y-1">
            {(preview?.files ?? []).slice(0, 40).map((f) => (
              <div key={f.path} className="flex items-center justify-between gap-2 border-b py-1 last:border-0">
                <span className="truncate">
                  {f.path} {f.planned ? <Badge variant="secondary">planificado</Badge> : null}
                </span>
                {f.preview_url && !f.planned ? (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => void apiClient.openDGCPExpedientePreviewFile(opportunityId, f.path)}
                  >
                    Abrir {f.kind}
                  </Button>
                ) : null}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Actividad del expediente</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {(data.timeline?.length ?? 0) === 0 && (
            <p className="text-muted-foreground">Aún no hay eventos registrados.</p>
          )}
          {(data.timeline ?? []).slice(0, 20).map((ev, idx) => (
            <div key={`${ev.at}-${idx}`} className="flex gap-3 border-b pb-2 last:border-0">
              <div className="min-w-[140px] text-xs text-muted-foreground tabular-nums">
                {formatTs(ev.at)}
              </div>
              <div>
                <p className="font-medium text-sm">{ev.label ?? ev.event_type}</p>
                <p className="text-muted-foreground text-xs">{ev.summary}</p>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

function formatTs(iso: string): string {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat("es-DO", { dateStyle: "short", timeStyle: "short" }).format(
      new Date(iso),
    );
  } catch {
    return iso;
  }
}

function Kpi({
  label,
  value,
  icon,
  tone,
}: {
  label: string;
  value: string | number;
  icon?: React.ReactNode;
  tone?: "primary" | "ok" | "warn" | "bad";
}) {
  return (
    <div
      className={cn(
        "rounded-md border px-3 py-2",
        tone === "primary" && "border-primary/30 bg-primary/5",
        tone === "ok" && "border-emerald-500/30 bg-emerald-500/5",
        tone === "warn" && "border-amber-500/30 bg-amber-500/5",
        tone === "bad" && "border-red-500/30 bg-red-500/5",
      )}
    >
      <p className="flex items-center gap-1 text-[11px] uppercase tracking-wide text-muted-foreground">
        {icon}
        {label}
      </p>
      <p className="text-2xl font-semibold tabular-nums">{value}</p>
    </div>
  );
}
