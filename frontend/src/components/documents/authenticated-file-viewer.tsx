"use client";

import { Copy, Download, ExternalLink, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  downloadAuthenticatedBlob,
  fetchAuthenticatedFile,
  isPdfContent,
  openAuthenticatedBlobInNewTab,
  revokeAuthenticatedFileUrl,
  type AuthenticatedFilePayload,
} from "@/lib/authenticated-file";

interface AuthenticatedFileViewerProps {
  /** Ruta API: `/knowledge/assets/{id}/file` o URL absoluta con /api/v1 */
  filePath: string | null;
  /** Nombre sugerido si el servidor no envía Content-Disposition */
  filenameHint?: string;
  relativePath?: string | null;
  extractedText?: string | null;
  className?: string;
}

export function AuthenticatedFileViewer({
  filePath,
  filenameHint = "documento",
  relativePath,
  extractedText,
  className,
}: AuthenticatedFileViewerProps) {
  const [file, setFile] = useState<AuthenticatedFilePayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!filePath) return;
    setLoading(true);
    setError(null);
    setFile((prev) => {
      if (prev) revokeAuthenticatedFileUrl(prev.objectUrl);
      return null;
    });
    try {
      const payload = await fetchAuthenticatedFile(filePath);
      setFile(payload);
    } catch (err) {
      if (err instanceof Error && err.message === "UNAUTHORIZED") {
        setError("Sesión expirada. Inicia sesión nuevamente.");
      } else {
        setError(err instanceof Error ? err.message : "No se pudo cargar el archivo.");
      }
    } finally {
      setLoading(false);
    }
  }, [filePath]);

  useEffect(() => {
    void load();
    return () => {
      setFile((prev) => {
        if (prev) revokeAuthenticatedFileUrl(prev.objectUrl);
        return null;
      });
    };
  }, [load]);

  const displayName = file?.filename ?? filenameHint;
  const showPdf = file && isPdfContent(file.contentType, displayName);

  return (
    <div className={className}>
      {loading && (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Cargando archivo…
        </p>
      )}

      {error && <p className="text-sm text-destructive">{error}</p>}

      {file && !loading && (
        <>
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => openAuthenticatedBlobInNewTab(file.objectUrl)}
            >
              <ExternalLink className="mr-2 h-4 w-4" />
              Abrir en nueva pestaña
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => downloadAuthenticatedBlob(file.blob, displayName)}
            >
              <Download className="mr-2 h-4 w-4" />
              Descargar
            </Button>
            {relativePath && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => void navigator.clipboard.writeText(relativePath)}
              >
                <Copy className="mr-2 h-4 w-4" />
                Copiar ruta
              </Button>
            )}
          </div>

          {showPdf && (
            <iframe
              title={displayName}
              src={file.objectUrl}
              className="mt-3 w-full h-[420px] rounded border"
            />
          )}

          {!showPdf && (
            <p className="mt-2 text-xs text-muted-foreground">
              Vista previa no disponible para este formato — use Descargar o Abrir en nueva pestaña.
            </p>
          )}
        </>
      )}

      {extractedText !== undefined && (
        <div className="mt-4">
          <p className="text-xs font-medium uppercase text-muted-foreground mb-2">Texto extraído</p>
          <pre className="max-h-64 overflow-auto rounded border bg-muted/30 p-3 text-xs whitespace-pre-wrap">
            {extractedText?.trim() || "Sin texto extraído — use descarga y validación manual."}
          </pre>
        </div>
      )}
    </div>
  );
}
