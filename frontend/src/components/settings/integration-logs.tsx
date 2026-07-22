"use client";

import type { SettingsAuditEntry } from "@/lib/settings";

const ACTION_LABELS: Record<string, string> = {
  "settings.integration_updated": "Configuración actualizada",
  "settings.integration_tested": "Prueba de conexión",
  "settings.integration_disconnected": "Desconectado",
};

export function IntegrationLogs({ logs }: { logs: SettingsAuditEntry[] }) {
  if (!logs.length) {
    return <p className="text-sm text-muted-foreground">Sin eventos recientes.</p>;
  }

  return (
    <div className="space-y-2">
      {logs.map((log) => (
        <div key={log.id} className="rounded-lg border border-border px-3 py-2 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-medium">{ACTION_LABELS[log.action] || log.action}</span>
            <span className="text-xs text-muted-foreground">
              {new Date(log.created_at).toLocaleString("es-DO")}
            </span>
          </div>
          {log.details?.message != null && (
            <p className="mt-1 text-muted-foreground">{String(log.details.message)}</p>
          )}
          {log.details?.ok != null && (
            <p className={log.details.ok ? "text-success" : "text-destructive"}>
              {log.details.ok ? "Prueba exitosa" : "Prueba fallida"}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
