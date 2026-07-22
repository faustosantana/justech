"use client";

import { useCallback, useEffect, useState } from "react";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { SystemStatusGrid, type StatusGridItem } from "@/components/admin/system-status-grid";
import { apiClient } from "@/lib/api";

const CONFIG_URLS: Record<string, string> = {
  microsoft365: "/configuracion/integraciones/microsoft365",
  odoo: "/configuracion/integraciones/odoo",
  dgcp: "/configuracion/integraciones/dgcp",
  whatsapp: "/configuracion/integraciones/whatsapp",
};

export default function EstadoSistemaPage() {
  const [items, setItems] = useState<StatusGridItem[]>([]);
  const [env, setEnv] = useState("");
  const [testing, setTesting] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [statusRes, integrationsRes] = await Promise.all([
      apiClient.getSettingsSystemStatus(),
      apiClient.getAdminIntegrations(),
    ]);
    setEnv(statusRes.environment);

    const grid: StatusGridItem[] = statusRes.items.map((item) => {
      const nameKey = item.name.toLowerCase();
      const match = integrationsRes.items.find(
        (i) => i.name.toLowerCase().includes(nameKey) || nameKey.includes(i.slug),
      );
      const id = match?.id || nameKey.replace(/\s+/g, "-");
      const configUrl =
        match?.config_url ||
        CONFIG_URLS[match?.slug || ""] ||
        (match?.is_dynamic ? `/configuracion/apis/${match.id}` : undefined);

      return {
        id,
        name: item.name,
        status: item.status,
        message: item.message,
        config_url: configUrl,
        is_dynamic: match?.is_dynamic,
        onTest: match
          ? async () => {
              setTesting(id);
              try {
                await apiClient.testAdminIntegration(match.is_dynamic ? match.id : match.slug);
                await load();
              } finally {
                setTesting(null);
              }
            }
          : undefined,
        testing: testing === id,
      };
    });

    setItems(grid);
  }, [testing]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div>
      <AdminPageHeader
        title="Estado del sistema"
        description="Salud de servicios, integraciones y acciones rápidas"
      />
      <p className="mb-4 text-sm text-muted-foreground">Ambiente: <strong className="capitalize">{env}</strong></p>
      <SystemStatusGrid items={items} />
    </div>
  );
}
