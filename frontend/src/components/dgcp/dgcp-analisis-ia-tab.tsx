"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2, RefreshCw, Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import { isUserFacingRecommendation } from "@/lib/dgcp-detail-tabs";
import {
  EXPEDIENTE_STATUS_LABELS,
  hasJaiosIntelligence,
  isDGCPOperationalInterest,
  type DGCPBidPackage,
  type DGCPChecklist,
  type DGCPOpportunity,
  type DGCPProcessDocuments,
  type DGCPRequirements,
} from "@/lib/dgcp";

type Phase = "loading" | "no_docs" | "ready" | "running" | "done" | "error";

export function DgcpAnalisisIaTab({
  opportunity,
  execBid,
  execChecklist,
  execStatus,
  onGoDocumentos,
  onAnalyzed,
}: {
  opportunity: DGCPOpportunity;
  execBid: DGCPBidPackage | null;
  execChecklist: DGCPChecklist | null;
  execStatus: string | null;
  onGoDocumentos?: () => void;
  onAnalyzed?: () => void;
}) {
  const interested = isDGCPOperationalInterest(opportunity.status);
  const [phase, setPhase] = useState<Phase>("loading");
  const [error, setError] = useState<string | null>(null);
  const [processDocs, setProcessDocs] = useState<DGCPProcessDocuments | null>(null);
  const [requirements, setRequirements] = useState<DGCPRequirements | null>(null);
  const [checklist, setChecklist] = useState<DGCPChecklist | null>(execChecklist);
  const [bid, setBid] = useState<DGCPBidPackage | null>(execBid);
  const [intel, setIntel] = useState(
    hasJaiosIntelligence(opportunity.jaios_intelligence) ? opportunity.jaios_intelligence : null,
  );
  const [job, setJob] = useState<{
    status?: string;
    stage?: string | null;
    progress?: number | null;
    error?: string | null;
  } | null>(null);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);

  const realDocs = useMemo(() => {
    const items = processDocs?.items ?? [];
    return items.filter((d) => d.source_type === "process_file" || d.source_type === "reference");
  }, [processDocs]);

  const refresh = useCallback(async () => {
    if (!interested) {
      setPhase("ready");
      return;
    }
    setError(null);
    try {
      const [docs, req, chk, pkg, status, intelligence] = await Promise.all([
        apiClient.getDGCPProcessDocuments(opportunity.id).catch(() => null),
        apiClient.getDGCPRequirements(opportunity.id).catch(() => null),
        apiClient.getDGCPChecklist(opportunity.id).catch(() => null),
        apiClient.getDGCPBidPackage(opportunity.id).catch(() => null),
        apiClient.getDGCPAnalysisStatus?.(opportunity.id).catch(() => null),
        apiClient.getDGCPIntelligence?.(opportunity.id).catch(() => null),
      ]);
      setProcessDocs(docs);
      if (req) setRequirements(req);
      if (chk) setChecklist(chk);
      if (pkg) setBid(pkg);
      if (hasJaiosIntelligence(intelligence)) setIntel(intelligence);
      const files = (docs?.items ?? []).filter(
        (d) => d.source_type === "process_file" || d.source_type === "reference",
      );
      if (status?.job?.status === "in_progress") {
        setJob(status.job);
        setPhase("running");
        return;
      }
      if (files.length === 0) {
        setPhase("no_docs");
        return;
      }
      if (pkg?.analyzed_at || req?.analyzed_at) {
        setPhase("done");
        return;
      }
      setPhase("ready");
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo cargar el estado del análisis");
      setPhase("error");
    }
  }, [interested, opportunity.id]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (phase !== "running" || !startedAt) return;
    const t = window.setInterval(() => setElapsed(Math.floor((Date.now() - startedAt) / 1000)), 1000);
    return () => window.clearInterval(t);
  }, [phase, startedAt]);

  useEffect(() => {
    if (phase !== "running") return;
    const timer = window.setInterval(() => {
      void (apiClient.getDGCPAnalysisStatus?.(opportunity.id) ?? Promise.resolve({ job: null }))
        .then(async (s) => {
          if (!s.job || s.job.status !== "in_progress") {
            setJob(s.job);
            await refresh();
            onAnalyzed?.();
            return;
          }
          setJob(s.job);
        })
        .catch(() => {});
    }, 2500);
    return () => window.clearInterval(timer);
  }, [phase, opportunity.id, refresh, onAnalyzed]);

  const runAnalyze = async () => {
    setError(null);
    setPhase("running");
    setStartedAt(Date.now());
    setElapsed(0);
    try {
      const result = await apiClient.analyzeDGCPRequirements(opportunity.id);
      if (result.requirements) setRequirements(result.requirements);
      if (result.checklist) setChecklist(result.checklist);
      if (result.bid_package) setBid(result.bid_package);
      try {
        const intelligence = await apiClient.analyzeDGCPIntelligence(opportunity.id);
        if (hasJaiosIntelligence(intelligence)) setIntel(intelligence);
      } catch {
        /* intelligence opcional */
      }
      await refresh();
      onAnalyzed?.();
      setPhase("done");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "El análisis falló";
      setError(msg);
      setPhase("error");
    }
  };

  if (!interested) {
    return (
      <Card>
        <CardContent className="py-4 text-sm">
          Marque interés para habilitar el análisis del pliego.
        </CardContent>
      </Card>
    );
  }

  if (phase === "loading") {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground py-8 justify-center">
        <Loader2 className="h-4 w-4 animate-spin" />
        Cargando estado del análisis…
      </div>
    );
  }

  if (phase === "no_docs") {
    return (
      <Card className="border-amber-500/30 bg-amber-500/5">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Este proceso no tiene documentos cargados para analizar.</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Suba el pliego u otros documentos del proceso antes de ejecutar el análisis con IA.
          </p>
          <Button type="button" onClick={() => onGoDocumentos?.()}>
            <Upload className="mr-2 h-4 w-4" />
            Cargar documentos del proceso
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (phase === "ready") {
    return (
      <Card className="border-primary/30">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">
            Los documentos están disponibles, pero todavía no han sido analizados.
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            {realDocs.length} documento(s) del proceso listos. El análisis extraerá requisitos, documentos
            solicitados, riesgos y recomendaciones.
          </p>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          <div className="flex flex-wrap gap-2">
            <Button type="button" onClick={() => void runAnalyze()}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Analizar proceso con IA
            </Button>
            <Button type="button" variant="outline" onClick={() => onGoDocumentos?.()}>
              Ver documentos
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (phase === "running") {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            Análisis en curso
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-2">
          <p>Estado: {job?.status || "in_progress"}</p>
          <p>Etapa: {job?.stage || "Procesando pliego y requisitos"}</p>
          <p>Progreso: {job?.progress != null ? `${job.progress}%` : "—"}</p>
          <p>Tiempo transcurrido: {elapsed}s</p>
          {job?.error ? <p className="text-destructive">{job.error}</p> : null}
        </CardContent>
      </Card>
    );
  }

  if (phase === "error") {
    return (
      <Card className="border-destructive/40">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">No se pudo completar el análisis</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-destructive">{error || "Error desconocido"}</p>
          <div className="flex flex-wrap gap-2">
            <Button type="button" onClick={() => void runAnalyze()}>
              Reintentar análisis
            </Button>
            <Button type="button" variant="outline" onClick={() => void refresh()}>
              Actualizar estado
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  const exec = intel?.executive;
  const decision = exec?.recommendation || "revisar";
  const score = intel?.premium_score ?? opportunity.score ?? opportunity.confidence_score;
  const summary =
    exec?.summary ||
    (requirements
      ? `Proceso ${requirements.opportunity_code}: se extrajeron requisitos técnicos, legales, financieros y administrativos.`
      : null);
  const reqGroups = [
    { label: "Legales", items: requirements?.legal || [] },
    { label: "Técnicos", items: requirements?.technical || [] },
    { label: "Financieros", items: requirements?.financial || [] },
    { label: "Administrativos", items: requirements?.administrative || [] },
  ].filter((g) => g.items.length > 0);
  const requestedDocs = [
    ...(requirements?.mandatory_documents || []),
    ...(checklist?.items || []).map((i) => ({
      key: i.requirement_key,
      label: i.requirement,
      mandatory: i.mandatory,
      status: i.status,
    })),
  ];
  const pending = (checklist?.items || [])
    .filter((i) => ["faltante", "pendiente", "encontrado_sin_analizar"].includes(i.status))
    .map((i) => i.requirement)
    .filter(isUserFacingRecommendation)
    .slice(0, 15);
  const risks = [
    ...(exec?.risks || []).map((r: unknown) => (typeof r === "string" ? r : String(r))),
    ...(opportunity.risks || []).map((r) => (typeof r === "string" ? r : r.descripcion || "")),
    ...(checklist?.items || []).map((i) => i.risk || "").filter(Boolean),
  ]
    .filter(isUserFacingRecommendation)
    .slice(0, 10);
  const recommendations = [
    ...(exec?.next_actions || []),
    ...(opportunity.ai_recommendations || []),
    ...(bid?.recommended_tasks || []),
  ]
    .map((a) => (typeof a === "string" ? a : ""))
    .filter(isUserFacingRecommendation)
    .slice(0, 10);

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-1"><CardTitle className="text-xs text-muted-foreground">Decisión sugerida</CardTitle></CardHeader>
          <CardContent className="text-lg font-semibold capitalize">{decision}</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1"><CardTitle className="text-xs text-muted-foreground">Score / confianza</CardTitle></CardHeader>
          <CardContent className="text-lg font-semibold">
            {score ?? "—"}
            {opportunity.confidence_score ? ` · ${opportunity.confidence_score}%` : ""}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1"><CardTitle className="text-xs text-muted-foreground">Estado</CardTitle></CardHeader>
          <CardContent className="text-sm">
            Analizado {bid?.analyzed_at ? new Date(bid.analyzed_at).toLocaleString("es-DO") : ""}
            {execStatus ? (
              <span className="block text-xs text-muted-foreground mt-1">
                {EXPEDIENTE_STATUS_LABELS[execStatus] ?? execStatus}
              </span>
            ) : null}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1"><CardTitle className="text-xs text-muted-foreground">Documentos proceso</CardTitle></CardHeader>
          <CardContent className="text-lg font-semibold">{realDocs.length}</CardContent>
        </Card>
      </div>

      {summary ? (
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">Resumen ejecutivo</CardTitle></CardHeader>
          <CardContent className="text-sm">{summary}</CardContent>
        </Card>
      ) : null}

      {reqGroups.length > 0 ? (
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">Requisitos</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            {reqGroups.map((g) => (
              <div key={g.label}>
                <p className="font-medium mb-1">{g.label}</p>
                <ul className="list-disc pl-5 space-y-0.5">
                  {g.items.slice(0, 8).map((i) => (
                    <li key={i.key}>
                      {i.label}
                      {i.mandatory ? " · obligatorio" : ""}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}

      {requestedDocs.length > 0 ? (
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">Documentos solicitados</CardTitle></CardHeader>
          <CardContent>
            <ul className="space-y-1 text-sm">
              {(checklist?.items || []).slice(0, 20).map((i) => (
                <li key={i.id} className="rounded border px-3 py-1.5 flex justify-between gap-2">
                  <span>
                    {i.requirement}
                    {i.mandatory ? " *" : ""}
                  </span>
                  <span className="text-xs text-muted-foreground">{i.display_status || i.status}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}

      {pending.length > 0 ? (
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">Pendientes</CardTitle></CardHeader>
          <CardContent>
            <ul className="list-disc pl-5 text-sm space-y-1">
              {pending.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}

      {risks.length > 0 ? (
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">Riesgos</CardTitle></CardHeader>
          <CardContent>
            <ul className="space-y-1 text-sm">
              {risks.map((r, i) => (
                <li key={i} className="rounded border px-3 py-1.5">{r}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}

      {recommendations.length > 0 ? (
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">Recomendaciones</CardTitle></CardHeader>
          <CardContent>
            <ul className="list-disc pl-5 text-sm space-y-1">
              {recommendations.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <Button type="button" variant="outline" onClick={() => void runAnalyze()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Reanalizar con IA
        </Button>
        <Button type="button" variant="outline" onClick={() => onGoDocumentos?.()}>
          Ir a documentos
        </Button>
      </div>
    </div>
  );
}
