"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Cloud,
  FolderSync,
  History,
  RefreshCw,
  Zap,
} from "lucide-react";

import { DocumentsHubM365Panel } from "@/components/documents/documents-hub-m365-panel";
import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";
import type { RepositoryBinding, RepositorySyncJob } from "@/lib/settings";

const STATUS_STYLES: Record<string, string> = {
  synced: "bg-emerald-500/15 text-emerald-700 border-emerald-500/30",
  configured: "bg-blue-500/15 text-blue-700 border-blue-500/30",
  error: "bg-red-500/15 text-red-700 border-red-500/30",
  pending: "bg-amber-500/15 text-amber-700 border-amber-500/30",
  not_configured: "bg-muted text-muted-foreground",
};

const TYPE_LABELS: Record<string, string> = {
  company_data: "Datos empresas",
  legal_documents: "Documentos legales",
  dgcp_templates: "Plantillas DGCP",
  price_inbox: "Precios / Entradas",
  price_processed: "Precios / Procesados",
  licitations: "Licitaciones",
  outputs: "Salidas",
};

export default function DocumentosRepositoriosPage() {
  const [bindings, setBindings] = useState<RepositoryBinding[]>([]);
  const [jobs, setJobs] = useState<RepositorySyncJob[]>([]);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [syncingAll, setSyncingAll] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    apiClient
      .getDocumentsHubRepositories()
      .then((b) => {
        setBindings(b);
        return apiClient.getRepositorySyncJobs(30).then(setJobs).catch(() => setJobs([]));
      })
      .catch((err) => {
        setBindings([]);
        setJobs([]);
        setError(
          err instanceof ApiError
            ? err.message
            : "No se pudieron cargar los repositorios. Verifique su conexión M365.",
        );
      });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const sync = async (id: string) => {
    setSyncing(id);
    try {
      await apiClient.syncDocumentsHubRepository(id);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al sincronizar carpeta.");
    } finally {
      setSyncing(null);
    }
  };

  const syncAll = async () => {
    setSyncingAll(true);
    try {
      await apiClient.syncAllSettingsRepositories();
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al sincronizar todos los repositorios.");
    } finally {
      setSyncingAll(false);
    }
  };

  const configured = bindings.filter((b) => b.id && b.status !== "not_configured").length;

  return (
    <AppShell
      title="Repositorios OneDrive"
      description="Carpetas Justech-AI sincronizadas con JAIOS"
    >
      {error && (
        <Card className="mb-4 border-amber-500/40 bg-amber-500/5">
          <CardContent className="flex items-center gap-2 py-3 text-sm text-amber-800">
            <AlertTriangle className="h-4 w-4" />
            {error}
          </CardContent>
        </Card>
      )}

      <DocumentsHubM365Panel bindings={bindings} onPersisted={load} />

      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-transparent">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Cloud className="h-4 w-4 text-primary" />
              Repositorios
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold">{configured}/{bindings.length}</p>
            <p className="text-xs text-muted-foreground">configurados</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <FolderSync className="h-4 w-4" />
              Auto-sync
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold">{bindings.filter((b) => b.auto_sync).length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Zap className="h-4 w-4" />
              Acciones
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Button size="sm" onClick={syncAll} disabled={syncingAll}>
              <RefreshCw className={`mr-2 h-4 w-4 ${syncingAll ? "animate-spin" : ""}`} />
              Sincronizar todos
            </Button>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4">
        {bindings.length === 0 && !error && (
          <Card>
            <CardContent className="py-8 text-center text-sm text-muted-foreground">
              No hay carpetas configuradas. Conecte Microsoft 365 en Configuración y pulse «Sincronizar todos».
            </CardContent>
          </Card>
        )}
        {bindings.map((binding) => (
          <Card key={binding.folder_key} className={binding.status === "error" ? "border-red-500/40" : undefined}>
            <CardHeader className="flex flex-row items-start justify-between gap-4 pb-2">
              <div>
                <CardTitle className="text-base">{binding.label}</CardTitle>
                <CardDescription className="font-mono text-xs">
                  {binding.folder_key}
                  {binding.folder_path ? ` · ${binding.folder_path}` : " · Sin ruta"}
                </CardDescription>
              </div>
              <Badge variant="outline" className={STATUS_STYLES[binding.status] || STATUS_STYLES.not_configured}>
                {binding.status}
              </Badge>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-wrap items-center gap-4 text-sm">
                {binding.repository_type && (
                  <Badge variant="secondary">{TYPE_LABELS[binding.repository_type] || binding.repository_type}</Badge>
                )}
                <span className="text-muted-foreground">{binding.indexed_files} archivos</span>
                {binding.last_sync_at && (
                  <span className="text-xs text-muted-foreground">
                    Última: {new Date(binding.last_sync_at).toLocaleString()}
                  </span>
                )}
                {binding.web_url && (
                  <a href={binding.web_url} target="_blank" rel="noreferrer" className="text-xs text-primary hover:underline">
                    Abrir carpeta
                  </a>
                )}
                {binding.id && (
                  <Button size="sm" variant="outline" onClick={() => sync(binding.id!)} disabled={syncing === binding.id}>
                    {syncing === binding.id ? "Sincronizando…" : "Sincronizar ahora"}
                  </Button>
                )}
              </div>
              {binding.last_error && (
                <p className="flex items-start gap-2 rounded-md bg-red-500/10 p-2 text-xs text-red-700">
                  <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  {binding.last_error}
                </p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <History className="h-4 w-4" />
            Historial de sincronización
          </CardTitle>
        </CardHeader>
        <CardContent>
          {jobs.length === 0 ? (
            <p className="text-sm text-muted-foreground">Sin jobs registrados aún.</p>
          ) : (
            <div className="space-y-2">
              {jobs.map((j) => (
                <div key={j.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm">
                  <div className="flex items-center gap-2">
                    {j.status === "completed" ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                    ) : (
                      <AlertCircle className="h-4 w-4 text-amber-600" />
                    )}
                    <span className="font-medium">{j.trigger}</span>
                    <Badge variant="outline">{j.status}</Badge>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {j.files_synced} archivos · {j.records_indexed} indexados
                    {j.started_at && ` · ${new Date(j.started_at).toLocaleString()}`}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </AppShell>
  );
}
