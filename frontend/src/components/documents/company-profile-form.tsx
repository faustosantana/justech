"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Download,
  ExternalLink,
  FolderOpen,
  Mail,
  Pencil,
  RefreshCw,
  Save,
  Search,
  Upload,
} from "lucide-react";

import { DocumentViewButton } from "@/components/documents/document-view-button";
import { CompanyPersonSelect, isProfilePersonField } from "@/components/documents/company-person-select";
import { CompanyRepresentativesPanel } from "@/components/documents/company-representatives-panel";
import { M365DocumentSearchPicker } from "@/components/m365/m365-document-search-picker";
import { isPathLikeM365Query } from "@/lib/m365-query-utils";
import { sanitizeMicrosoftUrl } from "@/lib/m365-urls";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";
import type { CompanyCompletion, CompanyFieldStatus } from "@/lib/documents-hub";
import { progressBarClass } from "@/lib/documents-hub";
import { cn } from "@/lib/utils";

const BADGE_STYLES: Record<string, string> = {
  Falta: "border-amber-500/40 bg-amber-500/10 text-amber-800",
  Completo: "border-emerald-500/40 bg-emerald-500/10 text-emerald-800",
  "Documento cargado": "border-blue-500/40 bg-blue-500/10 text-blue-800",
  "Dato escrito": "border-sky-500/40 bg-sky-500/10 text-sky-800",
  "Documento detectado, número pendiente": "border-amber-500/40 bg-amber-500/10 text-amber-800",
  Vencido: "border-red-500/40 bg-red-500/10 text-red-800",
  "Pendiente de validar": "border-amber-500/40 bg-amber-500/10 text-amber-800",
  "Cédula validada": "border-emerald-500/40 bg-emerald-500/10 text-emerald-800",
  Rechazada: "border-red-500/40 bg-red-500/10 text-red-800",
  "Sin representante asignado": "border-slate-500/40 bg-slate-500/10 text-slate-700",
};

const UPLOAD_LABELS: Record<string, string> = {
  datos_bancarios: "Subir certificación bancaria",
  cedula_representante: "Subir imagen/PDF de cédula",
  certificacion_bancaria: "Subir certificación bancaria",
  registro_mercantil: "Subir registro mercantil",
};

type ModalKind = "edit" | "upload" | "request" | "pick-upload" | null;

interface CompanyProfileFormProps {
  companyId: string;
  onSaved?: () => void;
  onGenerateForm?: () => void;
  onRequestAll?: () => void;
  onAddRepresentative?: () => void;
}

export function CompanyProfileForm({
  companyId,
  onSaved,
  onGenerateForm,
  onRequestAll,
  onAddRepresentative,
}: CompanyProfileFormProps) {
  const [completion, setCompletion] = useState<CompanyCompletion | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState<ModalKind>(null);
  const [activeField, setActiveField] = useState<CompanyFieldStatus | null>(null);
  const [editValue, setEditValue] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [validUntil, setValidUntil] = useState("");
  const [requestResult, setRequestResult] = useState<{ subject: string; body: string } | null>(null);
  const [docPickerOpen, setDocPickerOpen] = useState(false);
  const [docPickerQuery, setDocPickerQuery] = useState("");
  const [docPickerField, setDocPickerField] = useState<CompanyFieldStatus | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    apiClient
      .getDocumentsHubCompletion(companyId)
      .then(setCompletion)
      .catch((err) => {
        setCompletion(null);
        setError(err instanceof ApiError ? err.message : "No se pudo cargar el estado de los campos.");
      })
      .finally(() => setLoading(false));
  }, [companyId]);

  useEffect(() => {
    load();
  }, [load]);

  const missingFields = useMemo(
    () => (completion?.fields || []).filter((f) => f.badge === "Falta" || f.badge === "Vencido"),
    [completion],
  );

  const uploadableFields = useMemo(
    () => (completion?.fields || []).filter((f) => f.kind === "document" || f.kind === "hybrid"),
    [completion],
  );

  const openModal = (kind: ModalKind, field: CompanyFieldStatus) => {
    setActiveField(field);
    setModal(kind);
    setEditValue(field.text_value || "");
    setUploadFile(null);
    setValidUntil("");
    setRequestResult(null);
    setError(null);
  };

  const closeModal = () => {
    setModal(null);
    setActiveField(null);
    setUploadFile(null);
    setRequestResult(null);
  };

  const saveField = async () => {
    if (!activeField) return;
    setSaving(true);
    setError(null);
    try {
      await apiClient.updateDocumentsHubField(companyId, activeField.field_key, editValue);
      closeModal();
      load();
      onSaved?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar el campo.");
    } finally {
      setSaving(false);
    }
  };

  const uploadDocument = async () => {
    if (!activeField || !uploadFile) return;
    setUploading(true);
    setError(null);
    try {
      await apiClient.uploadDocumentsHubCompanyDocument(
        companyId,
        activeField.field_key,
        uploadFile,
        validUntil || undefined,
      );
      closeModal();
      load();
      onSaved?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo subir el documento.");
    } finally {
      setUploading(false);
    }
  };

  const requestField = async () => {
    if (!activeField) return;
    setSaving(true);
    setError(null);
    try {
      const result = await apiClient.requestDocumentsHubMissingFields(companyId, {
        field_keys: [activeField.field_key],
        create_task: true,
        send_email: true,
      });
      setRequestResult({ subject: result.subject, body: result.body });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo generar la solicitud.");
    } finally {
      setSaving(false);
    }
  };

  const requestAllMissing = async () => {
    if (onRequestAll) {
      onRequestAll();
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const result = await apiClient.requestDocumentsHubMissingFields(companyId, {
        field_keys: missingFields.map((f) => f.field_key),
        create_task: true,
        send_email: true,
      });
      setRequestResult({ subject: result.subject, body: result.body });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo solicitar faltantes.");
    } finally {
      setSaving(false);
    }
  };

  const syncOneDrive = async () => {
    setSyncing(true);
    setError(null);
    try {
      const result = await apiClient.syncDocumentsHubCompanyOneDrive(companyId);
      if (result.errors?.length) {
        setError(result.errors.join(" · "));
      } else if (result.message) {
        setError(null);
      }
      load();
      onSaved?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al sincronizar OneDrive.");
    } finally {
      setSyncing(false);
    }
  };

  const openDocumentSearch = (field: CompanyFieldStatus, query = "") => {
    setDocPickerField(field);
    setDocPickerQuery(query || field.label);
    setDocPickerOpen(true);
  };

  const downloadFile = (url: string, name: string) => {
    const a = document.createElement("a");
    a.href = url;
    a.target = "_blank";
    a.rel = "noreferrer";
    a.download = name;
    a.click();
  };

  const renderActions = (field: CompanyFieldStatus) => {
    const actions: React.ReactNode[] = [];
    const isMissing = field.badge === "Falta" || field.badge === "Vencido";
    const hasDoc = Boolean(field.document_id || field.document_name);
    const uploadLabel = UPLOAD_LABELS[field.field_key] || "Subir documento";

    if (field.kind === "text" || field.kind === "hybrid") {
      if (isMissing || field.badge === "Dato escrito" || field.badge === "Completo") {
        actions.push(
          <Button key="edit" size="sm" variant="outline" onClick={() => openModal("edit", field)}>
            <Pencil className="mr-1 h-3.5 w-3.5" />
            {field.kind === "hybrid" ? "Escribir" : "Completar"}
          </Button>,
        );
      }
    }

    if (field.kind === "document" || field.kind === "hybrid") {
      if (isMissing || !hasDoc) {
        actions.push(
          <Button key="upload" size="sm" variant="outline" onClick={() => openModal("upload", field)}>
            <Upload className="mr-1 h-3.5 w-3.5" />
            {uploadLabel}
          </Button>,
        );
      }
    if (hasDoc) {
      actions.push(
        <DocumentViewButton
          key="view-doc"
          knowledgeAssetId={field.knowledge_asset_id}
          documentId={field.document_id}
          webUrl={field.onedrive_url}
          viewUrl={field.view_url}
        />,
      );
      actions.push(
        <Button key="replace" size="sm" variant="outline" onClick={() => openModal("upload", field)}>
          <Upload className="mr-1 h-3.5 w-3.5" />
          Reemplazar
        </Button>,
      );
    }
      if (field.onedrive_folder) {
        actions.push(
          <Button key="folder" size="sm" variant="ghost" onClick={() => openDocumentSearch(field, field.onedrive_folder!)}>
            <Search className="mr-1 h-3.5 w-3.5" />
            Buscar en carpeta
          </Button>,
        );
      }
      actions.push(
        <Button key="search-doc" size="sm" variant="ghost" onClick={() => openDocumentSearch(field)}>
          <FolderOpen className="mr-1 h-3.5 w-3.5" />
          Buscar documento
        </Button>,
      );
    }

    if (isMissing || field.badge === "Dato escrito" || field.badge === "Vencido") {
      actions.push(
        <Button key="request" size="sm" variant="ghost" onClick={() => openModal("request", field)}>
          <Mail className="mr-1 h-3.5 w-3.5" />
          Solicitar
        </Button>,
      );
    }

    return actions;
  };

  return (
    <>
      {successMessage && !modal && (
        <Card className="mb-4 border-emerald-500/40 bg-emerald-500/5">
          <CardContent className="py-3 text-sm text-emerald-800">{successMessage}</CardContent>
        </Card>
      )}

      {error && !modal && (
        <Card className="mb-4 border-amber-500/40 bg-amber-500/5">
          <CardContent className="flex items-center gap-2 py-3 text-sm text-amber-800">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            {error}
          </CardContent>
        </Card>
      )}

      {requestResult && !modal && (
        <Card className="mb-4 border-blue-500/30">
          <CardContent className="space-y-2 py-4 text-sm">
            <p className="font-medium">{requestResult.subject}</p>
            <pre className="whitespace-pre-wrap text-xs text-muted-foreground">{requestResult.body}</pre>
            <Button size="sm" variant="ghost" onClick={() => setRequestResult(null)}>
              Cerrar
            </Button>
          </CardContent>
        </Card>
      )}

      {completion && (
        <Card className="mb-4">
          <CardContent className="flex flex-wrap items-center gap-4 py-4">
            <div className="min-w-[200px] flex-1">
              <p className="text-sm font-medium">{completion.empresa}</p>
              <p className="text-sm text-muted-foreground">
                {completion.fields_complete} de {completion.fields_total} campos completos ({completion.completeness_score}%)
              </p>
              {completion.progress_note && (
                <p className="text-xs text-amber-700">{completion.progress_note}</p>
              )}
              <div className="mt-2 h-2 max-w-md overflow-hidden rounded-full bg-muted">
                <div
                  className={cn(
                    "h-full rounded-full transition-all",
                    progressBarClass(completion.progress_semaphore, completion.completeness_score),
                  )}
                  style={{ width: `${completion.completeness_score}%` }}
                />
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setModal("pick-upload");
                  setActiveField(null);
                  setError(null);
                }}
                disabled={uploadableFields.length === 0}
              >
                <Upload className="mr-1 h-4 w-4" />
                Subir documento
              </Button>
              <Button size="sm" variant="outline" onClick={requestAllMissing} disabled={saving || missingFields.length === 0}>
                <Mail className="mr-1 h-4 w-4" />
                Solicitar a Jennipher
              </Button>
              {onGenerateForm && (
                <Button size="sm" variant="outline" onClick={onGenerateForm}>
                  Generar formulario externo
                </Button>
              )}
              <Button size="sm" variant="outline" onClick={syncOneDrive} disabled={syncing}>
                <RefreshCw className={cn("mr-1 h-4 w-4", syncing && "animate-spin")} />
                Sincronizar OneDrive
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Datos corporativos</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {loading && <p className="text-sm text-muted-foreground">Cargando campos…</p>}
          {!loading && (completion?.fields || []).length === 0 && (
            <p className="text-sm text-muted-foreground">Sin campos configurados.</p>
          )}
          {completion?.fields.map((field) => (
            <div
              key={field.field_key}
              className="rounded-lg border border-border/60 p-4 transition-colors hover:bg-muted/30"
            >
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium">{field.label}</span>
                <Badge variant="outline" className={BADGE_STYLES[field.badge] || ""}>
                  {field.badge}
                </Badge>
                {field.vigency_status && (
                  <Badge variant="secondary" className="text-xs capitalize">
                    {field.vigency_status}
                  </Badge>
                )}
                {field.is_required && (
                  <Badge variant="secondary" className="text-xs">
                    Requerido
                  </Badge>
                )}
              </div>
              {field.field_key === "cedula_representante" ? (
                <CompanyRepresentativesPanel
                  companyId={companyId}
                  documentTypes={["cedula"]}
                  title="Cédula por representante"
                  onChanged={() => {
                    load();
                    onSaved?.();
                  }}
                />
              ) : isProfilePersonField(field.field_key) ? (
                <>
                  {field.text_value && (
                    <p className="mb-1 text-sm text-muted-foreground">{field.text_value}</p>
                  )}
                  <CompanyPersonSelect
                    companyId={companyId}
                    fieldKey={field.field_key}
                    fieldLabel={field.label}
                    currentValue={field.text_value}
                    onLinked={(msg) => {
                      setSuccessMessage(msg);
                      load();
                      onSaved?.();
                    }}
                  />
                  <div className="mt-2 flex flex-wrap gap-2">{renderActions(field)}</div>
                </>
              ) : (
                <>
                  {field.text_value && (
                    <p className="mb-1 text-sm text-muted-foreground">{field.text_value}</p>
                  )}
                  {field.document_name && (
                    <p className="mb-1 text-sm text-muted-foreground">Archivo: {field.document_name}</p>
                  )}
                  {field.uploaded_at && (
                    <p className="mb-1 text-xs text-muted-foreground">
                      Subido: {new Date(field.uploaded_at).toLocaleString()}
                    </p>
                  )}
                  {field.onedrive_folder && (
                    <p className="mb-2 font-mono text-xs text-muted-foreground">{field.onedrive_folder}</p>
                  )}
                  <div className="flex flex-wrap gap-2">{renderActions(field)}</div>
                </>
              )}
            </div>
          ))}
        </CardContent>
      </Card>

      {modal === "pick-upload" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle className="text-base">Subir documento</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <p className="text-sm text-muted-foreground">Seleccione el tipo de documento:</p>
              {uploadableFields.map((f) => (
                <Button
                  key={f.field_key}
                  variant="outline"
                  className="w-full justify-start"
                  onClick={() => openModal("upload", f)}
                >
                  {UPLOAD_LABELS[f.field_key] || f.label}
                </Button>
              ))}
              <Button variant="ghost" className="w-full" onClick={closeModal}>
                Cancelar
              </Button>
            </CardContent>
          </Card>
        </div>
      )}

      {modal && modal !== "pick-upload" && activeField && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <Card className="w-full max-w-lg">
            <CardHeader>
              <CardTitle className="text-base">
                {modal === "edit" && `Completar — ${activeField.label}`}
                {modal === "upload" &&
                  `${UPLOAD_LABELS[activeField.field_key] || "Subir documento"} — ${activeField.label}`}
                {modal === "request" && `Solicitar — ${activeField.label}`}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {error && (
                <p className="rounded-md bg-amber-500/10 px-3 py-2 text-sm text-amber-800">{error}</p>
              )}

              {modal === "edit" && (
                <>
                  <textarea
                    className="min-h-[100px] w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    placeholder={`Ingrese ${activeField.label.toLowerCase()}`}
                  />
                  <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={closeModal}>
                      Cancelar
                    </Button>
                    <Button onClick={saveField} disabled={saving || !editValue.trim()}>
                      <Save className="mr-1 h-4 w-4" />
                      Guardar cambios
                    </Button>
                  </div>
                </>
              )}

              {modal === "upload" && (
                <>
                  <p className="text-xs text-muted-foreground">
                    Destino OneDrive: <span className="font-mono">{activeField.onedrive_folder}</span>
                  </p>
                  <input
                    type="file"
                    accept=".pdf,.png,.jpg,.jpeg,.doc,.docx"
                    className="w-full text-sm"
                    onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  />
                  <label className="block text-xs text-muted-foreground">
                    Fecha de vencimiento (opcional)
                    <input
                      type="date"
                      className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
                      value={validUntil}
                      onChange={(e) => setValidUntil(e.target.value)}
                    />
                  </label>
                  <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={closeModal}>
                      Cancelar
                    </Button>
                    <Button onClick={uploadDocument} disabled={uploading || !uploadFile}>
                      <Upload className="mr-1 h-4 w-4" />
                      {uploading ? "Subiendo…" : "Subir a OneDrive"}
                    </Button>
                  </div>
                </>
              )}

              {modal === "request" && (
                <>
                  <p className="text-sm text-muted-foreground">
                    Solicitud a Jennipher para: <strong>{activeField.label}</strong>
                  </p>
                  {requestResult ? (
                    <div className="rounded-lg border bg-muted/40 p-3 text-xs">
                      <p className="font-medium">{requestResult.subject}</p>
                      <pre className="mt-2 whitespace-pre-wrap text-muted-foreground">{requestResult.body}</pre>
                    </div>
                  ) : (
                    <div className="flex justify-end gap-2">
                      <Button variant="outline" onClick={closeModal}>
                        Cancelar
                      </Button>
                      <Button onClick={requestField} disabled={saving || activeField.field_key === "_all"}>
                        <Mail className="mr-1 h-4 w-4" />
                        Solicitar a Jennipher
                      </Button>
                    </div>
                  )}
                  {requestResult && (
                    <div className="flex justify-end">
                      <Button onClick={closeModal}>Cerrar</Button>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      <M365DocumentSearchPicker
        open={docPickerOpen}
        onClose={() => {
          setDocPickerOpen(false);
          setDocPickerField(null);
        }}
        companyId={companyId}
        fieldKey={docPickerField?.field_key}
        fieldLabel={docPickerField?.label}
        initialQuery={docPickerQuery}
        initialTab={isPathLikeM365Query(docPickerQuery) ? "browse" : "search"}
        entityType="internal_company"
        entityId={companyId}
        title="Buscar documento en Microsoft 365"
        onLinked={(message) => {
          setSuccessMessage(message);
          setError(null);
          load();
          onSaved?.();
        }}
        onImported={(message) => {
          setSuccessMessage(message);
          setError(null);
          load();
          onSaved?.();
        }}
      />

    </>
  );
}
