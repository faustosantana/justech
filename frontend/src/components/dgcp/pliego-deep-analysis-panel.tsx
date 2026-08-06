"use client";

import { useCallback, useEffect, useState } from "react";
import { ChevronDown, ChevronRight, ExternalLink, Loader2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";

type PliegoEvidence = {
  document_id?: string | null;
  document_name?: string;
  page?: number | null;
  section?: string | null;
  fragment?: string;
  confidence?: number;
  page_identified?: boolean;
  review_required?: boolean;
};

type PliegoField = {
  key: string;
  label?: string;
  value?: unknown;
  items?: unknown[];
  found?: boolean;
  confidence?: number;
  evidence?: PliegoEvidence[];
  source_documents?: string[];
  review_required?: boolean;
  notes?: string;
  reviewed?: boolean;
  comment?: string | null;
};

type PliegoAnalysis = {
  opportunity_id: string;
  status?: string;
  version?: number;
  created_at?: string;
  fields?: Record<string, PliegoField>;
  documents?: Array<{
    document_id: string;
    name: string;
    doc_type?: string;
    pages?: number | null;
    ocr_used?: boolean;
    duplicate_of?: string | null;
    extraction_status?: string;
  }>;
  stages?: Array<{ stage: string; status: string; message?: string; error?: string | null }>;
  decision?: {
    decision?: string;
    reason?: string;
    positive_factors?: string[];
    negative_factors?: string[];
    main_risks?: string[];
    critical_pendientes?: string[];
    confidence?: number;
  } | null;
  meta?: {
    contradictions?: string[];
    failed_stages?: string[];
    prompt_hash?: string;
    model?: string | null;
    duration_ms?: number;
  };
  ui_sections?: Record<string, string[]>;
};

const SECTION_ORDER = [
  "Resumen",
  "Datos generales",
  "Cronograma",
  "Requisitos",
  "Documentos solicitados",
  "Garantías y pagos",
  "Evaluación y descalificación",
  "Riesgos",
  "Pendientes",
  "Recomendaciones",
  "Preguntas",
  "Decisión sugerida",
];

function fmtValue(field: PliegoField): string {
  if (field.value == null || field.value === "") return "No identificado";
  if (typeof field.value === "object") return JSON.stringify(field.value);
  return String(field.value);
}

function ItemList({ items }: { items: unknown[] }) {
  if (!items?.length) return null;
  return (
    <ul className="mt-2 space-y-1 text-sm">
      {items.slice(0, 30).map((item, idx) => {
        if (typeof item === "string") {
          return (
            <li key={idx} className="rounded border px-2 py-1">
              {item}
            </li>
          );
        }
        if (item && typeof item === "object") {
          const o = item as Record<string, unknown>;
          const title =
            (o.nombre as string) ||
            (o.label as string) ||
            (o.descripcion as string) ||
            (o.accion as string) ||
            (o.texto as string) ||
            (o.decision as string) ||
            null;
          const meta = [
            o.prioridad && `prioridad: ${o.prioridad}`,
            o.severidad && `severidad: ${o.severidad}`,
            o.categoria && `cat: ${o.categoria}`,
            o.pagina != null && `pág. ${o.pagina}`,
            o.obligatorio === true && "obligatorio",
            o.obligatorio === false && "condicional",
          ]
            .filter(Boolean)
            .join(" · ");
          return (
            <li key={idx} className="rounded border px-2 py-1.5">
              <div>{title || "Ítem"}</div>
              {meta ? <div className="text-xs text-muted-foreground">{meta}</div> : null}
            </li>
          );
        }
        return (
          <li key={idx} className="rounded border px-2 py-1 text-xs">
            {String(item)}
          </li>
        );
      })}
    </ul>
  );
}

function EvidenceBlock({
  opportunityId,
  evidence,
  onOpenDoc,
}: {
  opportunityId: string;
  evidence: PliegoEvidence[];
  onOpenDoc?: (documentId: string, page?: number | null) => void;
}) {
  if (!evidence?.length) {
    return <p className="text-xs text-muted-foreground mt-2">Sin evidencia de página.</p>;
  }
  return (
    <div className="mt-2 space-y-1">
      {evidence.slice(0, 5).map((ev, i) => (
        <div key={i} className="rounded bg-muted/40 px-2 py-1.5 text-xs space-y-1">
          <div className="flex flex-wrap gap-x-2 gap-y-0.5">
            <span className="font-medium">{ev.document_name || "Documento"}</span>
            <span>
              {ev.page_identified && ev.page != null
                ? `pág. ${ev.page}`
                : "página no identificada"}
            </span>
            {ev.section ? <span className="text-muted-foreground">{ev.section}</span> : null}
            {ev.confidence != null ? (
              <span className="text-muted-foreground">
                conf. {Math.round(ev.confidence * 100)}%
              </span>
            ) : null}
          </div>
          {ev.fragment ? <p className="text-muted-foreground italic">«{ev.fragment}»</p> : null}
          {ev.document_id ? (
            <button
              type="button"
              className="inline-flex items-center gap-1 text-primary hover:underline"
              onClick={() => onOpenDoc?.(ev.document_id!, ev.page)}
            >
              Abrir documento
              <ExternalLink className="h-3 w-3" />
            </button>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function FieldCard({
  opportunityId,
  field,
  onReview,
  onOpenDoc,
}: {
  opportunityId: string;
  field: PliegoField;
  onReview: (key: string) => void;
  onOpenDoc?: (documentId: string, page?: number | null) => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-lg border px-3 py-2">
      <button
        type="button"
        className="flex w-full items-start justify-between gap-2 text-left"
        onClick={() => setOpen((v) => !v)}
      >
        <div>
          <div className="text-sm font-medium">{field.label || field.key}</div>
          <div className="text-xs text-muted-foreground">
            {field.found ? "Encontrado" : "No identificado"}
            {field.confidence != null ? ` · ${Math.round(field.confidence * 100)}%` : ""}
            {field.review_required ? " · revisión" : ""}
            {field.reviewed ? " · revisado" : ""}
          </div>
        </div>
        {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
      </button>
      <p className="mt-1 text-sm">{fmtValue(field)}</p>
      {open && (
        <div className="mt-2 border-t pt-2">
          <ItemList items={field.items || []} />
          {field.notes ? <p className="text-xs text-muted-foreground mt-1">{field.notes}</p> : null}
          <EvidenceBlock
            opportunityId={opportunityId}
            evidence={field.evidence || []}
            onOpenDoc={onOpenDoc}
          />
          <div className="mt-2 flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => onReview(field.key)}
              disabled={!!field.reviewed}
            >
              {field.reviewed ? "Revisado" : "Marcar revisado"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

export function PliegoDeepAnalysisPanel({
  opportunityId,
  interested,
}: {
  opportunityId: string;
  interested: boolean;
}) {
  const [data, setData] = useState<PliegoAnalysis | null>(null);
  const [versions, setVersions] = useState<Array<{ version: number; status: string; created_at?: string }>>([]);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!interested) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getDGCPPliegoAnalysis(opportunityId);
      setData((res?.current as PliegoAnalysis) || null);
      setVersions((res?.versions as typeof versions) || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo cargar el análisis de pliego");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [opportunityId, interested]);

  useEffect(() => {
    void load();
  }, [load]);

  const run = async () => {
    setRunning(true);
    setError(null);
    try {
      const res = await apiClient.runDGCPPliegoAnalysis(opportunityId, true);
      setData((res?.current as PliegoAnalysis) || null);
      setVersions((res?.versions as typeof versions) || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falló el análisis profundo del pliego");
    } finally {
      setRunning(false);
    }
  };

  const onReview = async (key: string) => {
    try {
      const updated = await apiClient.reviewDGCPPliegoField(opportunityId, key, { reviewed: true });
      setData(updated as PliegoAnalysis);
    } catch {
      setError("No se pudo marcar el campo como revisado");
    }
  };

  const onOpenDoc = (documentId: string, page?: number | null) => {
    const q = page ? `?page=${page}` : "";
    window.open(
      `/api/v1/dgcp/opportunities/${opportunityId}/process-documents/${documentId}/file${q}`,
      "_blank",
      "noopener,noreferrer",
    );
  };

  if (!interested) {
    return (
      <Card>
        <CardContent className="py-4 text-sm text-muted-foreground">
          Marque interés para ejecutar el análisis profundo del pliego.
        </CardContent>
      </Card>
    );
  }

  const fields = data?.fields || {};
  const sections = data?.ui_sections || {};
  const sectionKeys = SECTION_ORDER.filter((s) => sections[s]?.length);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <Button onClick={() => void run()} disabled={running}>
          {running ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-2 h-4 w-4" />
          )}
          Analizar pliego completo (29 campos)
        </Button>
        <Button variant="outline" onClick={() => void load()} disabled={loading}>
          Actualizar
        </Button>
      </div>

      {error && (
        <p className="text-sm text-destructive rounded-lg border border-destructive/30 px-3 py-2">
          {error}
        </p>
      )}

      {loading && !data && (
        <p className="text-sm text-muted-foreground">Cargando análisis profundo…</p>
      )}

      {!loading && !data && !error && (
        <Card>
          <CardContent className="py-4 text-sm text-muted-foreground">
            Aún no hay análisis profundo. Ejecute «Analizar pliego completo» o «Analizar pliego con IA».
          </CardContent>
        </Card>
      )}

      {data && (
        <>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Estado del análisis profundo</CardTitle>
            </CardHeader>
            <CardContent className="text-sm space-y-1">
              <p>
                Estado: <strong>{data.status || "—"}</strong>
                {data.version != null ? ` · versión ${data.version}` : ""}
                {data.meta?.duration_ms != null ? ` · ${data.meta.duration_ms} ms` : ""}
              </p>
              {data.meta?.prompt_hash ? (
                <p className="text-xs text-muted-foreground">prompt {data.meta.prompt_hash}</p>
              ) : null}
              {data.meta?.failed_stages?.length ? (
                <p className="text-amber-700 dark:text-amber-300 text-xs">
                  Etapas con fallo: {data.meta.failed_stages.join(", ")}
                </p>
              ) : null}
              {data.meta?.contradictions?.length ? (
                <ul className="text-xs text-amber-800 list-disc pl-4">
                  {data.meta.contradictions.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              ) : null}
              {versions.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  Historial: {versions.map((v) => `v${v.version} (${v.status})`).join(" · ")}
                </p>
              )}
            </CardContent>
          </Card>

          {data.decision && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Decisión sugerida</CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-2">
                <p>
                  <strong>{data.decision.decision || "revisar"}</strong>
                  {data.decision.confidence != null
                    ? ` · confianza ${Math.round(data.decision.confidence * 100)}%`
                    : ""}
                </p>
                {data.decision.reason ? <p>{data.decision.reason}</p> : null}
                <p className="text-xs text-muted-foreground">
                  Sugerencia no irreversible — requiere validación humana.
                </p>
              </CardContent>
            </Card>
          )}

          {sectionKeys.map((section) => (
            <Card key={section}>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">{section}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {(sections[section] || []).map((key) => {
                  const field = fields[key];
                  if (!field) return null;
                  return (
                    <FieldCard
                      key={key}
                      opportunityId={opportunityId}
                      field={field}
                      onReview={onReview}
                      onOpenDoc={onOpenDoc}
                    />
                  );
                })}
              </CardContent>
            </Card>
          ))}

          {data.documents && data.documents.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Documentos de entrada</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="text-sm space-y-1">
                  {data.documents.map((d) => (
                    <li key={d.document_id} className="rounded border px-2 py-1.5 flex justify-between gap-2">
                      <span>
                        {d.name}{" "}
                        <span className="text-xs text-muted-foreground">
                          ({d.doc_type}
                          {d.pages != null ? ` · ${d.pages} pág.` : ""}
                          {d.ocr_used ? " · OCR" : ""}
                          {d.duplicate_of ? " · duplicado omitido" : ""})
                        </span>
                      </span>
                      <span className="text-xs">{d.extraction_status}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
