"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowRight, Truck } from "lucide-react";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { ConnectionStatusBadge } from "@/components/settings/connection-status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api";
import type { IntegrationStatus } from "@/lib/settings";

const SUPPLIER_IDS = [
  "ingram",
  "omega",
  "intcomex",
  "tecnomarket",
  "cecomsa",
  "tecnosinergia",
] as const;

const COMING_SOON = new Set(["intcomex", "tecnomarket", "tecnosinergia"]);

export default function IntegracionesProveedoresPage() {
  const [items, setItems] = useState<
    {
      provider: string;
      label: string;
      connected: boolean;
      credentials_configured: boolean;
      status?: IntegrationStatus;
      last_test_at?: string | null;
      last_test_message?: string | null;
    }[]
  >([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await apiClient.getAdminIntegrations();
      const suppliers = res.builtin_items.filter((i) =>
        SUPPLIER_IDS.includes(i.slug as (typeof SUPPLIER_IDS)[number]),
      );
      setItems(
        suppliers.map((i) => ({
          provider: i.slug,
          label: i.name,
          connected: i.connected,
          credentials_configured: i.status !== "not_configured",
          status: i.status as IntegrationStatus,
          last_test_at: i.last_test_at,
          last_test_message: i.last_test_message,
        })),
      );
      setError(null);
    } catch {
      setError("No tiene permisos de administrador para ver integraciones.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div>
      <AdminPageHeader
        title="Integraciones de Proveedores"
        description="Credenciales, autenticación, pruebas de conexión y habilitación de fuentes live para el buscador comercial"
      />

      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {SUPPLIER_IDS.map((id) => {
          const item = items.find((i) => i.provider === id);
          const comingSoon = COMING_SOON.has(id);
          const label = item?.label ?? id;
          return (
            <Card key={id} className={comingSoon ? "opacity-70" : "hover:shadow-md transition-shadow"}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Truck className="h-4 w-4" />
                    {label}
                  </CardTitle>
                  {!comingSoon && item && (
                    <ConnectionStatusBadge
                      status={(item.status ?? "not_configured") as IntegrationStatus}
                      connected={item.connected}
                      configured={item.credentials_configured}
                    />
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                {comingSoon ? (
                  <p className="text-muted-foreground">Próximamente — conector en desarrollo</p>
                ) : (
                  <>
                    <p className="text-muted-foreground">
                      {item?.last_test_message || (item?.credentials_configured ? "Credenciales configuradas" : "Sin configurar")}
                    </p>
                    {item?.last_test_at && (
                      <p className="text-xs text-muted-foreground">
                        Última prueba: {new Date(item.last_test_at).toLocaleString("es-DO")}
                      </p>
                    )}
                    <Button size="sm" variant="outline" asChild>
                      <Link href={`/configuracion/integraciones/proveedores/${id}`}>
                        Configurar <ArrowRight className="ml-1 h-3.5 w-3.5" />
                      </Link>
                    </Button>
                  </>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
