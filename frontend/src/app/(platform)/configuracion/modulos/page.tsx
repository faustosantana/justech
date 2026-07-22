"use client";

import { useCallback, useEffect, useState } from "react";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { Card, CardContent } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import type { TenantModule } from "@/lib/admin";

export default function AdminModulosPage() {
  const [modules, setModules] = useState<TenantModule[]>([]);
  const [canMutate, setCanMutate] = useState(false);

  const load = useCallback(async () => {
    const [access, res] = await Promise.all([
      apiClient.getAdminAccess(),
      apiClient.getAdminModules(),
    ]);
    setCanMutate(access.can_mutate);
    setModules(res.items);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const toggle = async (key: string, enabled: boolean) => {
    if (!canMutate) return;
    await apiClient.updateAdminModule(key, enabled);
    load();
  };

  return (
    <div>
      <AdminPageHeader title="Módulos" description="Activar o desactivar módulos del tenant" />
      <Card>
        <CardContent className="pt-6 space-y-3">
          {modules.map((m) => (
            <label key={m.module_key} className="flex items-center justify-between rounded-lg border p-3">
              <div>
                <p className="font-medium text-sm">{m.name}</p>
                <p className="text-xs text-muted-foreground">{m.module_key}{m.is_future ? " · futuro" : ""}</p>
              </div>
              <input
                type="checkbox"
                checked={m.is_enabled}
                disabled={!canMutate || m.is_future}
                onChange={(e) => toggle(m.module_key, e.target.checked)}
              />
            </label>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
