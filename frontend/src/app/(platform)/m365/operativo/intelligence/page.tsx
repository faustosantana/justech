"use client";

import {
  Archive,
  ArrowRight,
  FileText,
  Mail,
  RefreshCw,
  Sparkles,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import type { M365OperativeDashboard, M365ProcessedEmail } from "@/lib/m365-operative";
import { cn } from "@/lib/utils";

/** Bandeja inteligente — clasificación DGCP, n8n, acciones sugeridas */
export default function M365OperativeIntelligencePage() {
  const router = useRouter();
  const [dashboard, setDashboard] = useState<M365OperativeDashboard | null>(null);
  const [emails, setEmails] = useState<M365ProcessedEmail[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!getAccessToken()) {
      router.replace("/login");
      return;
    }
    setLoading(true);
    try {
      const [dash, list] = await Promise.all([
        apiClient.getM365OperativeDashboard(),
        apiClient.getM365OperativeEmails(),
      ]);
      setDashboard(dash);
      setEmails(list.items);
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  const sync = async () => {
    setSyncing(true);
    try {
      await apiClient.syncM365OperativeInbox();
      await load();
    } finally {
      setSyncing(false);
    }
  };

  const runAction = async (emailId: string, actionKey: string) => {
    setActionLoading(`${emailId}:${actionKey}`);
    try {
      await apiClient.executeM365OperativeAction(emailId, actionKey);
      await load();
    } finally {
      setActionLoading(null);
    }
  };

  const kpis = dashboard
    ? [
        { label: "Correos hoy", value: dashboard.emails_today },
        { label: "Adjuntos procesados", value: dashboard.attachments_processed },
        { label: "Cotizaciones", value: dashboard.quotes_detected },
        { label: "Facturas", value: dashboard.invoices_detected },
        { label: "Órdenes", value: dashboard.purchase_orders_detected },
        { label: "Tareas generadas", value: dashboard.tasks_generated },
        { label: "Indexados Hermes", value: dashboard.documents_indexed },
      ]
    : [];

  return (
    <AppShell
      title="M365 Email Intelligence"
      description="Clasificación automática, relación DGCP/Odoo y acciones en un clic"
    >
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Link href="/m365/operativo" className="text-sm text-muted-foreground hover:text-foreground">
          ← Outlook M365
        </Link>
        <Button size="sm" onClick={() => void sync()} disabled={syncing}>
          <RefreshCw className={cn("mr-2 h-4 w-4", syncing && "animate-spin")} />
          Sincronizar bandeja
        </Button>
        {dashboard?.demo_mode && (
          <span className="rounded-full bg-amber-500/10 px-3 py-1 text-xs text-amber-700">
            Modo demo — conecte OAuth en Cuentas para correo real
          </span>
        )}
      </div>

      {loading && <p className="text-sm text-muted-foreground">Cargando…</p>}

      {!loading && dashboard && (
        <>
          <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
            {kpis.map((k) => (
              <Card key={k.label} className="border-border/80">
                <CardContent className="p-4">
                  <p className="text-2xl font-semibold tabular-nums">{k.value}</p>
                  <p className="text-xs text-muted-foreground">{k.label}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          {dashboard.briefing_lines.length > 0 && (
            <Card className="mb-6 border-primary/20 bg-primary/5">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Sparkles className="h-4 w-4 text-primary" />
                  Resumen proactivo
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1 text-sm">
                {dashboard.briefing_lines.map((line) => (
                  <p key={line}>{line}</p>
                ))}
              </CardContent>
            </Card>
          )}

          <div className="space-y-4">
            {emails.map((email) => (
              <Card key={email.id} className="overflow-hidden">
                <CardHeader className="border-b border-border/60 bg-muted/20 pb-3">
                  <CardTitle className="text-base">{email.subject}</CardTitle>
                  <p className="text-sm text-muted-foreground">
                    {email.sender_name || email.sender_email} · {email.classification_label}
                  </p>
                </CardHeader>
                <CardContent className="p-4">
                  <div className="flex flex-wrap gap-2">
                    {email.suggested_actions.map((action) => (
                      <Button
                        key={action.key}
                        size="sm"
                        variant="secondary"
                        disabled={actionLoading === `${email.id}:${action.key}`}
                        onClick={() => void runAction(email.id, action.key)}
                      >
                        {action.label}
                      </Button>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {emails.length === 0 && (
            <Card>
              <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
                <Mail className="h-10 w-10 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">
                  Sin correos procesados. Sincronice la bandeja o conecte OAuth.
                </p>
                <Button onClick={() => void sync()}>
                  Sincronizar
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </AppShell>
  );
}
