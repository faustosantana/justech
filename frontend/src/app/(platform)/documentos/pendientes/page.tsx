"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Mail, RefreshCw } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";
import type { DocumentPendingItem } from "@/lib/documents-hub";
import { cn } from "@/lib/utils";

const SEVERITY_STYLES: Record<string, string> = {
  missing: "bg-amber-500/15 text-amber-800",
  expired: "bg-red-500/15 text-red-800",
};

export default function DocumentosPendientesPage() {
  const [items, setItems] = useState<DocumentPendingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    apiClient
      .getDocumentsHubPending()
      .then(setItems)
      .catch((err) => {
        setItems([]);
        setError(err instanceof ApiError ? err.message : "No se pudieron cargar los pendientes.");
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const scan = async () => {
    await apiClient.scanDocumentsHubPending();
    load();
  };

  const markReceived = async (id: string) => {
    await apiClient.markDocumentsPendingReceived(id);
    load();
  };

  return (
    <AppShell title="Pendientes documentales" description="Detección automática de información y documentos faltantes">
      <div className="mb-4 flex gap-2">
        <Button size="sm" onClick={scan} disabled={loading}>
          <RefreshCw className={cn("mr-2 h-4 w-4", loading && "animate-spin")} />
          Escanear faltantes
        </Button>
        <Button size="sm" variant="outline" onClick={load}>
          Actualizar
        </Button>
      </div>

      {error && (
        <Card className="mb-4 border-amber-500/40 bg-amber-500/5">
          <CardContent className="flex items-center gap-2 py-3 text-sm text-amber-800">
            <AlertTriangle className="h-4 w-4" />
            {error}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Centro de pendientes</CardTitle>
        </CardHeader>
        <CardContent>
          {items.length === 0 && !loading && (
            <p className="text-sm text-muted-foreground">Sin pendientes detectados. Ejecute un escaneo.</p>
          )}
          <div className="space-y-2">
            {items.map((item) => (
              <div
                key={item.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border px-4 py-3"
              >
                <div>
                  <p className="font-medium">{item.company_label}</p>
                  <p className="text-sm text-muted-foreground">{item.item_label}</p>
                  <p className="text-xs text-muted-foreground">
                    Detectado: {new Date(item.detected_at).toLocaleDateString()} · {item.responsible}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge className={SEVERITY_STYLES[item.severity] || ""}>{item.severity}</Badge>
                  <Badge variant="outline">{item.status}</Badge>
                  {item.status !== "resolved" && (
                    <Button size="sm" variant="outline" onClick={() => markReceived(item.id)}>
                      <CheckCircle2 className="mr-1 h-4 w-4" />
                      Recibido
                    </Button>
                  )}
                  {item.onedrive_path && (
                    <span className="max-w-[200px] truncate text-xs text-muted-foreground" title={item.onedrive_path}>
                      {item.onedrive_path}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </AppShell>
  );
}
