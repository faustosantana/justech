"use client";

import { Bell, ClipboardCheck, Download, FileStack, Loader2, Package, PenLine, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { DocumentPreviewModal } from "@/components/dgcp/document-preview-modal";
import { DGCPFinalizationPanel } from "@/components/dgcp/dgcp-finalization-panel";
import { RealExpedientePanel } from "@/components/dgcp/real-expediente-panel";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiClient } from "@/lib/api";
import {
  CHECKLIST_STATUS_LABELS,
  COMPLIANCE_STATUS_LABELS,
  EXPEDIENTE_STATUS_LABELS,
  PROCESS_DOC_ROLE_LABELS,
  PROCESS_PRIORITY_LABELS,
  REQUIREMENT_TYPE_LABELS,
  type DGCPChecklist,
  type DGCPChecklistItem,
  type DGCPBidAlerts,
  type DGCPBidPackage,
  type DGCPDocumentMatches,
  type DGCPExpedienteStatus,
  type DGCPFormPreview,
  type DGCPProcessDocuments,
  type DGCPRequirements,
  type DGCPOpportunity,
  type DGCPEconomicOfferStatus,
  isDGCPOperationalInterest,
} from "@/lib/dgcp";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

const PROCESS_DOC_SOURCES = new Set(["portal", "dgcp_api", "portal_text", "process_file", "reference"]);
const PLIEGO_ROLES = new Set(["pliego", "tdr", "terminos_referencia", "ficha_tecnica", "anexo"]);

function hasChecklistEvidence(item: DGCPChecklistItem): boolean {
  return Boolean(
    item.document_id ||
      item.knowledge_asset_id ||
      item.process_document_id ||
      item.status === "no_aplica",
  );
}

function effectiveChecklistStatus(item: DGCPChecklistItem): string {
  if (
    (item.status === "validado_manual" || item.status === "encontrado_vigente") &&
    !hasChecklistEvidence(item)
  ) {
    return "faltante";
  }
  return item.status;
}

function formatNoteTimestamp(iso: string): string {
  try {
    return new Intl.DateTimeFormat("es-DO", { dateStyle: "short", timeStyle: "short" }).format(
      new Date(iso),
    );
  } catch {
    return iso;
  }
}

function apiErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error && err.message !== "UNAUTHORIZED") return err.message;
  return fallback;
}

interface Props {
  opportunity: DGCPOpportunity;
  activeTab: string;
  interested: boolean;
  onOpportunityUpdated?: (opportunity: DGCPOpportunity) => void;
  onAnalysisUpdate?: (
    bid: DGCPBidPackage,
    checklist: DGCPChecklist,
    status: string | null,
  ) => void;
}

function InterestGate() {
  return (
    <Card className="border-warning/30 bg-amber-500/10">
      <CardContent className="py-6 text-sm space-y-2">
        <p className="font-medium">Análisis operativo no habilitado</p>
        <p className="text-muted-foreground">
          En la pestaña <strong>Resumen</strong>, pulse <strong>Mostrar interés</strong> antes de
          analizar requisitos, ver documentos del proceso, validar, agregar notas o crear tareas.
        </p>
      </CardContent>
    </Card>
  );
}

export function OpportunityBidSection({
  opportunity,
  activeTab,
  interested,
  onOpportunityUpdated,
  onAnalysisUpdate,
}: Props) {
  const [requirements, setRequirements] = useState<DGCPRequirements | null>(null);
  const [checklist, setChecklist] = useState<DGCPChecklist | null>(null);
  const [bidPackage, setBidPackage] = useState<DGCPBidPackage | null>(null);
  const [matches, setMatches] = useState<DGCPDocumentMatches | null>(null);
  const [formPreview, setFormPreview] = useState<DGCPFormPreview | null>(null);
  const [processDocs, setProcessDocs] = useState<DGCPProcessDocuments | null>(null);
  const [alerts, setAlerts] = useState<DGCPBidAlerts | null>(null);
  const [expedienteStatus, setExpedienteStatus] = useState<DGCPExpedienteStatus | null>(null);
  const [analysisWarnings, setAnalysisWarnings] = useState<string[]>([]);
  const [selectedFormType, setSelectedFormType] = useState("SNCC.F042");
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [expedienteBusy, setExpedienteBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewItemId, setPreviewItemId] = useState<string | null>(null);
  const [validationItemId, setValidationItemId] = useState<string | null>(null);
  const [validationNote, setValidationNote] = useState("");
  const [validationStatus, setValidationStatus] = useState("validado_manual");
  const [validationExpiry, setValidationExpiry] = useState("");
  const [validationBusy, setValidationBusy] = useState(false);
  const [taskBusyId, setTaskBusyId] = useState<string | null>(null);
  const [noteItemId, setNoteItemId] = useState<string | null>(null);
  const [noteText, setNoteText] = useState("");
  const [noteBusy, setNoteBusy] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [associateItemId, setAssociateItemId] = useState<string | null>(null);
  const [associateBusy, setAssociateBusy] = useState(false);
  const [economicOfferStatus, setEconomicOfferStatus] = useState<DGCPEconomicOfferStatus | null>(null);

  const analyzed = Boolean(requirements?.analyzed_at ?? bidPackage?.analyzed_at);

  const load = useCallback(async () => {
    if (!interested) return;
    setLoading(true);
    setError(null);
    try {
      const [req, chk, pkg, mat] = await Promise.all([
        apiClient.getDGCPRequirements(opportunity.id),
        apiClient.getDGCPChecklist(opportunity.id),
        apiClient.getDGCPBidPackage(opportunity.id),
        apiClient.getDGCPDocumentMatches(opportunity.id),
      ]);
      setRequirements(req);
      setChecklist(chk);
      setBidPackage(pkg);
      setMatches(mat);

      if (req.analyzed_at ?? pkg.analyzed_at) {
        const [proc, alertRes, exp, eco] = await Promise.all([
          apiClient.getDGCPProcessDocuments(opportunity.id).catch(() => null),
          apiClient.getDGCPAlerts(opportunity.id).catch(() => null),
          apiClient.getDGCPExpedienteStatus(opportunity.id).catch(() => null),
          apiClient.getDGCPEconomicOfferStatus(opportunity.id).catch(() => null),
        ]);
        if (proc) setProcessDocs(proc);
        if (alertRes) setAlerts(alertRes);
        if (exp) setExpedienteStatus(exp);
        if (eco) setEconomicOfferStatus(eco);
      }
    } catch (err) {
      const message =
        err instanceof Error && err.message === "UNAUTHORIZED"
          ? "Sesión expirada. Vuelva a iniciar sesión."
          : "No se pudo cargar el análisis. Ejecute «Analizar requisitos».";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [interested, opportunity.id]);

  useEffect(() => {
    if (!interested) return;
    if (activeTab !== "resumen" && activeTab !== "historial" && activeTab !== "tareas") {
      void load();
    }
  }, [activeTab, interested, load]);

  const handleAnalyze = async () => {
    setAnalyzing(true);
    setError(null);
    try {
      const result = await apiClient.analyzeDGCPRequirements(opportunity.id);
      setRequirements(result.requirements);
      setChecklist(result.checklist);
      setBidPackage(result.bid_package);
      setMatches(result.document_matches);
      if ("process_documents" in result && Array.isArray(result.process_documents)) {
        setProcessDocs({
          opportunity_id: opportunity.id,
          items: result.process_documents as DGCPProcessDocuments["items"],
          total: result.process_documents.length,
        });
      }
      if ("alerts" in result && Array.isArray(result.alerts)) {
        setAlerts({
          opportunity_id: opportunity.id,
          alerts: result.alerts as DGCPBidAlerts["alerts"],
          total: result.alerts.length,
        });
      }
      if ("analysis_warnings" in result && Array.isArray(result.analysis_warnings)) {
        setAnalysisWarnings(result.analysis_warnings as string[]);
      }
      const [exp, eco] = await Promise.all([
        apiClient.getDGCPExpedienteStatus(opportunity.id).catch(() => null),
        apiClient.getDGCPEconomicOfferStatus(opportunity.id).catch(() => null),
      ]);
      if (exp) setExpedienteStatus(exp);
      if (eco) setEconomicOfferStatus(eco);
      onAnalysisUpdate?.(result.bid_package, result.checklist, exp?.expediente_status ?? null);
    } catch (err) {
      setError(apiErrorMessage(err, "Error al analizar requisitos."));
    } finally {
      setAnalyzing(false);
    }
  };

  const handleCreateTask = async (itemId: string) => {
    setTaskBusyId(itemId);
    setError(null);
    setActionSuccess(null);
    try {
      const result = await apiClient.createDGCPChecklistTask(opportunity.id, itemId);
      setChecklist((prev) =>
        prev
          ? {
              ...prev,
              items: prev.items.map((item) =>
                item.id === itemId ? { ...item, task_id: result.task_id } : item,
              ),
            }
          : prev,
      );
      setActionSuccess(result.existing ? "Tarea existente — use «Ver tarea»." : "Tarea creada correctamente.");
      await load();
      return result;
    } catch (err) {
      setError(apiErrorMessage(err, "No se pudo crear la tarea."));
      throw new Error("task_create_failed");
    } finally {
      setTaskBusyId(null);
    }
  };

  const handleAddNote = async () => {
    if (!noteItemId || !noteText.trim()) return;
    setNoteBusy(true);
    setError(null);
    setActionSuccess(null);
    try {
      const result = await apiClient.addDGCPChecklistNote(opportunity.id, noteItemId, noteText.trim());
      setChecklist(result.checklist);
      setNoteItemId(null);
      setNoteText("");
      setActionSuccess("Nota guardada en base de datos.");
      await load();
    } catch (err) {
      setError(apiErrorMessage(err, "No se pudo guardar la nota."));
    } finally {
      setNoteBusy(false);
    }
  };

  const handleManualValidation = async () => {
    if (!validationItemId) return;
    setValidationBusy(true);
    setError(null);
    try {
      const result = await apiClient.manualValidateDGCPRequirement(opportunity.id, validationItemId, {
        status: validationStatus,
        note: validationNote,
        expiration_date: validationExpiry || undefined,
      });
      setChecklist(result.checklist);
      setBidPackage(result.bid_package);
      setExpedienteStatus((prev) =>
        prev ? { ...prev, expediente_status: result.expediente_status } : prev,
      );
      onAnalysisUpdate?.(result.bid_package, result.checklist, result.expediente_status);
      setValidationItemId(null);
      setValidationNote("");
      setValidationExpiry("");
      setActionSuccess(`Validación guardada — ${result.bid_package.preparation_pct}% preparación.`);
      await load();
    } catch (err) {
      setError(apiErrorMessage(err, "No se pudo guardar la validación manual."));
    } finally {
      setValidationBusy(false);
    }
  };

  const handleMarkNoAplica = async (itemId: string) => {
    setError(null);
    try {
      const result = await apiClient.manualValidateDGCPRequirement(opportunity.id, itemId, {
        status: "no_aplica",
        note: "Marcado como no aplica por el usuario.",
      });
      setChecklist(result.checklist);
      setBidPackage(result.bid_package);
      onAnalysisUpdate?.(result.bid_package, result.checklist, result.expediente_status);
      setActionSuccess("Requisito marcado como no aplica.");
    } catch (err) {
      setError(apiErrorMessage(err, "No se pudo marcar como no aplica."));
    }
  };

  const handleAssociateDocument = async (documentId?: string, knowledgeAssetId?: string) => {
    if (!associateItemId) return;
    setAssociateBusy(true);
    setError(null);
    try {
      const result = await apiClient.associateDGCPChecklistDocument(opportunity.id, associateItemId, {
        document_id: documentId,
        knowledge_asset_id: knowledgeAssetId,
      });
      setChecklist(result.checklist);
      setBidPackage(result.bid_package);
      onAnalysisUpdate?.(result.bid_package, result.checklist, result.expediente_status);
      setAssociateItemId(null);
      setActionSuccess("Documento asociado al requisito.");
    } catch (err) {
      setError(apiErrorMessage(err, "No se pudo asociar el documento."));
    } finally {
      setAssociateBusy(false);
    }
  };

  const handleUploadForRequirement = async (file: File) => {
    if (!associateItemId) return;
    setAssociateBusy(true);
    setError(null);
    try {
      const result = await apiClient.uploadDGCPChecklistDocument(opportunity.id, associateItemId, file);
      setChecklist(result.checklist);
      setBidPackage(result.bid_package);
      onAnalysisUpdate?.(result.bid_package, result.checklist, result.expediente_status);
      setAssociateItemId(null);
      setActionSuccess("Documento subido y asociado.");
    } catch (err) {
      setError(apiErrorMessage(err, "No se pudo subir el documento."));
    } finally {
      setAssociateBusy(false);
    }
  };

  const handlePreviewSncc = async (formType: string) => {
    const preview = await apiClient.previewDGCPForm(opportunity.id, formType);
    setFormPreview(preview);
  };

  const handleAutofillPreview = async () => {
    const preview = await apiClient.autofillDGCPForm(opportunity.id, selectedFormType);
    setFormPreview(preview);
  };

  const handleGenerateForm = async () => {
    await apiClient.generateDGCPForm(opportunity.id, selectedFormType);
    await load();
  };

  const handlePrepareExpediente = async () => {
    setExpedienteBusy(true);
    setError(null);
    try {
      await apiClient.prepareDGCPExpediente(opportunity.id);
      const exp = await apiClient.getDGCPExpedienteStatus(opportunity.id);
      setExpedienteStatus(exp);
      await load();
    } catch {
      setError("No se pudo preparar el expediente.");
    } finally {
      setExpedienteBusy(false);
    }
  };

  const handleDownloadExpediente = async () => {
    setExpedienteBusy(true);
    try {
      await apiClient.downloadDGCPExpediente(
        opportunity.id,
        expedienteStatus?.opportunity_code
          ? `expediente_${expedienteStatus.opportunity_code}.zip`
          : undefined,
      );
    } catch {
      setError("No se pudo descargar el expediente.");
    } finally {
      setExpedienteBusy(false);
    }
  };

  const handleMarkReady = async () => {
    setExpedienteBusy(true);
    try {
      const exp = await apiClient.markDGCPExpedienteReady(opportunity.id);
      setExpedienteStatus(exp);
    } catch {
      setError("Marque «Preparar expediente» antes de enviar a revisión.");
    } finally {
      setExpedienteBusy(false);
    }
  };

  if (activeTab === "resumen" || activeTab === "historial" || activeTab === "tareas") {
    return null;
  }

  if (!interested) {
    return <InterestGate />;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <Button onClick={() => void handleAnalyze()} disabled={analyzing || !interested}>
          {analyzing ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-2 h-4 w-4" />
          )}
          Analizar requisitos
        </Button>
        <Button variant="outline" onClick={() => void load()} disabled={loading}>
          Actualizar
        </Button>
      </div>

      {analyzed && economicOfferStatus && (
        <div className="rounded-lg border border-primary/20 bg-primary/5 px-4 py-3 text-sm flex flex-wrap items-center gap-3 justify-between">
          <div>
            <p className="font-medium">Oferta económica — {economicOfferStatus.display_status}</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              {economicOfferStatus.document_title
                ? `Documento: ${economicOfferStatus.document_title}`
                : economicOfferStatus.draft_status
                  ? `Borrador: ${economicOfferStatus.draft_status}`
                  : "Suba la cotización PDF manualmente desde el checklist (Asociar / subir)"}
              {economicOfferStatus.preparation_pct != null
                ? ` · Preparación ${economicOfferStatus.preparation_pct.toFixed(0)}%`
                : ""}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {economicOfferStatus.task_id && (
              <Button size="sm" variant="outline" asChild>
                <Link href={`/tasks/${economicOfferStatus.task_id}`}>Ver tarea</Link>
              </Button>
            )}
          </div>
        </div>
      )}

      {analysisWarnings.length > 0 && (
        <div className="rounded-lg border border-warning/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-800 dark:text-amber-200">
          {analysisWarnings.map((w) => (
            <p key={w}>{w}</p>
          ))}
        </div>
      )}

      {actionSuccess && (
        <p className="text-sm text-success rounded-lg border border-success/30 px-3 py-2">
          {actionSuccess}
        </p>
      )}

      {error && (
        <p className="text-sm text-destructive rounded-lg border border-destructive/30 px-3 py-2">{error}</p>
      )}

      {loading && !requirements ? (
        <p className="text-sm text-muted-foreground">Cargando análisis…</p>
      ) : (
        <>
          {activeTab === "requisitos" && (
            analyzed && checklist && matches ? (
              <ComplianceBoardTab
                opportunityId={opportunity.id}
                checklist={checklist}
                matches={matches}
                warnings={analysisWarnings}
                onPreview={(itemId) => setPreviewItemId(itemId)}
                onValidate={(itemId) => {
                  setValidationItemId(itemId);
                  setValidationStatus("validado_manual");
                }}
                onCreateTask={handleCreateTask}
                taskBusyId={taskBusyId}
                onAddNote={(itemId) => {
                  setNoteItemId(itemId);
                  setNoteText("");
                }}
                onAssociate={setAssociateItemId}
                onMarkNoAplica={handleMarkNoAplica}
              />
            ) : (
              <EmptyAnalysisHint />
            )
          )}
          {activeTab === "documentos-proceso" && (
            analyzed ? (
              processDocs ? (
                <ProcessDocumentsTab documents={processDocs} opportunityId={opportunity.id} />
              ) : (
                <EmptyAnalysisHint message="Sin documentos del proceso indexados todavía." />
              )
            ) : (
              <EmptyAnalysisHint />
            )
          )}
          {activeTab === "documentos" && matches && (
            analyzed ? (
              <DocumentosJustechTab
                matches={matches}
                checklist={checklist}
                onPreview={setPreviewItemId}
                onValidate={(itemId) => {
                  setValidationItemId(itemId);
                  setValidationStatus("validado_manual");
                }}
                onAddNote={(itemId) => {
                  setNoteItemId(itemId);
                  setNoteText("");
                }}
                onCreateTask={handleCreateTask}
                taskBusyId={taskBusyId}
              />
            ) : (
              <EmptyAnalysisHint />
            )
          )}
          {activeTab === "checklist" && checklist && (
            analyzed && checklist.total > 0 ? (
              <ChecklistTab
                opportunityId={opportunity.id}
                checklist={checklist}
                onCreateTask={handleCreateTask}
                onPreviewSncc={handlePreviewSncc}
                onPreview={setPreviewItemId}
                onValidate={(itemId) => {
                  setValidationItemId(itemId);
                  setValidationStatus("validado_manual");
                }}
                taskBusyId={taskBusyId}
                onAddNote={(itemId) => {
                  setNoteItemId(itemId);
                  setNoteText("");
                }}
                onAssociate={setAssociateItemId}
                onMarkNoAplica={handleMarkNoAplica}
              />
            ) : (
              <EmptyAnalysisHint />
            )
          )}
          {activeTab === "expediente" && bidPackage && (
            analyzed ? (
              <ExpedienteTab
                opportunityId={opportunity.id}
                checklist={checklist}
                bidPackage={bidPackage}
                expedienteStatus={expedienteStatus}
                busy={expedienteBusy}
                onPrepare={() => void handlePrepareExpediente()}
                onDownload={() => void handleDownloadExpediente()}
                onMarkReady={() => void handleMarkReady()}
                onFinalizationUpdated={() => void load()}
              />
            ) : (
              <EmptyAnalysisHint />
            )
          )}
          {activeTab === "autollenado" && (
            analyzed ? (
              <AutollenadoTab
                formType={selectedFormType}
                onFormTypeChange={setSelectedFormType}
                onPreview={() => void handleAutofillPreview()}
                onGenerate={() => void handleGenerateForm()}
                preview={formPreview}
              />
            ) : (
              <EmptyAnalysisHint />
            )
          )}
          {activeTab === "alertas" && (
            analyzed && alerts ? (
              <AlertasTab alerts={alerts} />
            ) : (
              <EmptyAnalysisHint />
            )
          )}
          {activeTab === "riesgos" && checklist && (
            analyzed && checklist.total > 0 ? (
              <RiesgosTab checklist={checklist} opportunity={opportunity} />
            ) : (
              <EmptyAnalysisHint />
            )
          )}
        </>
      )}

      <DocumentPreviewModal
        open={Boolean(previewItemId)}
        onOpenChange={(open) => !open && setPreviewItemId(null)}
        opportunityId={opportunity.id}
        itemId={previewItemId ?? ""}
        checklistItem={checklist?.items.find((i) => i.id === previewItemId) ?? null}
        onValidated={() => void load().then(() => setActionSuccess("Validación guardada desde visor."))}
        onNoted={() => void load().then(() => setActionSuccess("Nota guardada desde visor."))}
        onTaskCreated={() => void load().then(() => setActionSuccess("Tarea creada desde visor."))}
      />

      {associateItemId && (
        <AssociateDocumentModal
          busy={associateBusy}
          onClose={() => setAssociateItemId(null)}
          onPickKnowledge={(id) => void handleAssociateDocument(undefined, id)}
          onPickDocument={(id) => void handleAssociateDocument(id, undefined)}
          onUpload={(file) => void handleUploadForRequirement(file)}
        />
      )}

      {validationItemId && (() => {
        const validationItem = checklist?.items.find((i) => i.id === validationItemId);
        const lacksDoc = validationItem ? !hasChecklistEvidence(validationItem) : true;
        return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <Card className="w-full max-w-lg border-primary/30">
            <CardHeader>
              <CardTitle className="text-base">Validar requisito</CardTitle>
              {validationItem && (
                <p className="text-sm text-muted-foreground">{validationItem.requirement}</p>
              )}
            </CardHeader>
            <CardContent className="space-y-3">
            {lacksDoc && validationStatus === "validado_manual" && (
              <p className="text-sm text-amber-700 dark:text-amber-300 rounded border border-amber-500/30 px-3 py-2">
                No hay documento asociado. Use «No aplica» o adjunte evidencia antes de marcar como validado.
              </p>
            )}
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <Label>Estado</Label>
                <select
                  className="brand-input h-9 py-1"
                  value={validationStatus}
                  onChange={(e) => setValidationStatus(e.target.value)}
                >
                  <option value="validado_manual">Validado manualmente</option>
                  <option value="encontrado_vencido">Marcar vencido</option>
                  <option value="requiere_revision">Requiere revisión</option>
                  <option value="no_aplica">No aplica</option>
                </select>
              </div>
              <div className="space-y-1">
                <Label>Vencimiento (opcional)</Label>
                <Input type="date" value={validationExpiry} onChange={(e) => setValidationExpiry(e.target.value)} />
              </div>
            </div>
            <div className="space-y-1">
              <Label>Nota</Label>
              <Input
                value={validationNote}
                onChange={(e) => setValidationNote(e.target.value)}
                placeholder="Ej.: Revisado por Fausto. Certificación DGII vigente hasta 14/05/2026."
              />
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={() => void handleManualValidation()}
                disabled={validationBusy || (lacksDoc && validationStatus === "validado_manual")}
              >
                Guardar validación
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setValidationItemId(null)}>
                Cancelar
              </Button>
            </div>
          </CardContent>
          </Card>
        </div>
        );
      })()}

      {noteItemId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <Card className="w-full max-w-lg border-primary/30">
            <CardHeader>
              <CardTitle className="text-base">Agregar nota</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
            <div className="space-y-1">
              <Label>Nota</Label>
              <Input
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                placeholder="Se guardará con autor, fecha e historial."
              />
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={() => void handleAddNote()} disabled={noteBusy || !noteText.trim()}>
                Guardar nota
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setNoteItemId(null)}>
                Cancelar
              </Button>
            </div>
          </CardContent>
          </Card>
        </div>
      )}

      {formPreview && (
        <Card className="border-primary/30">
          <CardHeader>
            <CardTitle className="text-base">
              Vista previa — {formPreview.form_type}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p className="text-muted-foreground">{formPreview.note}</p>
            <p className="text-xs">
              Confianza general: {(formPreview.overall_confidence * 100).toFixed(0)}%
            </p>
            <div className="divide-y rounded border">
              {formPreview.fields.map((f) => (
                <div key={f.label} className="flex flex-wrap justify-between gap-2 px-3 py-2">
                  <div>
                    <span className="text-muted-foreground">{f.label}</span>
                    {f.source && (
                      <p className="text-[10px] text-muted-foreground">Fuente: {f.source}</p>
                    )}
                  </div>
                  <div className="text-right">
                    <span className={f.status === "pendiente" ? "text-amber-500" : "font-medium"}>
                      {f.value ?? "Pendiente"}
                    </span>
                    <p className="text-[10px] text-muted-foreground">
                      {(f.confidence * 100).toFixed(0)}% · {f.status}
                    </p>
                  </div>
                </div>
              ))}
            </div>
            {formPreview.warnings.length > 0 && (
              <ul className="text-xs text-warning list-disc pl-4">
                {formPreview.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            )}
            {formPreview.generate_enabled && (
              <Button variant="outline" size="sm" onClick={() => void handleGenerateForm()}>
                Generar copia controlada
              </Button>
            )}
            {!formPreview.generate_enabled && (
              <Button variant="outline" size="sm" disabled title="Use la pestaña Autollenado para generar">
                Generar documento (Autollenado)
              </Button>
            )}
            <Button variant="ghost" size="sm" onClick={() => setFormPreview(null)}>
              Cerrar vista previa
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function EmptyAnalysisHint({ message }: { message?: string }) {
  return (
    <p className="text-sm text-muted-foreground rounded-lg border px-3 py-4">
      {message ??
        "Aún no hay análisis guardado. Pulse «Analizar requisitos» para generar checklist, expediente y cruces documentales."}
    </p>
  );
}

function ComplianceBoardTab({
  opportunityId,
  checklist,
  matches,
  warnings,
  onPreview,
  onValidate,
  onCreateTask,
  taskBusyId,
  onAddNote,
  onAssociate,
  onMarkNoAplica,
}: {
  opportunityId: string;
  checklist: DGCPChecklist;
  matches: DGCPDocumentMatches;
  warnings: string[];
  onPreview: (itemId: string) => void;
  onValidate: (itemId: string) => void;
  onCreateTask: (itemId: string) => Promise<{ task_id: string; existing?: boolean }>;
  taskBusyId: string | null;
  onAddNote: (itemId: string) => void;
  onAssociate: (itemId: string) => void;
  onMarkNoAplica: (itemId: string) => void;
}) {
  const matchByKey = Object.fromEntries(matches.matches.map((m) => [m.requirement_key, m]));
  const itemByKey = Object.fromEntries(checklist.items.map((i) => [i.requirement_key, i]));

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Tablero de cumplimiento — cada fila es un requisito extraído del proceso, no un documento del
        repositorio.
      </p>
      {warnings.length > 0 && (
        <div className="rounded-lg border border-warning/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-800 dark:text-amber-200">
          {warnings.map((w) => (
            <p key={w}>{w}</p>
          ))}
        </div>
      )}
      <div className="grid gap-3">
        {checklist.items.map((item) => {
          const match = matchByKey[item.requirement_key];
          return (
            <div
              key={item.id}
              className="rounded-lg border bg-card px-4 py-3 grid gap-3 lg:grid-cols-[1fr_auto] lg:items-start"
            >
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <ComplianceIcon status={item.status} item={item} />
                  <p className="font-medium">{item.requirement}</p>
                  <StatusPill status={item.status} item={item} />
                </div>
                <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                  <span>{REQUIREMENT_TYPE_LABELS[item.tipo] ?? item.tipo}</span>
                  <span>{item.mandatory ? "Obligatorio" : "Opcional"}</span>
                  {match?.match_source && (
                    <span>
                      Fuente:{" "}
                      {match.match_source === "knowledge_repository"
                        ? "JustechAI"
                        : match.match_source === "knowledge_template"
                          ? "Plantilla"
                          : match.match_source === "document_repository"
                            ? "JAIOS Docs"
                            : "Proceso DGCP"}
                    </span>
                  )}
                </div>
                {(match?.notes ?? item.notes) && (
                  <p className="text-xs rounded bg-muted/50 px-2 py-1">{match?.notes ?? item.notes}</p>
                )}
                {item.manual_validation && typeof item.manual_validation === "object" && (
                  <p className="text-xs text-success ">
                    Validación manual: {(item.manual_validation as { note?: string }).note ?? "Registrada"}
                  </p>
                )}
                {match?.validity_analysis && (
                  <p className="text-xs text-muted-foreground">
                    Evidencia:{" "}
                    {String((match.validity_analysis as { evidence_text?: string }).evidence_text ?? "—")}
                  </p>
                )}
                {item.note_history && item.note_history.length > 0 && (
                  <div className="text-xs space-y-1 rounded bg-muted/30 px-2 py-1">
                    {item.note_history.slice(-3).reverse().map((entry, idx) => (
                      <p key={`${entry.created_at}-${idx}`}>
                        <span className="font-medium">{entry.author}</span>{" "}
                        <span className="text-muted-foreground">
                          {formatNoteTimestamp(entry.created_at)}
                        </span>
                        <br />
                        {entry.note}
                      </p>
                    ))}
                  </div>
                )}
                {item.recommended_action && (
                  <p className="text-xs text-primary">Acción: {item.recommended_action}</p>
                )}
              </div>
              <div className="space-y-2 text-sm lg:text-right min-w-[180px]">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Documento asociado</p>
                  <p className="font-medium">{match?.document_title ?? "Ninguno"}</p>
                </div>
                <RequirementActions
                  item={item}
                  taskBusy={taskBusyId === item.id}
                  onPreview={() => onPreview(item.id)}
                  onValidate={() => onValidate(item.id)}
                  onAddNote={() => onAddNote(item.id)}
                  onCreateTask={() => void onCreateTask(item.id)}
                  onAssociate={() => onAssociate(item.id)}
                  onMarkNoAplica={() => onMarkNoAplica(item.id)}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ComplianceIcon({
  status,
  item,
}: {
  status: string;
  item?: DGCPChecklistItem;
}) {
  const effectiveStatus = item ? effectiveChecklistStatus(item) : status;
  const icon =
    effectiveStatus === "encontrado_vigente" || effectiveStatus === "validado_manual"
      ? "🟢"
      : effectiveStatus === "requiere_revision" ||
          effectiveStatus === "encontrado_sin_fecha" ||
          effectiveStatus === "encontrado_sin_analizar"
        ? "🟡"
        : effectiveStatus === "requiere_completado"
          ? "🟠"
          : effectiveStatus === "faltante" || effectiveStatus === "encontrado_vencido"
            ? "🔴"
            : effectiveStatus === "no_aplica"
              ? "⚫"
              : "⚪";
  return <span aria-hidden>{icon}</span>;
}

function RequirementActions({
  item,
  taskBusy,
  onPreview,
  onValidate,
  onAddNote,
  onCreateTask,
  onAssociate,
  onMarkNoAplica,
}: {
  item: DGCPChecklistItem;
  taskBusy?: boolean;
  onPreview: () => void;
  onValidate: () => void;
  onAddNote: () => void;
  onCreateTask: () => void;
  onAssociate: () => void;
  onMarkNoAplica: () => void;
}) {
  const hasDoc = Boolean(
    item.document_id || item.document_title || item.knowledge_asset_id || item.process_document_id,
  );
  const isFaltante = effectiveChecklistStatus(item) === "faltante" || !hasDoc;
  const isOferta = item.requirement_key === "oferta_economica";
  return (
    <div className="flex flex-wrap gap-1 justify-end">
      {hasDoc && (
        <>
          <Button size="sm" variant="outline" onClick={onPreview}>
            Ver documento
          </Button>
          <Button size="sm" variant="ghost" onClick={onPreview}>
            Descargar
          </Button>
        </>
      )}
      {isFaltante && (
        <Button size="sm" variant="outline" onClick={onAssociate}>
          {isOferta ? "Adjuntar" : "Asociar / subir"}
        </Button>
      )}
      <Button size="sm" variant="ghost" onClick={onValidate}>
        Validar
      </Button>
      <Button size="sm" variant="ghost" onClick={onAddNote}>
        Agregar nota
      </Button>
      <Button size="sm" variant="ghost" onClick={onMarkNoAplica}>
        No aplica
      </Button>
      {item.task_id ? (
        <Button size="sm" variant="secondary" asChild>
          <Link href={`/tasks/${item.task_id}`}>Ver tarea</Link>
        </Button>
      ) : (
        <Button size="sm" variant="outline" onClick={onCreateTask} disabled={taskBusy}>
          {taskBusy ? "Creando…" : "Crear tarea"}
        </Button>
      )}
      {item.completable && item.form_type && (
        <Button size="sm" variant="ghost" asChild>
          <span className="text-xs">Autollenado</span>
        </Button>
      )}
    </div>
  );
}

function DocumentosJustechTab({
  matches,
  checklist,
  onPreview,
  onValidate,
  onAddNote,
  onCreateTask,
  taskBusyId,
}: {
  matches: DGCPDocumentMatches;
  checklist: DGCPChecklist | null;
  onPreview: (itemId: string) => void;
  onValidate: (itemId: string) => void;
  onAddNote: (itemId: string) => void;
  onCreateTask: (itemId: string) => Promise<{ task_id: string; existing?: boolean }>;
  taskBusyId: string | null;
}) {
  const justechMatches = matches.matches.filter(
    (m) =>
      m.match_source === "knowledge_repository" ||
      m.match_source === "document_repository" ||
      m.match_source === "knowledge_template",
  );
  const itemByKey = Object.fromEntries((checklist?.items ?? []).map((i) => [i.requirement_key, i]));

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Documentos corporativos Justech (RPE, DGII, TSS, SNCC, ofertas, cartas) usados para cumplir
        requisitos — no confundir con pliego/TDR del comprador (pestaña Docs. Proceso).
      </p>
      <div className="grid gap-4">
        {justechMatches.map((m) => {
          const item = itemByKey[m.requirement_key];
          return (
            <Card key={m.requirement_key} className="overflow-hidden">
              <CardContent className="p-0">
                <div className="grid md:grid-cols-2 divide-y md:divide-y-0 md:divide-x">
                  <div className="p-4 space-y-1">
                    <p className="text-xs font-medium uppercase text-muted-foreground">Requisito</p>
                    <p className="font-semibold">{m.requirement_label}</p>
                    <StatusPill status={m.status} item={item} />
                  </div>
                  <div className="p-4 space-y-2 bg-muted/20">
                    <p className="text-xs font-medium uppercase text-muted-foreground">Documento Justech</p>
                    {m.document_id ? (
                      <Link
                        href={`/documents?id=${m.document_id}`}
                        className="text-primary hover:underline font-medium"
                      >
                        {m.document_title}
                      </Link>
                    ) : m.knowledge_asset_id ? (
                      <p className="font-medium">{m.document_title}</p>
                    ) : m.document_title ? (
                      <p className="font-medium">{m.document_title}</p>
                    ) : (
                      <p className="text-muted-foreground italic">Ninguno</p>
                    )}
                    {m.relative_path && (
                      <p className="text-xs text-muted-foreground break-all">Ruta: {m.relative_path}</p>
                    )}
                    {item && (
                      <p className="text-xs text-muted-foreground">
                        Estado:{" "}
                        {COMPLIANCE_STATUS_LABELS[effectiveChecklistStatus(item)] ?? item.status}
                      </p>
                    )}
                    {m.valid_until && (
                      <p className="text-xs text-muted-foreground">Vigencia: hasta {m.valid_until}</p>
                    )}
                    {item && (
                      <div className="flex flex-wrap gap-1 pt-1">
                        {(m.document_title || m.document_id || m.knowledge_asset_id) && (
                          <>
                            <Button size="sm" variant="outline" onClick={() => onPreview(item.id)}>
                              Ver documento
                            </Button>
                            <Button size="sm" variant="ghost" onClick={() => onPreview(item.id)}>
                              Descargar
                            </Button>
                          </>
                        )}
                        <Button size="sm" variant="ghost" onClick={() => onValidate(item.id)}>
                          Validar
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => onAddNote(item.id)}>
                          Agregar nota
                        </Button>
                        {item.task_id ? (
                          <Button size="sm" variant="secondary" asChild>
                            <Link href={`/tasks/${item.task_id}`}>Ver tarea</Link>
                          </Button>
                        ) : (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => void onCreateTask(item.id)}
                            disabled={taskBusyId === item.id}
                          >
                            {taskBusyId === item.id ? "Creando…" : "Crear tarea"}
                          </Button>
                        )}
                      </div>
                    )}
                    {item?.note_history && item.note_history.length > 0 && (
                      <div className="text-xs space-y-1 rounded bg-muted/30 px-2 py-1 mt-2">
                        {item.note_history.slice(-2).reverse().map((entry, idx) => (
                          <p key={`${entry.created_at}-${idx}`}>
                            <span className="font-medium">{entry.author}</span>{" "}
                            {formatNoteTimestamp(entry.created_at)} — {entry.note}
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

function DocumentosTab({ matches }: { matches: DGCPDocumentMatches }) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Cruce documental: qué requisito satisface cada documento del repositorio corporativo.
      </p>
      <div className="grid gap-4">
        {matches.matches.map((m) => (
          <Card key={m.requirement_key} className="overflow-hidden">
            <CardContent className="p-0">
              <div className="grid md:grid-cols-2 divide-y md:divide-y-0 md:divide-x">
                <div className="p-4 space-y-1">
                  <p className="text-xs font-medium uppercase text-muted-foreground">Requisito</p>
                  <p className="font-semibold">{m.requirement_label}</p>
                  <StatusPill status={m.status} />
                </div>
                <div className="p-4 space-y-2 bg-muted/20">
                  <p className="text-xs font-medium uppercase text-muted-foreground">Documento asociado</p>
                  {m.document_id ? (
                    <Link href={`/documents?id=${m.document_id}`} className="text-primary hover:underline font-medium">
                      {m.document_title}
                    </Link>
                  ) : m.document_title ? (
                    <p className="font-medium">{m.document_title}</p>
                  ) : (
                    <p className="text-muted-foreground italic">Ninguno</p>
                  )}
                  <p className="text-xs text-muted-foreground">
                    Estado: {COMPLIANCE_STATUS_LABELS[m.status] ?? m.status}
                  </p>
                  {m.vigency_status && m.vigency_status !== "no_aplica_vigencia" && (
                    <p className="text-xs text-muted-foreground">
                      Vigencia: {m.valid_until ? `hasta ${m.valid_until}` : m.vigency_status}
                    </p>
                  )}
                  {(m.observation ?? m.notes) && (
                    <p className="text-xs">{m.observation ?? m.notes}</p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

function ChecklistTab({
  checklist,
  onCreateTask,
  onPreview,
  onValidate,
  taskBusyId,
  onAddNote,
  onAssociate,
  onMarkNoAplica,
}: {
  opportunityId: string;
  checklist: DGCPChecklist;
  onCreateTask: (id: string) => Promise<{ task_id: string; existing?: boolean }>;
  onPreviewSncc: (form: string) => Promise<void>;
  onPreview: (itemId: string) => void;
  onValidate: (itemId: string) => void;
  taskBusyId: string | null;
  onAddNote: (itemId: string) => void;
  onAssociate: (itemId: string) => void;
  onMarkNoAplica: (itemId: string) => void;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <ClipboardCheck className="h-4 w-4" />
          Checklist — {checklist.compliant_count ?? checklist.ready_count}/
          {checklist.mandatory_total ?? checklist.total} cumplidos
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          {checklist.pending_count} faltante(s) · {checklist.incomplete_count} por completar ·{" "}
          {checklist.expired_count} vencido(s) · {checklist.review_count ?? 0} requieren revisión ·{" "}
          {checklist.unanalyzed_count ?? 0} sin analizar
        </p>
      </CardHeader>
      <CardContent className="space-y-2">
        {checklist.items.map((item) => (
          <div
            key={item.id}
            className="flex flex-wrap items-start justify-between gap-2 rounded-lg border px-3 py-2 text-sm"
          >
            <div className="min-w-0 flex-1">
              <p className="font-medium">{item.requirement}</p>
              <p className="text-xs text-muted-foreground">
                {REQUIREMENT_TYPE_LABELS[item.tipo] ?? item.tipo}
                {item.mandatory ? " · Obligatorio" : " · Opcional"}
                {item.risk ? ` · ${item.risk}` : ""}
              </p>
              {item.recommended_action && (
                <p className="text-xs mt-1">{item.recommended_action}</p>
              )}
              {item.note_history && item.note_history.length > 0 && (
                <div className="text-xs space-y-1 rounded bg-muted/30 px-2 py-1 mt-1">
                  {item.note_history.slice(-2).reverse().map((entry, idx) => (
                    <p key={`${entry.created_at}-${idx}`}>
                      <span className="font-medium">{entry.author}</span>{" "}
                      {formatNoteTimestamp(entry.created_at)} — {entry.note}
                    </p>
                  ))}
                </div>
              )}
            </div>
            <div className="flex items-center gap-2 shrink-0 flex-wrap justify-end max-w-md">
              <StatusPill status={item.status} item={item} />
              <RequirementActions
                item={item}
                taskBusy={taskBusyId === item.id}
                onPreview={() => onPreview(item.id)}
                onValidate={() => onValidate(item.id)}
                onAddNote={() => onAddNote(item.id)}
                onCreateTask={() => void onCreateTask(item.id)}
                onAssociate={() => onAssociate(item.id)}
                onMarkNoAplica={() => void onMarkNoAplica(item.id)}
              />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function ExpedienteTab({
  opportunityId,
  checklist,
  bidPackage,
  expedienteStatus,
  busy,
  onPrepare,
  onDownload,
  onMarkReady,
  onFinalizationUpdated,
}: {
  opportunityId: string;
  checklist: DGCPChecklist | null;
  bidPackage: DGCPBidPackage;
  expedienteStatus: DGCPExpedienteStatus | null;
  busy: boolean;
  onPrepare: () => void;
  onDownload: () => void;
  onMarkReady: () => void;
  onFinalizationUpdated: () => void;
}) {
  const statusLabel =
    EXPEDIENTE_STATUS_LABELS[expedienteStatus?.expediente_status ?? "sin_preparar"] ?? "Sin preparar";

  return (
    <Card className="border-primary/20">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Package className="h-4 w-4 text-primary" />
          Expediente — {statusLabel}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Button onClick={onPrepare} disabled={busy}>
            {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Preparar expediente
          </Button>
          <Button
            variant="outline"
            onClick={onDownload}
            disabled={busy || !expedienteStatus?.can_download}
          >
            <Download className="mr-2 h-4 w-4" />
            Descargar expediente
          </Button>
          <Button
            variant="secondary"
            onClick={onMarkReady}
            disabled={busy || !expedienteStatus?.can_mark_ready}
          >
            Marcar listo para revisión
          </Button>
          <Button variant="ghost" disabled title="Presentación DGCP — fase futura">
            Presentar en DGCP
          </Button>
        </div>
        <div className="flex items-end gap-4">
          <p className="text-4xl font-bold text-primary">{bidPackage.preparation_pct.toFixed(0)}%</p>
          <p className="text-sm text-muted-foreground pb-1">
            {bidPackage.compliant_count ?? bidPackage.found_documents}/
            {bidPackage.mandatory_requirements ?? bidPackage.total_requirements ?? "—"} requisitos cumplidos
          </p>
        </div>
        <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-6 text-sm">
          <Metric label="Total requisitos" value={bidPackage.total_requirements ?? 0} />
          <Metric label="Cumplidos" value={bidPackage.compliant_count ?? 0} />
          <Metric label="Faltantes" value={bidPackage.pending_documents} />
          <Metric label="Vencidos" value={bidPackage.expired_documents} />
          <Metric label="Por completar" value={bidPackage.forms_to_complete} />
          <Metric label="Requieren revisión" value={bidPackage.review_count ?? 0} />
        </div>
        {bidPackage.recommended_tasks.length > 0 && (
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase mb-2">Tareas recomendadas</p>
            <ul className="list-disc pl-4 text-sm space-y-1">
              {bidPackage.recommended_tasks.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          </div>
        )}
        <DGCPFinalizationPanel
          opportunityId={opportunityId}
          checklist={checklist}
          busy={busy}
          onUpdated={onFinalizationUpdated}
        />
        <RealExpedientePanel opportunityId={opportunityId} busy={busy} onUpdated={onFinalizationUpdated} />
        <div className="grid gap-4 sm:grid-cols-2 text-sm">
          <ListBlock title="Disponibles" items={bidPackage.available} />
          <ListBlock title="Faltantes" items={bidPackage.missing} empty="Ninguno" />
          <ListBlock title="Vencidos" items={bidPackage.expired} empty="Ninguno" />
          <ListBlock title="Por completar" items={bidPackage.to_complete} empty="Ninguno" />
        </div>
      </CardContent>
    </Card>
  );
}

function RiesgosTab({
  checklist,
  opportunity,
}: {
  checklist: DGCPChecklist;
  opportunity: DGCPOpportunity;
}) {
  const risks = checklist.items.filter((i) => i.risk);
  return (
    <div className="space-y-4">
      {opportunity.risks.length > 0 && (
        <Card>
          <CardHeader><CardTitle className="text-base">Riesgos IA del proceso</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            {opportunity.risks.map((r, i) => (
              <p key={i}>{r.descripcion}</p>
            ))}
          </CardContent>
        </Card>
      )}
      <Card>
        <CardHeader><CardTitle className="text-base">Riesgos de cumplimiento documental</CardTitle></CardHeader>
        <CardContent>
          {risks.length === 0 ? (
            <p className="text-sm text-muted-foreground">Sin riesgos documentales detectados.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {risks.map((r) => (
                <li key={r.id} className="rounded border px-3 py-2">
                  <span className="font-medium">{r.requirement}</span>
                  <p className="text-muted-foreground text-xs mt-0.5">{r.risk}</p>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function ProcessDocumentsTab({
  documents,
}: {
  documents: DGCPProcessDocuments;
  opportunityId?: string;
}) {
  const items = documents.items.filter((d) => PROCESS_DOC_SOURCES.has(d.source_type));
  const hasRealPliego = items.some(
    (d) => PLIEGO_ROLES.has(d.doc_role) && d.has_text,
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <FileStack className="h-4 w-4" />
          Documentos del comprador ({items.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!hasRealPliego && (
          <div className="rounded-lg border border-warning/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-800 dark:text-amber-200 mb-4">
            No se encontró pliego/TDR real adjunto. Este análisis puede estar incompleto.
          </div>
        )}
        <p className="text-sm text-muted-foreground mb-4">
          Solo documentos entregados por la institución compradora (pliego, TDR, anexos, enmiendas).
          Almacenados en <code className="text-xs">DGCP/&#123;código&#125;/</code> — separados del
          repositorio corporativo Justech.
        </p>
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">No hay documentos del proceso indexados.</p>
        ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-xs text-muted-foreground">
                <th className="py-2 pr-4">Documento</th>
                <th className="py-2 pr-4">Rol</th>
                <th className="py-2 pr-4">Prioridad</th>
                <th className="py-2 pr-4">Estado</th>
                <th className="py-2">Texto</th>
              </tr>
            </thead>
            <tbody>
              {items.map((doc) => (
                <tr key={doc.id} className="border-b border-border/40">
                  <td className="py-2 pr-4">{doc.title}</td>
                  <td className="py-2 pr-4 text-xs">
                    {PROCESS_DOC_ROLE_LABELS[doc.doc_role] ?? doc.doc_role}
                  </td>
                  <td className="py-2 pr-4">
                    <PriorityPill priority={doc.priority} />
                  </td>
                  <td className="py-2 pr-4">
                    <ProcessStatusPill status={doc.display_status ?? doc.ingestion_status} />
                  </td>
                  <td className="py-2 text-xs">{doc.has_text ? "Sí" : "No"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        )}
      </CardContent>
    </Card>
  );
}

function AutollenadoTab({
  formType,
  onFormTypeChange,
  onPreview,
  onGenerate,
  preview,
}: {
  formType: string;
  onFormTypeChange: (v: string) => void;
  onPreview: () => void;
  onGenerate: () => void;
  preview: DGCPFormPreview | null;
}) {
  const forms = ["SNCC.F033", "SNCC.F042", "SNCC.F047", "OFERTA.ECONOMICA", "CARTA.PRESENTACION"];

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <PenLine className="h-4 w-4" />
            Autollenado controlado
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Vista previa y generación en copia controlada — plantillas originales intactas.
          </p>
          <div className="flex flex-wrap gap-2">
            {forms.map((f) => (
              <Button
                key={f}
                size="sm"
                variant={formType === f ? "default" : "outline"}
                onClick={() => onFormTypeChange(f)}
              >
                {f}
              </Button>
            ))}
          </div>
          <div className="flex gap-2 flex-wrap">
            <Button onClick={onPreview}>Vista previa autollenado</Button>
            <Button variant="secondary" onClick={onGenerate}>
              Generar copia controlada
            </Button>
          </div>
        </CardContent>
      </Card>
      {preview && (
        <Card className="border-primary/30">
          <CardHeader>
            <CardTitle className="text-base">{preview.form_type}</CardTitle>
          </CardHeader>
          <CardContent className="divide-y text-sm">
            {preview.fields.map((f) => (
              <div key={f.label} className="flex justify-between gap-4 py-2">
                <div>
                  <p>{f.label}</p>
                  {f.source && <p className="text-xs text-muted-foreground">Fuente: {f.source}</p>}
                </div>
                <div className="text-right">
                  <p className={f.status === "pendiente" ? "text-amber-500" : ""}>{f.value ?? "Pendiente"}</p>
                  <p className="text-xs text-muted-foreground">
                    {(f.confidence * 100).toFixed(0)}% · {f.status}
                  </p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function AlertasTab({ alerts }: { alerts: DGCPBidAlerts }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Bell className="h-4 w-4" />
          Alertas ({alerts.total})
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {alerts.alerts.length === 0 ? (
          <p className="text-sm text-muted-foreground">Sin alertas activas.</p>
        ) : (
          alerts.alerts.map((a) => (
            <div
              key={a.id}
              className={cn(
                "rounded border px-3 py-2 text-sm",
                a.severity === "high" && "border-red-500/30 bg-red-500/5",
                a.severity === "medium" && "border-amber-500/30 bg-warning/10",
              )}
            >
              <p className="font-medium">{a.title}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{a.message}</p>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}

function AssociateDocumentModal({
  busy,
  onClose,
  onPickKnowledge,
  onPickDocument,
  onUpload,
}: {
  busy: boolean;
  onClose: () => void;
  onPickKnowledge: (id: string) => void;
  onPickDocument: (id: string) => void;
  onUpload: (file: File) => void;
}) {
  const [knowledge, setKnowledge] = useState<
    Array<{ id: string; title: string; relative_path: string; folder_category: string }>
  >([]);
  const [documents, setDocuments] = useState<Array<{ id: string; title: string }>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void Promise.all([
      apiClient.listKnowledgeAssets({ limit: 40 }),
      apiClient.getDocuments({ limit: 40 }),
    ])
      .then(([k, d]) => {
        if (cancelled) return;
        setKnowledge(k.items);
        setDocuments(d.items.map((x) => ({ id: x.id, title: x.title })));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
      role="presentation"
    >
      <Card className="w-full max-w-2xl max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <CardHeader>
          <CardTitle className="text-base">Asociar documento corporativo</CardTitle>
          <p className="text-sm text-muted-foreground">
            Seleccione del repositorio JustechAI (carpetas oficiales) o suba un archivo nuevo.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label className="text-xs uppercase text-muted-foreground">Subir nuevo</Label>
            <Input
              type="file"
              accept=".pdf,.docx,.xlsx,.txt,.csv,.rtf,.odt"
              disabled={busy}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) onUpload(f);
              }}
            />
          </div>
          {loading ? (
            <p className="text-sm text-muted-foreground">Cargando repositorio…</p>
          ) : (
            <>
              <div>
                <p className="text-xs font-medium mb-2">JustechAI ({knowledge.length})</p>
                <div className="max-h-48 overflow-y-auto divide-y rounded border">
                  {knowledge.map((k) => (
                    <button
                      key={k.id}
                      type="button"
                      className="w-full px-3 py-2 text-left text-sm hover:bg-muted/50"
                      disabled={busy}
                      onClick={() => onPickKnowledge(k.id)}
                    >
                      <span className="font-medium">{k.title}</span>
                      <span className="block text-xs text-muted-foreground">{k.relative_path}</span>
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-xs font-medium mb-2">Documentos JAIOS ({documents.length})</p>
                <div className="max-h-32 overflow-y-auto divide-y rounded border">
                  {documents.map((d) => (
                    <button
                      key={d.id}
                      type="button"
                      className="w-full px-3 py-2 text-left text-sm hover:bg-muted/50"
                      disabled={busy}
                      onClick={() => onPickDocument(d.id)}
                    >
                      {d.title}
                    </button>
                  ))}
                </div>
              </div>
            </>
          )}
          <Button variant="ghost" size="sm" onClick={onClose} disabled={busy}>
            Cancelar
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

function ProcessStatusPill({ status }: { status: string }) {
  return (
    <span
      className={cn(
        "rounded px-2 py-0.5 text-[10px] font-semibold",
        status === "Requisitos extraídos" && "bg-success/10 text-success",
        status === "Texto extraído" && "bg-success/10 text-success",
        status === "Procesado" && "bg-blue-500/15 text-blue-700",
        status === "Detectado" && "bg-muted text-muted-foreground",
        status === "Error de lectura" && "bg-red-500/15 text-red-600",
        status === "Sin contenido relevante" && "bg-muted text-muted-foreground",
      )}
    >
      {status}
    </span>
  );
}

function PriorityPill({ priority }: { priority: string }) {
  return (
    <span
      className={cn(
        "rounded px-2 py-0.5 text-[10px] font-semibold uppercase",
        priority === "alta" && "bg-red-500/15 text-red-600",
        priority === "media" && "bg-warning/10 text-warning",
        priority === "baja" && "bg-muted text-muted-foreground",
      )}
    >
      {PROCESS_PRIORITY_LABELS[priority] ?? priority}
    </span>
  );
}

function StatusPill({ status, item }: { status: string; item?: DGCPChecklistItem }) {
  const effective = item ? effectiveChecklistStatus(item) : status;
  const label = COMPLIANCE_STATUS_LABELS[effective] ?? CHECKLIST_STATUS_LABELS[effective] ?? effective;
  return (
    <span
      className={cn(
        "rounded px-2 py-0.5 text-[10px] font-semibold uppercase",
        effective === "validado_manual" && "bg-success/10 text-success",
        (effective === "encontrado_vigente" || effective === "encontrado") &&
          "bg-success/10 text-success",
        (effective === "faltante" || effective === "pendiente") && "bg-muted text-muted-foreground",
        (effective === "encontrado_vencido" || effective === "vencido") && "bg-red-500/15 text-red-600",
        (effective === "requiere_completado" || effective === "completar" || effective === "incompleto") &&
          "bg-warning/10 text-warning",
        (effective === "requiere_revision" || effective === "encontrado_sin_fecha") &&
          "bg-orange-500/15 text-orange-600",
        (effective === "adjuntado" || effective === "borrador_pendiente") &&
          "bg-primary/10 text-primary",
        effective === "no_aplica" && "bg-blue-500/15 text-blue-600",
      )}
    >
      {label}
    </span>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded border px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-bold">{value}</p>
    </div>
  );
}

function ListBlock({ title, items, empty = "—" }: { title: string; items: string[]; empty?: string }) {
  return (
    <div>
      <p className="text-xs font-medium text-muted-foreground mb-1">{title}</p>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">{empty}</p>
      ) : (
        <ul className="text-sm list-disc pl-4 space-y-0.5">
          {items.map((i) => (
            <li key={i}>{i}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
