"use client";

import Link from "next/link";
import { AlertCircle, Cloud, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api";

type TemplateOperationalStatus = Awaited<ReturnType<typeof apiClient.getM365TemplatesOperationalStatus>>;

type Props = {
  compact?: boolean;
  className?: string;
};

export function M365TemplateOperationalBanner({ compact = false, className = "" }: Props) {
  const [status, setStatus] = useState<TemplateOperationalStatus | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setStatus(await apiClient.getM365TemplatesOperationalStatus());
    } catch {
      setStatus(null);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const sync = async () => {
    setSyncing(true);
    setMessage(null);
    try {
      const res = await apiClient.syncM365OfficialTemplates();
      setMessage(`Caché actualizada: ${res.cache_ok} nuevas · total ${res.cache_count}`);
      await load();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Error al sincronizar");
    } finally {
      setSyncing(false);
    }
  };

  if (!status) return null;

  const cacheOk = status.cache_missing_docx === 0 && status.cache_count > 0;
  const border = !status.oauth_connected && !cacheOk
    ? "border-destructive/40 bg-destructive/5"
    : status.cache_missing_docx > 0
      ? "border-amber-500/40 bg-amber-500/5"
      : "border-emerald-500/30 bg-emerald-500/5";

  return (
    <div className={`rounded-lg border p-4 text-sm ${border} ${className}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="font-medium flex items-center gap-2">
            <Cloud className="h-4 w-4" />
            Plantillas oficiales M365
          </p>
          {!compact && (
            <>
              <p>
                OAuth:{" "}
                <span className={status.oauth_connected ? "text-emerald-700" : "text-destructive"}>
                  {status.oauth_connected ? `Conectado (${status.oauth_email})` : "Desconectado"}
                </span>
                {" · "}
                Caché: <strong>{status.cache_count}</strong> DOCX
                {status.cache_missing_docx > 0 ? ` · ${status.cache_missing_docx} pendientes` : ""}
              </p>
              <p className="text-xs text-muted-foreground">
                Fuente autollenado:{" "}
                {status.oauth_connected
                  ? "SharePoint/M365 en vivo o caché oficial"
                  : cacheOk
                    ? "caché oficial DGCP (OAuth no requerido)"
                    : "sin plantilla disponible hasta reconectar o sincronizar"}
                {status.last_cache_bootstrap_at ? ` · caché: ${status.last_cache_bootstrap_at.slice(0, 16)}` : ""}
              </p>
            </>
          )}
          {compact && (
            <p className="text-xs text-muted-foreground">
              {status.oauth_connected ? "M365 conectado" : "OAuth off"}
              {" · "}
              caché {status.cache_count}
              {status.cache_missing_docx > 0 ? ` · ${status.cache_missing_docx} sin caché` : ""}
            </p>
          )}
          {status.message && !cacheOk && (
            <p className="text-xs text-amber-800 flex items-center gap-1">
              <AlertCircle className="h-3.5 w-3.5" />
              {status.message}
            </p>
          )}
          {message && <p className="text-xs">{message}</p>}
        </div>
        <div className="flex flex-wrap gap-2">
          {!status.oauth_connected && (
            <Button size="sm" variant="outline" asChild>
              <Link href="/m365/cuentas">Reconectar M365</Link>
            </Button>
          )}
          <Button size="sm" variant="secondary" onClick={() => void sync()} disabled={syncing || !status.oauth_connected}>
            <RefreshCw className={`mr-1 h-3.5 w-3.5 ${syncing ? "animate-spin" : ""}`} />
            Sync caché
          </Button>
        </div>
      </div>
    </div>
  );
}
