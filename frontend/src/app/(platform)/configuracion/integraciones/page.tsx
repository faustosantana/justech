"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, ArrowRight } from "lucide-react";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { IntegrationCard } from "@/components/settings/integration-card";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api";
import type { ConnectorSummary } from "@/lib/connectors";

const PRIMARY = new Set([
  "hermes",
  "openai",
  "anthropic",
  "deepseek",
  "qdrant",
  "odoo",
  "dgcp",
  "whatsapp_cloud",
  "whatsapp_web",
  "n8n",
  "smtp",
  "microsoft365",
  "outlook",
  "teams",
  "onedrive",
  "sharepoint",
]);

const SECTIONS: { title: string; slugs: string[] }[] = [
  {
    title: "IA / Modelos",
    slugs: ["hermes", "openai", "anthropic", "deepseek", "qdrant"],
  },
  {
    title: "ERP / Datos",
    slugs: ["odoo", "dgcp"],
  },
  {
    title: "Automatización / Correo",
    slugs: ["outlook", "teams", "onedrive", "sharepoint", "smtp", "n8n"],
  },
  {
    title: "Comunicación",
    slugs: ["whatsapp_cloud", "whatsapp_web"],
  },
];

type TestFeedback = {
  ok: boolean;
  message: string;
  missing_config?: string[];
  latency_ms?: number;
};

export default function IntegracionesPage() {
  const [items, setItems] = useState<ConnectorSummary[]>([]);
  const [env, setEnv] = useState("development");
  const [testing, setTesting] = useState<string | null>(null);
  const [testFeedback, setTestFeedback] = useState<Record<string, TestFeedback>>({});
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await apiClient.getAdminIntegrations();
      setItems(res.builtin_items.filter((i) => PRIMARY.has(i.slug)));
      setEnv(res.environment);
      setError(null);
    } catch {
      setError("No tiene permisos de administrador.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const bySlug = useMemo(() => Object.fromEntries(items.map((i) => [i.slug, i])), [items]);

  const test = async (id: string) => {
    setTesting(id);
    setTestFeedback((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
    try {
      const res = await apiClient.testAdminIntegration(id);
      const feedback: TestFeedback = {
        ok: res.ok,
        message: res.message,
        missing_config: res.missing_config,
        latency_ms: res.latency_ms != null ? Number(res.latency_ms) : undefined,
      };
      setTestFeedback((prev) => ({ ...prev, [id]: feedback }));
      await load();
    } catch (e) {
      setTestFeedback((prev) => ({
        ...prev,
        [id]: {
          ok: false,
          message: e instanceof Error ? e.message : "Error al probar integración",
        },
      }));
    } finally {
      setTesting(null);
    }
  };

  const configureHref = (item: ConnectorSummary) =>
    item.config_url || `/configuracion/integraciones/${item.slug}`;

  return (
    <div>
      <AdminPageHeader
        title="Integraciones"
        description="Configure, pruebe y monitoree conexiones reales — sin estados falsos"
        action={
          <Button variant="outline" size="sm" asChild>
            <Link href="/configuracion/integraciones/diagnostico">
              <Activity className="mr-1.5 h-3.5 w-3.5" />
              Diagnóstico
            </Link>
          </Button>
        }
      />
      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}
      <p className="mb-6 text-sm text-muted-foreground">
        Ambiente: <strong className="capitalize">{env}</strong>
      </p>

      {SECTIONS.map((section) => {
        const sectionItems = section.slugs
          .map((slug) => bySlug[slug])
          .filter(Boolean) as ConnectorSummary[];
        if (sectionItems.length === 0) return null;
        return (
          <section key={section.title} className="mb-10">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              {section.title}
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {sectionItems.map((item) => (
                <IntegrationCard
                  key={item.id}
                  item={{
                    provider: item.slug,
                    label: item.name,
                    category: item.connector_type,
                    connected: item.connected,
                    credentials_configured: item.status !== "not_configured",
                    status: item.status as import("@/lib/settings").IntegrationStatus,
                    read_only: item.read_only,
                    last_test_at: item.last_test_at,
                    last_test_ok: item.last_test_ok,
                    last_test_message: item.last_test_message,
                    environment: item.environment,
                    source: item.is_builtin ? "builtin" : "dynamic",
                    recent_logs: [],
                    model: item.model,
                  }}
                  configureHref={configureHref(item)}
                  onTest={() => test(item.slug)}
                  onDisconnect={() => apiClient.disconnectAdminIntegration(item.slug).then(load)}
                  testing={testing === item.slug}
                  testFeedback={testFeedback[item.slug]}
                  documentation={item.documentation}
                />
              ))}
            </div>
          </section>
        );
      })}

      <section className="mb-6">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Proveedores comerciales
        </h2>
        <p className="mb-3 text-sm text-muted-foreground">
          Ingram, Omega, Intcomex, Cecomsa, Tecnosinergia, Tecnomarket — credenciales y pruebas por proveedor.
        </p>
        <Button variant="outline" size="sm" asChild>
          <Link href="/configuracion/integraciones/proveedores">
            Ver proveedores <ArrowRight className="ml-1 h-3.5 w-3.5" />
          </Link>
        </Button>
      </section>
    </div>
  );
}
