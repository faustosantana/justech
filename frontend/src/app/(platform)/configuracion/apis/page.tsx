"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Plus, Plug } from "lucide-react";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { ConnectionStatusBadge } from "@/components/settings/connection-status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import type { ConnectorSummary } from "@/lib/connectors";
import type { IntegrationStatus } from "@/lib/settings";

export default function ApisConectoresPage() {
  const [dynamicItems, setDynamicItems] = useState<ConnectorSummary[]>([]);
  const [env, setEnv] = useState("development");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await apiClient.getAdminIntegrations();
      setDynamicItems(res.dynamic_items || []);
      setEnv(res.environment);
      setError(null);
    } catch {
      setError("No tiene permisos de administrador.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div>
      <AdminPageHeader
        title="APIs / Conectores"
        description="Cree y administre integraciones dinámicas sin tocar código — Ingram, Dell, Adobe, Huawei, ERPs y más."
        action={
          <Button asChild>
            <Link href="/configuracion/apis/nuevo">
              <Plus className="mr-2 h-4 w-4" />
              Nuevo conector
            </Link>
          </Button>
        }
      />

      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}
      <p className="mb-6 text-sm text-muted-foreground">
        Ambiente: <strong className="capitalize">{env}</strong>
      </p>

      {dynamicItems.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
            <Plug className="h-10 w-10 text-muted-foreground" />
            <div>
              <p className="font-medium">Sin conectores personalizados</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Cree su primer conector API en menos de un minuto.
              </p>
            </div>
            <Button asChild>
              <Link href="/configuracion/apis/nuevo">Crear conector</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {dynamicItems.map((item) => (
            <Card key={item.id} className="flex flex-col transition-shadow hover:shadow-md">
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="text-base">{item.name}</CardTitle>
                  <ConnectionStatusBadge status={item.status as IntegrationStatus} connected={item.connected} />
                </div>
                <p className="text-xs text-muted-foreground font-mono">{item.base_url || "Sin URL"}</p>
              </CardHeader>
              <CardContent className="mt-auto space-y-3 text-sm">
                <p className="text-muted-foreground">
                  {item.last_test_message || `${item.endpoint_count} endpoint(s)`}
                </p>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" asChild>
                    <Link href={`/configuracion/apis/${item.id}`}>Configurar</Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
