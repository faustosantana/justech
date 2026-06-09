"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { CommandCenterView } from "@/components/command-center/command-center-view";
import { DashboardSkeleton } from "@/components/dashboard/dashboard-skeleton";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { useAssistantContext } from "@/lib/assistant-context";
import { apiClient } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import type { ExecutiveDashboard } from "@/lib/dashboard";

export default function DashboardPage() {
  const router = useRouter();
  const { openCopilot } = useAssistantContext();
  const [data, setData] = useState<ExecutiveDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [briefingShown, setBriefingShown] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    apiClient
      .getExecutiveDashboard()
      .then(setData)
      .catch((err) => {
        const msg = err instanceof Error ? err.message : "Error desconocido";
        setError(`No se pudo cargar el Command Center. ${msg}`);
        setData(null);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!getAccessToken()) {
      router.replace("/login");
      return;
    }
    load();
  }, [router, load]);

  useEffect(() => {
    if (!data?.proactive_message || briefingShown) return;
    const timer = window.setTimeout(() => {
      openCopilot(data.proactive_message);
      setBriefingShown(true);
    }, 800);
    return () => window.clearTimeout(timer);
  }, [data, briefingShown, openCopilot]);

  return (
    <AppShell hideHeaderTitle>
      {loading && <DashboardSkeleton />}
      {!loading && error && (
        <div className="brand-surface mx-auto max-w-lg p-8 text-center">
          <p className="text-destructive">{error}</p>
          <Button className="mt-4" onClick={load}>
            Reintentar
          </Button>
        </div>
      )}
      {!loading && !error && !data && (
        <div className="brand-surface mx-auto max-w-lg p-8 text-center">
          <p className="text-muted-foreground">No hay datos del Command Center.</p>
          <Button className="mt-4" onClick={load}>
            Actualizar
          </Button>
        </div>
      )}
      {!loading && data && <CommandCenterView data={data} onOpenCopilot={openCopilot} />}
    </AppShell>
  );
}
