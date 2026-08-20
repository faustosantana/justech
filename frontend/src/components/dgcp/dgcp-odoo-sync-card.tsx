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

  return (
    <Card className="border-primary/20">
      <CardHeader className="flex flex-row items-center justify-between py-3">
        <CardTitle className="text-sm">Odoo CRM / Cotización</CardTitle>
        {pending && (
          <Button size="sm" variant="outline" disabled={busy} onClick={() => void retry()}>
            <RefreshCw className={`mr-1 h-3.5 w-3.5 ${busy ? "animate-spin" : ""}`} />
            Reintentar sync
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-2 text-xs text-muted-foreground">
        <p>
          Estado sync: <span className="font-medium text-foreground">{status}</span>
          {sync?.retry_count != null ? ` · reintentos: ${String(sync.retry_count)}` : ""}
        </p>
        {sync?.last_error ? <p className="text-destructive">Error: {String(sync.last_error)}</p> : null}
        <div className="flex flex-wrap gap-2">
          {crmUrl ? (
            <a href={crmUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-primary hover:underline">
              Oportunidad CRM <ExternalLink className="h-3 w-3" />
            </a>
          ) : (
            <span>Sin oportunidad CRM aún</span>
          )}
          {soUrl ? (
            <a href={soUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-primary hover:underline">
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
