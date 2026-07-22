"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowRight, RefreshCw } from "lucide-react";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { ConnectionStatusBadge } from "@/components/settings/connection-status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import type { IntegrationStatus } from "@/lib/settings";

type DiagnosticRow = {
  slug: string;
  name: string;
  configured: boolean;
  connected: boolean;
  status: string;
  last_test_at?: string | null;
  last_test_ok?: boolean | null;
  latency_ms?: number | null;
  last_error?: string | null;
  model?: string | null;
  config_url?: string | null;
};

export default function IntegracionesDiagnosticoPage() {
  const [items, setItems] = useState<DiagnosticRow[]>([]);
  const [env, setEnv] = useState("development");
  const [loading, setLoading] = useState(true);
  const [testingAll, setTestingAll] = useState(false);
  const [testSummary, setTestSummary] = useState<{ passed: number; failed: number; total: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.getIntegrationsDiagnostic();
      setItems(res.items);
      setEnv(res.environment);
      setError(null);
    } catch {
      setError("No se pudo cargar el diagnóstico. Verifique permisos de administrador.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const testAll = async () => {
    setTestingAll(true);
    setTestSummary(null);
    try {
      const res = await apiClient.testAllIntegrations();
      setTestSummary({ passed: res.passed, failed: res.failed, total: res.total });
      await load();
    } catch {
      setError("Error al ejecutar pruebas masivas.");
    } finally {
      setTestingAll(false);
    }
  };

  return (
    <div>
      <AdminPageHeader
        title="Diagnóstico de Integraciones"
        description="Estado real de configuración, conectividad y últimas pruebas"
        action={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" asChild>
              <Link href="/configuracion/integraciones">← Integraciones</Link>
            </Button>
            <Button size="sm" onClick={() => void testAll()} disabled={testingAll}>
              <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${testingAll ? "animate-spin" : ""}`} />
              {testingAll ? "Probando…" : "Probar todas"}
            </Button>
          </div>
        }
      />

      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}
      <p className="mb-4 text-sm text-muted-foreground">
        Ambiente: <strong className="capitalize">{env}</strong>
        {testSummary && (
          <span className="ml-3">
            Última ejecución: {testSummary.passed}/{testSummary.total} OK
            {testSummary.failed > 0 && (
              <span className="text-destructive"> — {testSummary.failed} fallaron</span>
            )}
          </span>
        )}
      </p>

      {loading ? (
        <p className="text-sm text-muted-foreground">Cargando diagnóstico…</p>
      ) : (
        <Card>
          <CardContent className="overflow-x-auto p-0">
            <table className="w-full min-w-[720px] text-sm">
              <thead>
                <tr className="border-b bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="px-4 py-3 font-medium">Integración</th>
                  <th className="px-4 py-3 font-medium">Configurado</th>
                  <th className="px-4 py-3 font-medium">Conectado</th>
                  <th className="px-4 py-3 font-medium">Última prueba</th>
                  <th className="px-4 py-3 font-medium">Modelo</th>
                  <th className="px-4 py-3 font-medium">Último error</th>
                  <th className="px-4 py-3 font-medium">Acción</th>
                </tr>
              </thead>
              <tbody>
                {items.map((row) => (
                  <tr key={row.slug} className="border-b last:border-0">
                    <td className="px-4 py-3 font-medium">
                      <div className="flex items-center gap-2">
                        {row.name}
                        <ConnectionStatusBadge
                          status={(row.status ?? "not_configured") as IntegrationStatus}
                          connected={row.connected}
                          configured={row.configured}
                        />
                      </div>
                    </td>
                    <td className="px-4 py-3">{row.configured ? "Sí" : "No"}</td>
                    <td className="px-4 py-3">{row.connected ? "Sí" : "No"}</td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {row.last_test_at
                        ? new Date(row.last_test_at).toLocaleString("es-DO")
                        : "—"}
                      {row.last_test_ok === false && (
                        <span className="ml-1 text-destructive">✗</span>
                      )}
                      {row.last_test_ok === true && (
                        <span className="ml-1 text-emerald-600">✓</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{row.model || "—"}</td>
                    <td className="max-w-[200px] truncate px-4 py-3 text-destructive" title={row.last_error ?? undefined}>
                      {row.last_error || "—"}
                    </td>
                    <td className="px-4 py-3">
                      <Button variant="ghost" size="sm" asChild>
                        <Link href={row.config_url || `/configuracion/integraciones/${row.slug}`}>
                          Configurar <ArrowRight className="ml-1 h-3 w-3" />
                        </Link>
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
