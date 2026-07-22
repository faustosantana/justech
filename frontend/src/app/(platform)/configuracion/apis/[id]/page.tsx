"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Trash2 } from "lucide-react";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { DynamicConnectorForm } from "@/components/admin/dynamic-connector-form";
import { EndpointBuilder } from "@/components/admin/endpoint-builder";
import { TestConnectionPanel } from "@/components/admin/test-connection-panel";
import { IntegrationLogs } from "@/components/settings/integration-logs";
import { ConnectionStatusBadge } from "@/components/settings/connection-status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";
import type { ConnectorCreatePayload, ConnectorDetail } from "@/lib/connectors";
import type { IntegrationStatus } from "@/lib/settings";

export default function ConectorDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [detail, setDetail] = useState<ConnectorDetail | null>(null);
  const [form, setForm] = useState<ConnectorCreatePayload | null>(null);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testMsg, setTestMsg] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await apiClient.getAdminIntegration(id) as ConnectorDetail;
      setDetail(res);
      setForm({
        name: res.name,
        connector_type: res.connector_type as ConnectorCreatePayload["connector_type"],
        auth_method: res.auth_method as ConnectorCreatePayload["auth_method"],
        base_url: res.base_url || "",
        config: res.config,
        secrets: {},
        user_link_mode: res.user_link_mode,
        documentation: res.documentation || "",
        read_only: res.read_only,
        environment: res.environment,
        endpoints: res.endpoints,
      });
    } catch {
      setError("Conector no encontrado.");
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  const save = async () => {
    if (!form) return;
    setSaving(true);
    try {
      await apiClient.updateConnector(id, form as unknown as Record<string, unknown>);
      await load();
      setTestMsg("Configuración actualizada.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al guardar.");
    } finally {
      setSaving(false);
    }
  };

  const test = async () => {
    setTesting(true);
    setTestMsg(null);
    try {
      const res = await apiClient.testConnector(id);
      setTestMsg(res.message);
      setPreview(res.response_preview || null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Prueba fallida.");
    } finally {
      setTesting(false);
    }
  };

  const remove = async () => {
    if (!confirm("¿Eliminar este conector?")) return;
    await apiClient.deleteConnector(id);
    router.push("/configuracion/apis");
  };

  if (!form || !detail) {
    return error ? <p className="text-destructive">{error}</p> : <p className="text-muted-foreground">Cargando…</p>;
  }

  return (
    <div>
      <AdminPageHeader
        title={detail.name}
        description={`Conector dinámico · ${detail.slug}`}
        action={
          <div className="flex gap-2">
            <ConnectionStatusBadge status={detail.status as IntegrationStatus} connected={detail.connected} />
            <Button variant="outline" size="sm" asChild>
              <Link href="/configuracion/apis"><ArrowLeft className="mr-2 h-4 w-4" />Volver</Link>
            </Button>
            <Button variant="ghost" size="sm" onClick={remove}>
              <Trash2 className="mr-2 h-4 w-4 text-destructive" />
              Eliminar
            </Button>
          </div>
        }
      />

      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}

      <div className="space-y-6">
        <DynamicConnectorForm value={form} onChange={setForm} onSubmit={save} loading={saving} submitLabel="Guardar cambios" />
        <EndpointBuilder endpoints={form.endpoints || []} onChange={(eps) => setForm({ ...form, endpoints: eps })} />
        <TestConnectionPanel onTest={test} loading={testing} message={testMsg} preview={preview} />

        {detail.recent_test_logs?.length > 0 && (
          <Card>
            <CardHeader><CardTitle className="text-base">Logs de prueba</CardTitle></CardHeader>
            <CardContent>
              <div className="space-y-2 text-sm">
                {detail.recent_test_logs.map((log) => (
                  <div key={String(log.id)} className="rounded border px-3 py-2">
                    <span className={log.ok ? "text-success" : "text-destructive"}>
                      {log.ok ? "OK" : "Error"}
                    </span>
                    {" — "}
                    {String(log.request_summary || "")}
                    <span className="ml-2 text-xs text-muted-foreground">
                      {log.created_at ? new Date(String(log.created_at)).toLocaleString("es-DO") : ""}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
