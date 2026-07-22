"use client";

import { AlertTriangle, Download, FileJson, FileText, FolderOpen, Loader2, PackageCheck } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import {
  REAL_EXPEDIENTE_STATUS_LABELS,
  type RealExpedienteStatus,
  type RealExpedienteValidation,
} from "@/lib/dgcp";

const FOLDER_LABELS: Record<string, string> = {
  "01_Documentos_Legales": "Documentos legales",
  "02_Formularios": "Formularios",
  "03_Oferta_Tecnica": "Oferta técnica",
  "04_Oferta_Economica": "Oferta económica",
  "05_Fichas_Tecnicas": "Fichas técnicas",
  "06_Cartas_Fabricante": "Cartas fabricante",
  "07_Revision": "Revisión",
  "08_Listo_Para_Subir": "Listo para subir",
};

interface Props {
  opportunityId: string;
  busy?: boolean;
  onUpdated?: () => void;
}

export function RealExpedientePanel({ opportunityId, busy, onUpdated }: Props) {
  const [status, setStatus] = useState<RealExpedienteStatus | null>(null);
  const [validation, setValidation] = useState<RealExpedienteValidation | null>(null);
  const [panelBusy, setPanelBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [manifestOpen, setManifestOpen] = useState(false);
  const [manifestPreview, setManifestPreview] = useState<string>("");

  const load = useCallback(async () => {
    try {
      const [st, val] = await Promise.all([
        apiClient.getRealExpedienteStatus(opportunityId),
        apiClient.validateRealExpediente(opportunityId).catch(() => null),
      ]);
      setStatus(st);
      setValidation(val);
    } catch {
      setStatus(null);
    }
  }, [opportunityId]);

  useEffect(() => {
    void load();
  }, [load]);

  const run = async (action: () => Promise<unknown>, okMsg: string) => {
    setPanelBusy(true);
    setError(null);
    setMessage(null);
    try {
      await action();
      setMessage(okMsg);
      await load();
      onUpdated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error en expediente real");
    } finally {
      setPanelBusy(false);
    }
  };

  const statusLabel =
    REAL_EXPEDIENTE_STATUS_LABELS[status?.status ?? "sin_generar"] ?? "Sin generar";
  const disabled = busy || panelBusy;

  return (
    <Card className="border-emerald-500/30 bg-emerald-500/5">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <PackageCheck className="h-4 w-4 text-emerald-600" />
          Expediente Real DGCP — {statusLabel}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-xs text-amber-700 dark:text-amber-400 flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
          JAIOS no sube automáticamente a Compras Públicas. Revise y suba manualmente al portal DGCP.
        </p>

        {status && (
          <div className="rounded-md border bg-background p-3 text-sm grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <p className="text-xs text-muted-foreground">Expediente</p>
              <p className="font-medium">{status.presentation_expediente}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Paquete DGCP</p>
              <p className="font-medium">{status.presentation_package}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">ZIP</p>
              <p className="font-medium">{status.presentation_zip}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Presentación</p>
              <p className="font-medium">{status.presentation_upload}</p>
            </div>
          </div>
        )}

        {validation && (
          <div className="rounded-md border bg-background p-3 text-sm space-y-2">
            <p>
              Preparación general: <strong>{validation.preparation_pct.toFixed(0)}%</strong>
            </p>
            {validation.completed.length > 0 && (
              <div>
                <p className="text-xs font-medium text-muted-foreground uppercase">Completado</p>
                <ul className="list-disc pl-4">
                  {validation.completed.slice(0, 8).map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              </div>
            )}
            {validation.missing.length > 0 && (
              <div>
                <p className="text-xs font-medium text-red-600 uppercase">Faltantes</p>
                <ul className="list-disc pl-4 text-red-700 dark:text-red-400">
                  {validation.missing.slice(0, 8).map((m) => (
                    <li key={m}>{m}</li>
                  ))}
                </ul>
              </div>
            )}
            {validation.warnings.length > 0 && (
              <div>
                <p className="text-xs font-medium text-amber-600 uppercase">Advertencias</p>
                <ul className="list-disc pl-4">
                  {validation.warnings.slice(0, 6).map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          <Button
            disabled={disabled}
            onClick={() =>
              void run(
                () => apiClient.generateRealExpediente(opportunityId),
                "Expediente real generado",
              )
            }
            title="Genera la estructura de carpetas del expediente real DGCP"
          >
            {panelBusy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Generar Expediente Real
          </Button>
          <Button
            variant="default"
            disabled={disabled || !validation?.can_prepare_package}
            title={
              !validation?.can_prepare_package
                ? "Complete checklist y documentos antes de preparar el paquete DGCP"
                : "Empaqueta archivos según estructura DGCP"
            }
            onClick={() =>
              void run(
                () => apiClient.prepareDGCPSubmissionPackage(opportunityId),
                "Paquete DGCP preparado",
              )
            }
          >
            Preparar Paquete DGCP
          </Button>
          <Button
            variant="outline"
            disabled={disabled || !status?.can_download}
            title={!status?.can_download ? "Genere el expediente real primero" : "Descargar ZIP del expediente"}
            onClick={() => void run(() => apiClient.downloadRealExpedienteZip(opportunityId), "ZIP descargado")}
          >
            <Download className="mr-2 h-4 w-4" />
            Descargar Expediente ZIP
          </Button>
          <Button
            variant="outline"
            disabled={disabled || !status?.expediente_path}
            title={!status?.expediente_path ? "Genere el expediente real primero" : "Descargar reporte PDF del expediente"}
            onClick={() => void run(() => apiClient.downloadRealExpedienteReport(opportunityId), "Reporte descargado")}
          >
            <FileText className="mr-2 h-4 w-4" />
            Descargar Reporte PDF
          </Button>
          <Button
            variant="secondary"
            disabled={disabled || !status?.can_mark_ready_review}
            title={!status?.can_mark_ready_review ? "El expediente debe estar completo y validado" : undefined}
            onClick={() =>
              void run(
                () => apiClient.markRealExpedienteReadyReview(opportunityId),
                "Marcado listo para revisión",
              )
            }
          >
            Marcar listo para revisión
          </Button>
          <Button
            variant="secondary"
            disabled={disabled || !status?.can_mark_ready_upload}
            title={!status?.can_mark_ready_upload ? "Complete revisión interna antes de marcar listo para subir" : undefined}
            onClick={() =>
              void run(
                () => apiClient.markRealExpedienteReadyUpload(opportunityId),
                "Marcado listo para subir",
              )
            }
          >
            Marcar listo para subir
          </Button>
          <Button
            variant="ghost"
            disabled={disabled}
            onClick={async () => {
              setPanelBusy(true);
              try {
                const m = await apiClient.getRealExpedienteManifest(opportunityId);
                setManifestPreview(JSON.stringify(m, null, 2));
                setManifestOpen(true);
              } catch {
                setError("Manifest no disponible");
              } finally {
                setPanelBusy(false);
              }
            }}
          >
            <FileJson className="mr-2 h-4 w-4" />
            Ver Manifest
          </Button>
          <Button variant="ghost" disabled title="Disponible en futura versión. Requiere autenticación oficial del portal DGCP.">
            Subir a Compras y Contrataciones
          </Button>
        </div>

        {status && (
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4 text-sm">
            {REAL_EXPEDIENTE_FOLDERS.map((folder) => (
              <div key={folder} className="flex items-center gap-2 rounded border px-2 py-1">
                <FolderOpen className="h-3 w-3 text-muted-foreground" />
                <span className="truncate">{FOLDER_LABELS[folder] ?? folder}</span>
                <span className="ml-auto font-mono text-xs">{status.folder_counts[folder] ?? 0}</span>
              </div>
            ))}
          </div>
        )}

        {(status?.missing?.length ?? 0) > 0 && (
          <ListBlock title="Faltantes" items={status!.missing.map((m) => String(m.name ?? m))} />
        )}
        {(status?.expired?.length ?? 0) > 0 && (
          <ListBlock title="Vencidos" items={status!.expired.map((e) => String(e.name ?? e))} />
        )}
        {(status?.requires_review?.length ?? 0) > 0 && (
          <ListBlock
            title="En revisión"
            items={status!.requires_review.map((r) => String(r.name ?? r))}
          />
        )}
        {(status?.ready_to_upload?.length ?? 0) > 0 && (
          <ListBlock
            title="Listos para subir"
            items={status!.ready_to_upload.map((r) => String(r.name ?? r.file ?? r))}
          />
        )}

        {message && <p className="text-sm text-emerald-700">{message}</p>}
        {error && <p className="text-sm text-destructive">{error}</p>}

        {manifestOpen && (
          <pre className="max-h-64 overflow-auto rounded border bg-muted p-2 text-xs">
            {manifestPreview}
          </pre>
        )}
      </CardContent>
    </Card>
  );
}

function ListBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="text-xs font-medium text-muted-foreground uppercase mb-1">{title}</p>
      <ul className="list-disc pl-4 text-sm space-y-0.5">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export const REAL_EXPEDIENTE_FOLDERS = [
  "01_Documentos_Legales",
  "02_Formularios",
  "03_Oferta_Tecnica",
  "04_Oferta_Economica",
  "05_Fichas_Tecnicas",
  "06_Cartas_Fabricante",
  "07_Revision",
  "08_Listo_Para_Subir",
] as const;
