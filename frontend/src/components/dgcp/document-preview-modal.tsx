"use client";

import { Copy, Loader2, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { AuthenticatedFileViewer } from "@/components/documents/authenticated-file-viewer";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiClient } from "@/lib/api";
import { COMPLIANCE_STATUS_LABELS, type DGCPChecklistItem } from "@/lib/dgcp";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  opportunityId: string;
  itemId: string;
  checklistItem?: DGCPChecklistItem | null;
  onValidated?: () => void;
  onNoted?: () => void;
  onTaskCreated?: () => void;
}

export function DocumentPreviewModal({
  open,
  onOpenChange,
  opportunityId,
  itemId,
  checklistItem,
  onValidated,
  onNoted,
  onTaskCreated,
}: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState(false);
  const [validationStatus, setValidationStatus] = useState("validado_manual");
  const [validationNote, setValidationNote] = useState("");
  const [noteText, setNoteText] = useState("");
  const [preview, setPreview] = useState<Awaited<ReturnType<typeof apiClient.getDGCPDocumentPreview>> | null>(
    null,
  );

  useEffect(() => {
    if (!open || !itemId) return;
    setLoading(true);
    setError(null);
    setPreview(null);
    void apiClient
      .getDGCPDocumentPreview(opportunityId, itemId)
      .then(setPreview)
      .catch(() => setError("No se pudo cargar la vista del documento."))
      .finally(() => setLoading(false));
  }, [open, opportunityId, itemId]);

  if (!open) return null;

  const validity = preview?.validity_analysis as Record<string, string> | null;
  const filePath = preview?.download_url ?? preview?.preview_url ?? null;
  const filenameHint =
    (preview?.metadata?.filename as string | undefined) ??
    preview?.document_title ??
    "documento";

  const handleValidate = async () => {
    setActionBusy(true);
    setError(null);
    try {
      await apiClient.manualValidateDGCPRequirement(opportunityId, itemId, {
        status: validationStatus,
        note: validationNote.trim() || undefined,
      });
      onValidated?.();
      onOpenChange(false);
    } catch {
      setError("No se pudo guardar la validación.");
    } finally {
      setActionBusy(false);
    }
  };

  const handleAddNote = async () => {
    if (!noteText.trim()) return;
    setActionBusy(true);
    setError(null);
    try {
      await apiClient.addDGCPChecklistNote(opportunityId, itemId, noteText.trim());
      setNoteText("");
      onNoted?.();
    } catch {
      setError("No se pudo guardar la nota.");
    } finally {
      setActionBusy(false);
    }
  };

  const handleCreateTask = async () => {
    setActionBusy(true);
    setError(null);
    try {
      await apiClient.createDGCPChecklistTask(opportunityId, itemId);
      onTaskCreated?.();
    } catch {
      setError("No se pudo crear la tarea.");
    } finally {
      setActionBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <Card className="w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>{preview?.requirement_label ?? "Documento"}</CardTitle>
          <Button variant="ghost" size="sm" onClick={() => onOpenChange(false)}>
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          {loading && <p className="text-muted-foreground">Cargando metadatos…</p>}
          {error && <p className="text-destructive">{error}</p>}

          {preview && !loading && (
            <>
              <div className="grid gap-2 sm:grid-cols-2">
                <Meta label="Documento" value={preview.document_title ?? "—"} />
                <Meta label="Ruta origen" value={preview.relative_path ?? "—"} />
                {validity?.expiration_date && (
                  <Meta label="Vencimiento detectado" value={validity.expiration_date} />
                )}
                {validity?.validity_status && (
                  <Meta
                    label="Estado vigencia"
                    value={COMPLIANCE_STATUS_LABELS[validity.validity_status] ?? validity.validity_status}
                  />
                )}
                {validity?.evidence_text && (
                  <Meta label="Evidencia" value={validity.evidence_text} className="sm:col-span-2" />
                )}
              </div>

              {checklistItem?.note_history && checklistItem.note_history.length > 0 && (
                <NoteHistory history={checklistItem.note_history} />
              )}

              <div className="rounded-lg border p-3 space-y-3">
                <p className="text-xs font-medium uppercase text-muted-foreground">Acciones</p>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-1">
                    <Label>Validar — estado</Label>
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
                    <Label>Nota de validación</Label>
                    <Input
                      value={validationNote}
                      onChange={(e) => setValidationNote(e.target.value)}
                      placeholder="Opcional al validar"
                    />
                  </div>
                </div>
                <Button size="sm" onClick={() => void handleValidate()} disabled={actionBusy}>
                  {actionBusy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  Guardar validación
                </Button>

                <div className="space-y-1 pt-2 border-t">
                  <Label>Agregar nota</Label>
                  <Input
                    value={noteText}
                    onChange={(e) => setNoteText(e.target.value)}
                    placeholder="Nota persistente con autor y fecha"
                  />
                  <Button size="sm" variant="outline" onClick={() => void handleAddNote()} disabled={actionBusy || !noteText.trim()}>
                    Guardar nota
                  </Button>
                </div>

                <div className="flex flex-wrap gap-2 pt-2 border-t">
                  {checklistItem?.task_id ? (
                    <Button size="sm" variant="secondary" asChild>
                      <Link href={`/tasks/${checklistItem.task_id}`}>Ver tarea</Link>
                    </Button>
                  ) : (
                    <Button size="sm" variant="outline" onClick={() => void handleCreateTask()} disabled={actionBusy}>
                      Crear tarea
                    </Button>
                  )}
                </div>
              </div>

              {preview.relative_path && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => void navigator.clipboard.writeText(preview.relative_path ?? "")}
                >
                  <Copy className="mr-2 h-4 w-4" />
                  Copiar ruta origen
                </Button>
              )}

              {filePath ? (
                <AuthenticatedFileViewer
                  filePath={filePath}
                  filenameHint={filenameHint}
                  relativePath={preview.relative_path}
                  extractedText={preview.extracted_text}
                />
              ) : (
                <p className="text-muted-foreground">No hay archivo asociado a este requisito.</p>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function NoteHistory({
  history,
}: {
  history: NonNullable<DGCPChecklistItem["note_history"]>;
}) {
  return (
    <div className="rounded-lg border bg-muted/20 p-3 space-y-2">
      <p className="text-xs font-medium uppercase text-muted-foreground">Historial de notas</p>
      {[...history].reverse().map((entry, idx) => (
        <div key={`${entry.created_at}-${idx}`} className="text-xs border-b border-border/40 pb-2 last:border-0">
          <p>{entry.note}</p>
          <p className="text-muted-foreground mt-1">
            {entry.author} · {new Date(entry.created_at).toLocaleString("es-DO")}
          </p>
        </div>
      ))}
    </div>
  );
}

function Meta({
  label,
  value,
  className,
}: {
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <div className={className}>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-medium break-all">{value}</p>
    </div>
  );
}
