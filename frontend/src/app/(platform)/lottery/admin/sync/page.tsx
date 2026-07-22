"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";
import { getAccessToken, getUserRole } from "@/lib/auth";
import { isLotteryClientRole } from "@/lib/lottery";

/** Admin sync staging — no visible para lottery_client. */
export default function LotteryAdminSyncPage() {
  const router = useRouter();
  const [obs, setObs] = useState<Record<string, unknown> | null>(null);
  const [runs, setRuns] = useState<unknown[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!getAccessToken()) {
      router.replace("/login?session=expired");
      return;
    }
    if (isLotteryClientRole(getUserRole())) {
      setError("Acceso denegado");
      router.replace("/lottery");
      return;
    }
    try {
      const [o, r] = await Promise.all([
        apiClient.getLotteryObservability(),
        apiClient.getLotteryAdminSyncRuns(),
      ]);
      setObs(o);
      setRuns(r.items || []);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar sync admin");
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  const dryRun = async () => {
    setMsg(null);
    try {
      const res = await apiClient.postLotteryAdminSyncDryRun({
        source: "fixture",
        limit: 5,
      });
      setMsg(`Dry-run OK: ${JSON.stringify(res.classifications)}`);
      await load();
    } catch (err) {
      setMsg(err instanceof ApiError ? err.message : "Dry-run falló");
    }
  };

  return (
    <AppShell title="Admin sync (staging)" description="Escritura controlada — scheduler apagado">
      <div className="mb-3 flex gap-2 text-sm">
        <Link href="/lottery" className="text-primary underline">
          Inicio
        </Link>
        <Link href="/lottery/admin/scheduler" className="text-primary underline">
          Scheduler
        </Link>
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
      {obs && (
        <Card className="mb-4">
          <CardHeader>
            <CardTitle className="text-base">Estado</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2 text-sm md:grid-cols-2">
            <p>Sync enabled: {String(obs.sync_enabled)}</p>
            <p>Write enabled: {String(obs.sync_write_enabled)}</p>
            <p>Scheduler: {String(obs.scheduler_enabled)} (debe ser false)</p>
            <p>Scraping: {String(obs.scraping_enabled)} (debe ser false)</p>
            <p>Sorteos: {String(obs.draws_count)}</p>
            <p>Última fecha: {String(obs.last_draw_date || "—")}</p>
            <p>Último write: {String(obs.last_write_sync || "—")}</p>
          </CardContent>
        </Card>
      )}
      <Card className="mb-4">
        <CardHeader>
          <CardTitle className="text-base">Acciones</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-xs text-muted-foreground">
            La escritura real solo se ejecuta vía CLI con gates explícitos
            (--write --environment staging --confirm-database jaios_lottery_staging --yes).
          </p>
          <Button onClick={() => void dryRun()}>Ejecutar dry-run fixture</Button>
          {msg && <p className="text-sm text-muted-foreground">{msg}</p>}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Últimas ejecuciones</CardTitle>
        </CardHeader>
        <CardContent>
          <pre tabIndex={0} className="max-h-96 overflow-auto rounded-md bg-muted p-3 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring">
            {JSON.stringify(runs, null, 2)}
          </pre>
        </CardContent>
      </Card>
    </AppShell>
  );
}
