"use client";

import { Download, Eye, FileText, Loader2, PenLine, RefreshCw, Send } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiClient } from "@/lib/api";
import { fetchAuthenticatedFile, revokeAuthenticatedFileUrl } from "@/lib/authenticated-file";
import type { DGCPAutofillTemplate, DGCPFormPreview, DGCPMissingFieldItem, DGCPRequiredFormItem } from "@/lib/dgcp";
import { formatCompletionStatus, formatFormStatus } from "@/lib/dgcp";
import { dgcpSmartAutofillEnabled } from "@/lib/dgcp-feature-flags";
import { M365TemplateOperationalBanner } from "@/components/m365/m365-template-operational-banner";
import { cn } from "@/lib/utils";

function formatTemplateSource(
  sourceType?: string | null,
  cacheStatus?: { cached?: boolean } | null,
): string {
  if (sourceType === "m365_cache" || cacheStatus?.cached) return "caché oficial DGCP/M365";
  if (sourceType === "m365") return "SharePoint / M365";
  if (sourceType === "local" || sourceType === "stub") return "no oficial (bloqueado)";
  return sourceType || "desconocida";
}

const CATEGORY_LABELS: Record<string, string> = {
  sncc_formulario: "SNCC",
  sncc_documento: "SNCC Doc",
  carta: "Carta",
  oferta_economica: "Oferta econ.",
  oferta_tecnica: "Oferta téc.",
  declaracion: "Declaración",
  sncc_pliego: "Pliego",
  contrato: "Contrato",
  portada: "Portada",
  consultoria: "Consultoría",
  proveedor: "Proveedor",
  legal_reutilizable: "Legal",
  datos_empresa: "Datos",
  general_dgcp: "DGCP",
  administrativo: "Admin",
};

type Props = {
  opportunityId: string;
  formType: string;
  onFormTypeChange: (v: string) => void;
  onGenerated?: () => void;
  onSendReview?: () => void;
};

export function DgcpAutofillDocumentPanel({
  opportunityId,
  formType,
  onFormTypeChange,
  onGenerated,
  onSendReview,
}: Props) {
  const [templates, setTemplates] = useState<DGCPAutofillTemplate[]>([]);
  const [templatesLoading, setTemplatesLoading] = useState(true);
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [preview, setPreview] = useState<DGCPFormPreview | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [loadingPdf, setLoadingPdf] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [showFieldEditor, setShowFieldEditor] = useState(false);
  const [showAliasMapper, setShowAliasMapper] = useState(false);
  const [mappingScope, setMappingScope] = useState<"global" | "template" | "document">("document");
  const [canonicalFields, setCanonicalFields] = useState<{ key: string; label: string }[]>([]);
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [lastGenerate, setLastGenerate] = useState<{ pdf_path?: string; filename?: string } | null>(null);
  const [requiredForms, setRequiredForms] = useState<DGCPRequiredFormItem[]>([]);
  const [libraryForms, setLibraryForms] = useState<DGCPAutofillTemplate[]>([]);
  const [missingFields, setMissingFields] = useState<DGCPMissingFieldItem[]>([]);
  const [completedFields, setCompletedFields] = useState<import("@/lib/dgcp").DGCPAutofillFieldStatus[]>([]);
  const [missingDraft, setMissingDraft] = useState<Record<string, string>>({});
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [savingFields, setSavingFields] = useState(false);
  const smartAutofill = dgcpSmartAutofillEnabled();

  const loadAutofillState = useCallback(
    async (fieldOverrides?: Record<string, string>) => {
      if (!formType) return null;
      const mergedOverrides = fieldOverrides ?? overrides;
      try {
        const [previewData, missingData] = await Promise.all([
          apiClient.autofillDGCPForm(opportunityId, formType, "justech", mergedOverrides),
          smartAutofill
            ? apiClient.getDGCPMissingFields(opportunityId, formType)
            : Promise.resolve(null),
        ]);
        setPreview(previewData);
        setError(null);
        if (missingData) {
          setMissingFields(missingData.fields);
          setCompletedFields(missingData.completed_fields ?? []);
        }
        const init: Record<string, string> = {};
        for (const f of previewData.fields) {
          if (f.key && f.value) init[f.key] = f.value;
        }
        setOverrides((prev) => ({ ...init, ...prev, ...mergedOverrides }));
        return previewData;
      } catch (err) {
        if (err instanceof ApiError && (err.code === "GRAPH_ERROR" || err.status === 401 || err.status === 502)) {
          try {
            const fallback = await apiClient.previewDGCPForm(opportunityId, formType, "justech");
            setPreview(fallback);
            setError(
              "Campos cargados desde el repositorio corporativo. Para generar el Word/PDF del formulario, conecte Microsoft 365 en Cuentas.",
            );
            return fallback;
          } catch {
            /* continúa al mensaje principal */
          }
        }
        const hint =
          err instanceof ApiError && typeof err.data === "object" && err.data && "hint" in (err.data as object)
            ? String((err.data as { hint?: string }).hint ?? "")
            : "";
        const detail =
          err instanceof ApiError && typeof err.data === "object" && err.data && "detail" in (err.data as object)
            ? String((err.data as { detail?: string }).detail ?? "")
            : "";
        const base =
          err instanceof ApiError
            ? detail || err.message
            : "No se pudo cargar el autollenado del formulario.";
        setError(hint ? `${base} ${hint}` : base);
        setPreview(null);
        return null;
      }
    },
    [formType, opportunityId, smartAutofill],
  );

  const loadPdfPreview = useCallback(
    async (fields?: Record<string, string>) => {
      setLoadingPdf(true);
      setError(null);
      try {
        if (pdfUrl) revokeAuthenticatedFileUrl(pdfUrl);
        const { objectUrl } = await fetchAuthenticatedFile(
          `/dgcp/opportunities/${opportunityId}/forms/document-preview`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              form_type: formType,
              company: "justech",
              field_overrides: fields ?? overrides,
            }),
          },
        );
        setPdfUrl(objectUrl);
      } catch {
        setError("No se pudo generar la vista previa del documento.");
      } finally {
        setLoadingPdf(false);
      }
    },
    [formType, opportunityId, overrides],
  );

  const handlePreview = async (fieldOverrides?: Record<string, string>) => {
    setLoadingPreview(true);
    setError(null);
    try {
      const data = await loadAutofillState(fieldOverrides);
      if (data?.document_preview_available !== false) {
        const fieldMap: Record<string, string> = {};
        for (const f of data?.fields ?? []) {
          if (f.key && f.value) fieldMap[f.key] = f.value;
        }
        await loadPdfPreview({ ...fieldMap, ...(fieldOverrides ?? overrides) });
      }
    } catch {
      setError("No se pudo analizar la plantilla ni generar la vista previa PDF.");
    } finally {
      setLoadingPreview(false);
    }
  };

  const saveFieldData = async () => {
    if (!formType) return;
    setSavingFields(true);
    setError(null);
    try {
      for (const field of missingFields) {
        const value = (missingDraft[field.key] ?? overrides[field.key] ?? field.inferred_value ?? "").trim();
        if (!value) continue;
        await apiClient.resolveDGCPMissingField(
          opportunityId,
          {
            key: field.key,
            value,
            persist_to_profile: field.persist_targets.includes("perfil_empresarial"),
            persist_to_expediente: true,
          },
          formType,
        );
      }
      for (const f of preview?.fields ?? []) {
        const key = f.key ?? f.label;
        const value = (overrides[key] ?? "").trim();
        if (!value || value === (f.value ?? "")) continue;
        if (f.status === "completo" && f.value === value) continue;
        await apiClient.resolveDGCPMissingField(
          opportunityId,
          { key, value, persist_to_profile: false, persist_to_expediente: true },
          formType,
        );
      }
      await handlePreview(overrides);
      onGenerated?.();
    } catch {
      setError("No se pudieron guardar uno o más campos. Verifique los valores e intente de nuevo.");
    } finally {
      setSavingFields(false);
    }
  };

  const handleGenerate = async (draft = false) => {
    setGenerating(true);
    setError(null);
    try {
      const result = await apiClient.generateDGCPForm(opportunityId, formType, "justech", overrides, draft);
      setLastGenerate(result);
      await loadPdfPreview(overrides);
      onGenerated?.();
    } catch (e) {
      const msg =
        e instanceof ApiError
          ? String((e.data as { detail?: string })?.detail ?? e.message)
          : draft
            ? "No se pudo guardar el borrador."
            : "Hay pendientes críticos. Complete los campos o guarde como borrador.";
      setError(msg);
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = async () => {
    try {
      await apiClient.downloadDGCPAutofillPdf(opportunityId, formType, "justech", overrides);
    } catch {
      setError("No se pudo descargar el PDF.");
    }
  };

  useEffect(() => {
    apiClient.getDGCPAutofillCanonicalFields().then((d) => setCanonicalFields(d.items)).catch(() => {});
  }, []);

  useEffect(() => {
    let cancelled = false;
    setTemplatesLoading(true);
    if (smartAutofill) {
      apiClient
        .getDGCPRequiredForms(opportunityId)
        .then((data) => {
          if (cancelled) return;
          setRequiredForms(data.required_forms);
          setLibraryForms(data.library_forms);
          setTemplates(data.library_forms);
          if (!formType && data.required_forms.length > 0) {
            onFormTypeChange(data.required_forms[0].form_type);
          }
        })
        .catch(() => {
          if (!cancelled) {
            setRequiredForms([]);
            setLibraryForms([]);
            setTemplates([]);
          }
        })
        .finally(() => {
          if (!cancelled) setTemplatesLoading(false);
        });
    } else {
      apiClient
        .getDGCPAutofillTemplates()
        .then((data) => {
          if (!cancelled) setTemplates(data.items);
        })
        .catch(() => {
          if (!cancelled) setTemplates([]);
        })
        .finally(() => {
          if (!cancelled) setTemplatesLoading(false);
        });
    }
    return () => {
      cancelled = true;
    };
  }, [opportunityId, smartAutofill, formType, onFormTypeChange]);

  useEffect(() => {
    if (!smartAutofill || !formType) return;
    let cancelled = false;
    apiClient
      .getDGCPMissingFields(opportunityId, formType)
      .then((data) => {
        if (!cancelled) {
          setMissingFields(data.fields);
          setCompletedFields(data.completed_fields ?? []);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setMissingFields([]);
          setCompletedFields([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [opportunityId, formType, smartAutofill, preview?.completion_status]);

  const resolveMissing = async (field: DGCPMissingFieldItem) => {
    const value = missingDraft[field.key]?.trim();
    if (!value) return;
    try {
      const res = await apiClient.resolveDGCPMissingField(opportunityId, {
        key: field.key,
        value,
        persist_to_profile: field.persist_targets.includes("perfil_empresarial"),
        persist_to_expediente: true,
      }, formType);
      setMissingFields(res.missing_fields.fields);
      setCompletedFields(res.missing_fields.completed_fields ?? []);
      setOverrides((prev) => ({ ...prev, [field.key]: value }));
      setMissingDraft((prev) => {
        const next = { ...prev };
        delete next[field.key];
        return next;
      });
      await loadAutofillState();
      await loadPdfPreview({ ...overrides, [field.key]: value });
      onGenerated?.();
    } catch {
      setError(`No se pudo guardar el campo ${field.label}.`);
    }
  };

  const categories = useMemo(() => {
    const set = new Set(templates.map((t) => t.detected_category));
    return Array.from(set).sort();
  }, [templates]);

  const filteredTemplates = useMemo(() => {
    if (!categoryFilter) return templates;
    return templates.filter((t) => t.detected_category === categoryFilter);
  }, [templates, categoryFilter]);

  const selectedTemplate = useMemo(
    () => templates.find((t) => t.form_type === formType) ?? null,
    [templates, formType],
  );

  const saveAliasOverride = (
    af: NonNullable<DGCPFormPreview["alias_fields"]>[number],
    patch: { canonical?: string | null; value?: string; status?: string },
  ) => {
    void apiClient.saveDGCPAliasMapping({
      alias_normalized: af.alias_normalized,
      alias_original: af.alias,
      canonical: patch.canonical ?? af.canonical ?? null,
      value: patch.value,
      scope: mappingScope,
      template_key: mappingScope !== "global" ? selectedTemplate?.template_key : undefined,
      opportunity_id: mappingScope === "document" ? opportunityId : undefined,
      status: patch.status ?? (patch.canonical ? "mapeado" : "pendiente"),
    });
  };

  const summary =
    preview?.alias_summary && (preview.alias_summary.total ?? 0) > 0
      ? preview.alias_summary
      : preview?.fields?.length
        ? {
            completed: preview.fields.filter((f) => f.value).length,
            critical_pending: preview.critical_pending_aliases?.length ?? 0,
            total: preview.fields.length,
          }
        : preview?.alias_summary ?? null;
  const hasCritical = (summary?.critical_pending ?? 0) > 0;
  const hasNonCritical = (summary?.non_critical_pending ?? 0) > 0;

  const pendingClassLabel: Record<string, string> = {
    completado: "Completado",
    critico: "Crítico",
    no_critico: "No crítico",
    ignorado: "Ignorado",
    no_aplica_etapa: "No aplica en esta etapa",
  };

  const pendingClassColor: Record<string, string> = {
    completado: "bg-emerald-500/15 text-emerald-700",
    critico: "bg-red-500/15 text-red-700",
    no_critico: "bg-amber-500/15 text-amber-800",
    ignorado: "bg-muted text-muted-foreground",
    no_aplica_etapa: "bg-slate-500/15 text-slate-600",
  };

  useEffect(() => {
    return () => {
      if (pdfUrl) revokeAuthenticatedFileUrl(pdfUrl);
    };
  }, [pdfUrl]);

  useEffect(() => {
    setPreview(null);
    if (pdfUrl) revokeAuthenticatedFileUrl(pdfUrl);
    setPdfUrl(null);
    setLastGenerate(null);
    setMissingFields([]);
    setCompletedFields([]);
  }, [formType, opportunityId]);

  useEffect(() => {
    if (!formType) return;
    let cancelled = false;
    void (async () => {
      const data = await loadAutofillState({});
      if (cancelled || !data) return;
      if (data.document_preview_available !== false) {
        const fieldMap: Record<string, string> = {};
        for (const f of data.fields) {
          if (f.key && f.value) fieldMap[f.key] = f.value;
        }
        await loadPdfPreview(fieldMap);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [formType, opportunityId, loadAutofillState, loadPdfPreview]);

  const hasTemplateLinked = Boolean(
    preview?.template_source || preview?.template_m365?.name || preview?.document_preview_available,
  );

  const generateDisabledReason = !preview
    ? "Genere primero la vista previa del documento."
    : !preview.generate_enabled
      ? preview.critical_pending_aliases?.length
        ? `Pendientes críticos: ${preview.critical_pending_aliases.join(", ")}`
        : "Complete los campos obligatorios del formulario antes de generar PDF listo para firma."
      : null;

  const downloadDisabledReason = !pdfUrl ? "La vista previa PDF aún no está disponible." : null;

  const allFieldRows = useMemo(() => {
    const byKey = new Map<string, import("@/lib/dgcp").DGCPFormPreviewField>();
    for (const f of preview?.fields ?? []) {
      const key = f.key ?? f.label;
      byKey.set(key, f);
    }
    for (const f of completedFields) {
      if (!byKey.has(f.key)) {
        byKey.set(f.key, {
          label: f.label,
          value: f.value,
          status: f.status ?? "completo",
          confidence: f.confidence,
          source: f.source,
          key: f.key,
        });
      }
    }
    for (const f of missingFields) {
      if (!byKey.has(f.key)) {
        byKey.set(f.key, {
          label: f.label,
          value: f.inferred_value ?? undefined,
          status: f.status ?? "pendiente",
          confidence: f.inference_confidence ?? undefined,
          source: f.suggested_source ?? undefined,
          key: f.key,
        });
      }
    }
    return Array.from(byKey.values());
  }, [preview?.fields, completedFields, missingFields]);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <PenLine className="h-4 w-4" />
            Autollenado — plantilla original
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            JAIOS descarga la plantilla real desde Microsoft 365, rellena los campos en su posición y genera una
            copia controlada PDF (LibreOffice) lista para firma y sello. La plantilla original no se modifica.
          </p>
          {summary && (
            <div className="grid gap-2 rounded border p-3 text-xs sm:grid-cols-3">
              <div>
                <span className="text-muted-foreground">Campos completados</span>
                <p className="font-semibold text-emerald-700">{summary.completed}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Críticos pendientes</span>
                <p className="font-semibold text-red-700">{summary.critical_pending}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Total campos</span>
                <p className="font-semibold">{summary.total}</p>
              </div>
            </div>
          )}
          {preview && hasCritical && (
            <div className="rounded border border-red-500/50 bg-red-500/10 p-3 text-sm text-red-800">
              Pendientes críticos: impiden marcar el documento como listo para firma. Complete manualmente o guarde
              borrador.
              {preview.critical_pending_aliases?.length ? (
                <p className="mt-1 text-xs">{preview.critical_pending_aliases.join(", ")}</p>
              ) : null}
            </div>
          )}
          {preview && !hasCritical && hasNonCritical && (
            <div className="rounded border border-amber-500/50 bg-amber-500/10 p-3 text-sm text-amber-900">
              Pendientes no críticos: puede generar PDF listo para firma; los campos aparecerán como [[PENDIENTE]] o
              vacíos.
            </div>
          )}
          {preview && (
            <p className="text-xs text-muted-foreground">
              Estado:{" "}
              <Badge variant={preview.ready_for_signature ? "default" : "secondary"}>
                {formatCompletionStatus(preview.completion_status)}
              </Badge>
              {!preview.ready_for_signature && " · Requiere revisión"}
            </p>
          )}
          <M365TemplateOperationalBanner compact className="mb-2" />
          {preview?.template_m365?.name && (
            <div className="rounded border bg-muted/30 p-2 text-xs space-y-1">
              <p>
                <span className="font-medium">Plantilla oficial:</span> {preview.template_m365.name}
              </p>
              <p className="text-muted-foreground">
                Fuente: {formatTemplateSource(preview.template_source_type, preview.template_cache_status)}
                {preview.template_status === "official" ? " · estado: oficial" : ""}
                {preview.template_status === "unavailable" ? (
                  <span className="text-destructive"> · Sin plantilla oficial</span>
                ) : null}
                {preview.template_status === "stub_blocked" ? (
                  <span className="text-destructive"> · Stub bloqueado</span>
                ) : null}
              </p>
              {preview.template_cache_status?.cached === false && (
                <p className="text-amber-700">
                  Caché no disponible —{" "}
                  <a href="/m365/cuentas" className="underline">
                    Reconectar M365
                  </a>{" "}
                  o sincronizar plantillas.
                </p>
              )}
              {preview.template_m365.web_url ? (
                <p>
                  <a href={preview.template_m365.web_url} target="_blank" rel="noopener noreferrer" className="underline">
                    Abrir en SharePoint
                  </a>
                </p>
              ) : null}
            </div>
          )}
          {preview && (preview.fields_detected ?? 0) > 0 && (
            <p className="text-xs text-muted-foreground">
              Campos detectados: {preview.fields_detected}
              {preview.unmapped_fields && preview.unmapped_fields.length > 0
                ? ` · No mapeados: ${preview.unmapped_fields.slice(0, 3).join("; ")}${preview.unmapped_fields.length > 3 ? "…" : ""}`
                : null}
            </p>
          )}
          {smartAutofill && requiredForms.length > 0 && (
            <div className="rounded border border-primary/30 bg-primary/5 p-3 space-y-2">
              <p className="text-xs font-semibold uppercase text-primary">Formularios requeridos por el proceso</p>
              <div className="flex flex-wrap gap-1">
                {requiredForms.map((f) => (
                  <Button
                    key={f.form_type}
                    size="sm"
                    variant={formType === f.form_type ? "default" : "outline"}
                    onClick={() => onFormTypeChange(f.form_type)}
                  >
                    {f.label}
                    <Badge variant="secondary" className="ml-1 text-[10px]">
                      {formatFormStatus(f.status)}
                    </Badge>
                  </Button>
                ))}
              </div>
            </div>
          )}
          {smartAutofill && completedFields.length > 0 && allFieldRows.length === 0 && (
            <div className="rounded border border-emerald-500/30 bg-emerald-500/5 p-3 space-y-2">
              <p className="text-xs font-semibold uppercase text-emerald-800">
                Campos completados ({completedFields.length})
              </p>
              <div className="grid gap-2 sm:grid-cols-2">
                {completedFields.map((field) => (
                  <div key={field.key} className="rounded border bg-background p-2 text-sm">
                    <p className="font-medium">{field.label}</p>
                    {field.value && <p className="text-xs text-muted-foreground truncate">{field.value}</p>}
                    {field.source && (
                      <p className="text-[10px] text-muted-foreground">Fuente: {field.source}</p>
                    )}
                    {field.confidence != null && (
                      <p className="text-[10px] text-muted-foreground">
                        Confianza: {Math.round(field.confidence * 100)}%
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          {smartAutofill && missingFields.length > 0 && (
            <div className="rounded border p-3 space-y-2">
              <p className="text-xs font-semibold uppercase text-muted-foreground">
                Campos faltantes ({missingFields.length})
              </p>
              {missingFields.map((field) => (
                <div key={field.key} className="flex flex-wrap items-end gap-2 text-sm">
                  <div className="min-w-[140px]">
                    <p className="font-medium">{field.label}</p>
                    {field.inference_confidence != null && field.inferred_value && (
                      <p className="text-xs text-muted-foreground">
                        Sugerido ({Math.round(field.inference_confidence * 100)}%): {field.inferred_value}
                      </p>
                    )}
                  </div>
                  <Input
                    className="max-w-xs"
                    placeholder={field.inferred_value ?? "Ingrese valor…"}
                    value={missingDraft[field.key] ?? field.inferred_value ?? ""}
                    onChange={(e) =>
                      setMissingDraft((prev) => ({ ...prev, [field.key]: e.target.value }))
                    }
                  />
                  <Button size="sm" variant="secondary" onClick={() => void resolveMissing(field)}>
                    Guardar
                  </Button>
                </div>
              ))}
            </div>
          )}
          {smartAutofill && libraryForms.length > 0 && (
            <div className="rounded border border-dashed p-3 space-y-2">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-medium text-muted-foreground">
                  Biblioteca SNCC / plantillas opcionales (no requeridas por este proceso)
                </p>
                <Button size="sm" variant="ghost" onClick={() => setLibraryOpen((v) => !v)}>
                  {libraryOpen ? "Ocultar biblioteca" : "Usar biblioteca SNCC"}
                </Button>
              </div>
              {libraryOpen && (
                <div className="flex flex-wrap gap-1 max-h-40 overflow-y-auto">
                  {libraryForms.map((t) => (
                    <Button
                      key={t.m365_file_id}
                      size="sm"
                      variant={formType === t.form_type ? "default" : "outline"}
                      className="h-auto text-xs"
                      onClick={() => onFormTypeChange(t.form_type)}
                    >
                      {t.detected_label || t.name.replace(".docx", "")}
                    </Button>
                  ))}
                </div>
              )}
            </div>
          )}
          {!templatesLoading && formType && !hasTemplateLinked && !loadingPreview && (
            <div className="rounded border border-amber-500/40 bg-amber-500/10 p-3 space-y-2 text-sm">
              <p className="font-medium">No hay plantilla vinculada para este formulario.</p>
              <p className="text-xs text-muted-foreground">
                Asocie una plantilla desde SharePoint/OneDrive, súbala al repositorio DGCP o elija otra desde la
                biblioteca SNCC.
              </p>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="outline" onClick={() => setLibraryOpen(true)}>
                  Usar biblioteca SNCC
                </Button>
                <Button size="sm" variant="outline" asChild>
                  <a href="/documentos/plantillas" target="_blank" rel="noopener noreferrer">
                    Asociar plantilla
                  </a>
                </Button>
                <Button size="sm" variant="outline" asChild>
                  <a href="/repositorios" target="_blank" rel="noopener noreferrer">
                    Subir plantilla
                  </a>
                </Button>
              </div>
            </div>
          )}
          {!smartAutofill && (
          <div className="flex flex-wrap gap-2">
            {categories.map((cat) => (
              <Button
                key={cat}
                size="sm"
                variant={categoryFilter === cat ? "default" : "outline"}
                onClick={() => setCategoryFilter(categoryFilter === cat ? null : cat)}
              >
                {CATEGORY_LABELS[cat] ?? cat}
              </Button>
            ))}
          </div>
          )}
          {!smartAutofill && (
          <div className="max-h-48 overflow-y-auto rounded border p-2">
            {templatesLoading ? (
              <p className="text-sm text-muted-foreground">Cargando plantillas M365…</p>
            ) : filteredTemplates.length === 0 ? (
              <p className="text-sm text-muted-foreground">No hay plantillas en el repositorio DGCP.</p>
            ) : (
              <div className="flex flex-wrap gap-1">
                {filteredTemplates.map((t) => (
                  <Button
                    key={t.m365_file_id}
                    size="sm"
                    variant={formType === t.form_type ? "default" : "ghost"}
                    className="h-auto max-w-full whitespace-normal text-left text-xs"
                    title={t.name}
                    onClick={() => onFormTypeChange(t.form_type)}
                  >
                    {t.detected_label || t.name.replace(".docx", "")}
                  </Button>
                ))}
              </div>
            )}
          </div>
          )}
          {!smartAutofill && (
          <p className="text-xs text-muted-foreground">
            {templates.length} plantilla(s) M365 indexadas · seleccionada: {formType || "—"}
          </p>
          )}
          {allFieldRows.length > 0 && (
            <div className="rounded border overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="p-2 text-left font-medium">Campo</th>
                    <th className="p-2 text-left font-medium">Valor</th>
                    <th className="p-2 text-left font-medium">Fuente</th>
                    <th className="p-2 text-left font-medium">Conf.</th>
                    <th className="p-2 text-left font-medium">Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {allFieldRows.map((f) => {
                    const key = f.key ?? f.label;
                    const isMissing = f.status === "pendiente" || f.status === "critico" || f.status === "faltante";
                    const isComplete = f.status === "completo";
                    return (
                      <tr key={key} className="border-t">
                        <td className="p-2 font-medium">{f.label}</td>
                        <td className="p-2 max-w-[200px] truncate">{overrides[key] ?? f.value ?? "—"}</td>
                        <td className="p-2 text-muted-foreground">{f.source ?? "—"}</td>
                        <td className="p-2">{f.confidence != null ? `${Math.round(f.confidence * 100)}%` : "—"}</td>
                        <td className="p-2">
                          <Badge variant={isComplete ? "default" : isMissing ? "destructive" : "secondary"}>
                            {isComplete ? "Completado" : isMissing ? "Falta" : pendingClassLabel[f.status ?? ""] ?? f.status}
                          </Badge>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => void handlePreview()} disabled={!formType || loadingPreview || loadingPdf} title={!formType ? "Seleccione un formulario SNCC" : undefined}>
              {(loadingPreview || loadingPdf) && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              <Eye className="mr-2 h-4 w-4" />
              Regenerar vista previa
            </Button>
            <Button variant="outline" onClick={() => void saveFieldData()} disabled={savingFields || !formType} title={!formType ? "Seleccione un formulario" : undefined}>
              {savingFields && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Guardar datos
            </Button>
            <Button variant="outline" onClick={() => setShowFieldEditor((v) => !v)} disabled={!preview} title={!preview ? "Genere la vista previa primero" : undefined}>
              Editar campos
            </Button>
            <Button variant="outline" onClick={() => setShowAliasMapper((v) => !v)} disabled={!preview?.alias_fields?.length} title={!preview?.alias_fields?.length ? "No hay alias Word en esta plantilla" : undefined}>
              Mapear alias Word
            </Button>
            <Button
              variant="secondary"
              onClick={() => void handleGenerate(false)}
              disabled={generating || !preview || !preview.generate_enabled}
              title={generateDisabledReason ?? undefined}
            >
              {generating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Generar PDF (listo firma)
            </Button>
            <Button
              variant="outline"
              onClick={() => void handleGenerate(true)}
              disabled={generating || !preview}
              title={!preview ? "Genere la vista previa antes de guardar borrador." : undefined}
            >
              Guardar borrador PDF
            </Button>
            <Button
              variant="outline"
              onClick={() => void handleDownload()}
              disabled={!pdfUrl}
              title={downloadDisabledReason ?? undefined}
            >
              <Download className="mr-2 h-4 w-4" />
              Descargar PDF
            </Button>
            {onSendReview && (
              <Button variant="outline" onClick={onSendReview} disabled={!lastGenerate}>
                <Send className="mr-2 h-4 w-4" />
                Enviar a revisión
              </Button>
            )}
          </div>
          {(generateDisabledReason || downloadDisabledReason) && (
            <div className="text-xs text-muted-foreground space-y-1">
              {generateDisabledReason && <p>PDF listo firma: {generateDisabledReason}</p>}
              {downloadDisabledReason && <p>Descarga: {downloadDisabledReason}</p>}
            </div>
          )}
          {error && <p className="text-sm text-destructive">{error}</p>}
          {lastGenerate?.filename && (
            <p className="text-xs text-muted-foreground">
              Guardado en expediente: {lastGenerate.filename}
            </p>
          )}
        </CardContent>
      </Card>

      {showAliasMapper && preview?.alias_fields && preview.alias_fields.length > 0 && (
        <Card className="border-dashed border-amber-500/40">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Mapeo alias Word → campo JAIOS</CardTitle>
            <div className="flex flex-wrap gap-2 pt-2">
              <Button
                size="sm"
                variant={mappingScope === "document" ? "default" : "outline"}
                onClick={() => setMappingScope("document")}
              >
                Este documento
              </Button>
              <Button
                size="sm"
                variant={mappingScope === "global" ? "default" : "outline"}
                onClick={() => setMappingScope("global")}
              >
                Global
              </Button>
              <Button
                size="sm"
                variant={mappingScope === "template" ? "default" : "outline"}
                disabled={!selectedTemplate}
                onClick={() => setMappingScope("template")}
              >
                Solo plantilla
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {preview.alias_fields.map((af) => (
              <div key={af.alias_normalized} className="grid gap-2 rounded border p-2 sm:grid-cols-5 sm:items-center">
                <div>
                  <p className="text-xs font-medium">{af.alias}</p>
                  <p className="text-[10px] text-muted-foreground">
                    {af.mapping_source} · {(af.confidence * 100).toFixed(0)}%
                  </p>
                  <span
                    className={cn(
                      "mt-1 inline-block rounded px-1.5 py-0.5 text-[10px]",
                      pendingClassColor[af.pending_class ?? "no_critico"],
                    )}
                  >
                    {pendingClassLabel[af.pending_class ?? "no_critico"] ?? af.pending_class}
                  </span>
                </div>
                {af.pending_class === "no_aplica_etapa" ? (
                  <p className="col-span-3 text-xs italic text-muted-foreground sm:col-span-4">
                    No aplica en esta etapa — no bloquea la generación.
                  </p>
                ) : (
                  <>
                <Input
                  className="h-8 text-xs"
                  placeholder="Valor manual"
                  defaultValue={overrides[af.alias_normalized] ?? af.value ?? ""}
                  onBlur={(e) => {
                    const val = e.target.value.trim();
                    setOverrides((prev) => ({ ...prev, [af.alias_normalized]: val }));
                    if (val) saveAliasOverride(af, { value: val });
                  }}
                />
                <select
                  className="h-8 rounded border bg-background px-2 text-xs"
                  defaultValue={af.canonical ?? ""}
                  onChange={(e) => {
                    const canonical = e.target.value || null;
                    saveAliasOverride(af, { canonical, status: canonical ? "mapeado" : "pendiente" });
                  }}
                >
                  <option value="">— Sin mapeo —</option>
                  {canonicalFields.map((c) => (
                    <option key={c.key} value={c.key}>
                      {c.label}
                    </option>
                  ))}
                </select>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => saveAliasOverride(af, { canonical: null, status: "ignorado" })}
                >
                  Ignorar
                </Button>
                  </>
                )}
              </div>
            ))}
            <Button size="sm" onClick={() => void handlePreview()}>
              Aplicar mapeos y regenerar vista previa
            </Button>
          </CardContent>
        </Card>
      )}

      {showFieldEditor && preview && (
        <Card className="border-dashed">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Campos detectados — edición manual</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">
            {preview.fields.map((f) => (
              <div key={f.label} className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">{f.label}</label>
                <Input
                  value={overrides[f.key ?? f.label] ?? f.value ?? ""}
                  placeholder={
                    f.status === "critico"
                      ? "Crítico — completar"
                      : f.status === "no_critico"
                        ? "No crítico — opcional"
                        : ""
                  }
                  className={cn(
                    f.status === "critico" && "border-red-500/50",
                    f.status === "no_critico" && "border-amber-500/50",
                  )}
                  onChange={(e) =>
                    setOverrides((prev) => ({
                      ...prev,
                      [f.key ?? f.label]: e.target.value,
                    }))
                  }
                />
                {f.source && <p className="text-[10px] text-muted-foreground">Fuente: {f.source}</p>}
              </div>
            ))}
            <div className="sm:col-span-2">
              <Button size="sm" onClick={() => void handlePreview()}>
                Aplicar cambios a vista previa
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {(pdfUrl || loadingPdf) && (
        <Card className="border-primary/30 overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <FileText className="h-4 w-4" />
              Documento resultante
            </CardTitle>
            {preview && (
              <Badge variant="outline">
                Confianza {(preview.overall_confidence * 100).toFixed(0)}%
              </Badge>
            )}
          </CardHeader>
          <CardContent className="p-0">
            {loadingPdf ? (
              <div className="flex h-[480px] items-center justify-center text-sm text-muted-foreground">
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                Generando vista previa…
              </div>
            ) : pdfUrl ? (
              <iframe
                title="Vista previa autollenado"
                src={pdfUrl}
                className="h-[min(70vh,720px)] w-full border-0 bg-muted/20"
              />
            ) : null}
          </CardContent>
        </Card>
      )}

      {preview && preview.missing.length > 0 && (
        <p className="text-xs text-muted-foreground">
          Campos pendientes visibles en documento: {preview.missing.join(", ")}
        </p>
      )}
    </div>
  );
}
