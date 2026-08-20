"use client";

import { useState } from "react";
import { ExternalLink, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import type { DGCPOpportunity } from "@/lib/dgcp";

type Props = {
  opportunity: DGCPOpportunity;
  onUpdated?: (opp: DGCPOpportunity) => void;
};

export function DgcpOdooSyncCard({ opportunity, onUpdated }: Props) {
  const sync = ((opportunity as DGCPOpportunity & { full_info?: Record<string, unknown> }).full_info
    ?.odoo_sync || undefined) as Record<string, unknown> | undefined;
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  if (!sync && !isDGCPPrepOrLater(opportunity.status)) return null;

  const status = String(sync?.status || "—");
  const fullInfo = (opportunity as DGCPOpportunity & { full_info?: Record<string, unknown> }).full_info;
  const crmUrl = String(sync?.crm_opportunity_url || fullInfo?.odoo_crm_opportunity_url || "");
  const soUrl = String(sync?.sale_order_url || "");
  const pending = status === "sync_pending";
  const synced = status === "synced";
  const owner =
    (sync?.jaios_owner as { name?: string; email?: string; id?: string } | undefined) ||
    undefined;
  const responsible =
    opportunity.responsible_name ||
    owner?.name ||
    (typeof fullInfo?.responsible_name === "string" ? fullInfo.responsible_name : null);

  async function retry() {
    setBusy(true);
    setMsg(null);
    try {
      const res = await apiClient.retryDGCPOdooSync(opportunity.id);
      setMsg(res.result?.ok ? "Sincronización OK" : res.result?.error || "Reintento registrado");
      const fresh = await apiClient.getDGCPOpportunity(opportunity.id);
      onUpdated?.(fresh);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Error al reintentar");
    } finally {
      setBusy(false);
    }
  }

  const statusLabel = synced ? "✅ Sincronizado" : pending ? "⚠ Pendiente" : status === "—" ? "—" : "❌ Error";

  return (
    <Card className="border-primary/20">
      <CardHeader className="flex flex-row items-center justify-between py-3">
        <CardTitle className="text-sm">Odoo CRM / Cotización</CardTitle>
        {(pending || status === "error") && (
          <Button size="sm" variant="outline" disabled={busy} onClick={() => void retry()}>
            <RefreshCw className={`mr-1 h-3.5 w-3.5 ${busy ? "animate-spin" : ""}`} />
            Reintentar sincronización
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-2 text-xs text-muted-foreground">
        {responsible ? (
          <p>
            Responsable: <span className="font-medium text-foreground">{responsible}</span>
          </p>
        ) : null}
        <p>
          Sincronización Odoo: <span className="font-medium text-foreground">{statusLabel}</span>
          {sync?.retry_count != null ? ` · reintentos: ${String(sync.retry_count)}` : ""}
        </p>
        {sync?.crm_opportunity_name || sync?.crm_opportunity_id ? (
          <p>
            Oportunidad:{" "}
            <span className="font-medium text-foreground">
              {String(sync?.crm_opportunity_name || `#${sync?.crm_opportunity_id}`)}
            </span>
          </p>
        ) : null}
        {sync?.sale_order_name ? (
          <p>
            Cotización: <span className="font-medium text-foreground">{String(sync.sale_order_name)}</span>
          </p>
        ) : null}
        {sync?.last_error ? <p className="text-destructive">Error: {String(sync.last_error)}</p> : null}
        <div className="flex flex-wrap gap-2 pt-1">
          {crmUrl ? (
            <a
              href={crmUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-primary hover:underline"
            >
              Abrir en Odoo <ExternalLink className="h-3 w-3" />
            </a>
          ) : (
            <span>Sin oportunidad CRM aún</span>
          )}
          {soUrl ? (
            <a
              href={soUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-primary hover:underline"
            >
              Cotización <ExternalLink className="h-3 w-3" />
            </a>
          ) : null}
        </div>
        {msg ? <p className="text-foreground">{msg}</p> : null}
      </CardContent>
    </Card>
  );
}

function isDGCPPrepOrLater(status: string) {
  return [
    "interested",
    "preparing",
    "ready_to_submit",
    "submitted",
    "under_evaluation",
    "suspended",
    "awarded",
    "won",
    "lost",
  ].includes(status);
}
