"use client";

import { useCallback, useEffect, useState } from "react";

import { ModuleDashboard } from "@/components/module/module-dashboard";
import { apiClient } from "@/lib/api";
import type { PlatformAccess } from "@/lib/admin";
import { useAssistantContext } from "@/lib/assistant-context";
import { loadModuleDashboard } from "@/lib/modules/dashboard-data";
import { MODULE_BY_ID, filterModuleDashboardData, filterModuleQuickActions } from "@/lib/modules/registry";

export function ModuleDashboardPage({ appId }: { appId: string }) {
  const module = MODULE_BY_ID[appId];
  const { openCopilot } = useAssistantContext();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<Awaited<ReturnType<typeof loadModuleDashboard>> | null>(null);
  const [, setAccess] = useState<PlatformAccess | null>(null);

  const load = useCallback(async () => {
    if (!module) return;
    setLoading(true);
    try {
      apiClient.getPlatformAccess().then(setAccess).catch(() => setAccess(null));
      const dashboard = filterModuleDashboardData(await loadModuleDashboard(module));
      setData(dashboard);
    } finally {
      setLoading(false);
    }
  }, [module]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!module) {
    return <p className="text-sm text-muted-foreground">Aplicación no encontrada.</p>;
  }

  return (
    <ModuleDashboard
      title={`Dashboard · ${module.label}`}
      subtitle={module.dashboardSubtitle}
      kpis={data?.kpis ?? []}
      actions={filterModuleQuickActions(module)}
      activity={data?.activity ?? []}
      alerts={data?.alerts}
      loading={loading}
      onCopilot={(prompt) => openCopilot(prompt)}
    />
  );
}
