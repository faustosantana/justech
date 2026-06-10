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

export default function M365OperativoPage() {
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
      title="Microsoft 365 Operativo"
      description="Email Intelligence + automatización documental — clasificación, relación y acciones en un clic"
    >
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Link href="/m365" className="text-sm text-muted-foreground hover:text-foreground">
          ← Centro M365
        </Link>
        <Button size="sm" onClick={() => void sync()} disabled={syncing}>
          <RefreshCw className={cn("mr-2 h-4 w-4", syncing && "animate-spin")} />
          Sincronizar bandeja
        </Button>
        {dashboard?.demo_mode && (
          <span className="rounded-full bg-amber-500/10 px-3 py-1 text-xs text-amber-700">
            Modo demo — conecta tu buzón en Cuentas M365 para correo real
          </span>
        )}
        {dashboard && dashboard.graph_connected && !dashboard.demo_mode && (
          <span className="rounded-full bg-emerald-500/10 px-3 py-1 text-xs text-emerald-700">
            Buzón conectado
          </span>
        )}
        {dashboard && !dashboard.graph_connected && !dashboard.demo_mode && (
          <Link
            href="/m365/cuentas"
            className="rounded-full bg-blue-500/10 px-3 py-1 text-xs text-blue-700 hover:bg-blue-500/20"
          >
            Conecta tu correo con usuario y contraseña →
          </Link>
        )}
      </div>

      {loading && <p className="text-sm text-muted-foreground">Cargando bandeja operativa…</p>}

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
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="text-xs uppercase tracking-wide text-muted-foreground">
                        {email.classification_label} · {email.classification_confidence}% confianza
                      </p>
                      <CardTitle className="mt-1 text-base">{email.subject}</CardTitle>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {email.sender_name || email.sender_email} · {email.mailbox}
                      </p>
                    </div>
                    <span className="rounded-md bg-background px-2 py-1 text-xs">{email.mailbox}</span>
                  </div>
                </CardHeader>
                <CardContent className="grid gap-4 p-4 lg:grid-cols-3">
                  <div className="space-y-2 text-sm lg:col-span-1">
                    <p className="font-medium">Extracción</p>
                    <ul className="space-y-1 text-muted-foreground">
                      {email.extracted_data.vendor ? (
                        <li>Proveedor: {String(email.extracted_data.vendor)}</li>
                      ) : null}
                      {email.extracted_data.client ? (
                        <li>Cliente: {String(email.extracted_data.client)}</li>
                      ) : null}
                      {email.extracted_data.amount != null ? (
                        <li>
                          Monto: {String(email.extracted_data.currency || "USD")}{" "}
                          {Number(email.extracted_data.amount).toLocaleString()}
                        </li>
                      ) : null}
                      {email.extracted_data.dgcp_process_code ? (
                        <li>Proceso: {String(email.extracted_data.dgcp_process_code)}</li>
                      ) : null}
                      {Array.isArray(email.extracted_data.products) &&
                      email.extracted_data.products.length > 0 ? (
                        <li>Productos: {(email.extracted_data.products as string[]).join(", ")}</li>
                      ) : null}
                    </ul>
                    {email.sharepoint_path && (
                      <p className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Archive className="h-3 w-3" />
                        {email.sharepoint_path}
                      </p>
                    )}
                  </div>
                  <div className="space-y-2 text-sm lg:col-span-1">
                    <p className="font-medium">Relaciones</p>
                    {email.relations.length === 0 ? (
                      <p className="text-muted-foreground">Sin relación automática</p>
                    ) : (
                      <ul className="space-y-1">
                        {email.relations.map((rel) => (
                          <li key={`${rel.entity_type}-${rel.label}`}>
                            {rel.href ? (
                              <Link href={rel.href} className="text-primary hover:underline">
                                {rel.label}
                              </Link>
                            ) : (
                              rel.label
                            )}
                            <span className="ml-1 text-xs text-muted-foreground">({rel.confidence}%)</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                  <div className="space-y-2 lg:col-span-1">
                    <p className="flex items-center gap-1 text-sm font-medium">
                      <Zap className="h-4 w-4" />
                      Acciones sugeridas
                    </p>
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
                  No hay correos procesados. Pulsa «Sincronizar bandeja» para cargar la demo operativa.
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
