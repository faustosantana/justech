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

/** Admin scheduler staging — Lottery Client blocked. */
export default function LotteryAdminSchedulerPage() {
  const router = useRouter();
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [alerts, setAlerts] = useState<unknown[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmText, setConfirmText] = useState("");

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
      const [s, a] = await Promise.all([
        apiClient.getLotteryAdminScheduler(),
        apiClient.getLotteryAdminSchedulerAlerts(),
      ]);
      setStatus(s);
      setAlerts(a.items || []);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar scheduler");
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  const runNow = async () => {
    setMsg(null);
    try {
      const res = await apiClient.postLotteryAdminSchedulerRunNow("fixture");
      setMsg(`Tick: ${JSON.stringify(res)}`);
      await load();
    } catch (err) {
      setMsg(err instanceof ApiError ? err.message : "run-now falló");
    }
  };

  const enableObserve = async () => {
    try {
      await apiClient.postLotteryAdminSchedulerEnable("observe");
      setMsg("Modo observe solicitado (requiere LOTTERY_SCHEDULER_ENABLED en runtime)");
      await load();
    } catch (err) {
      setMsg(err instanceof ApiError ? err.message : "enable falló");
    }
  };

  const disable = async () => {
    try {
      await apiClient.postLotteryAdminSchedulerDisable();
      setMsg("Scheduler disabled");
      await load();
    } catch (err) {
      setMsg(err instanceof ApiError ? err.message : "disable falló");
    }
  };

  const requestGuarded = async () => {
    try {
      await apiClient.postLotteryAdminSchedulerSetMode(
        "guarded_write",
        confirmText,
      );
      setMsg("guarded_write solicitado — verifique flags y backup");
      await load();
    } catch (err) {
      setMsg(err instanceof ApiError ? err.message : "set-mode falló");
    }
  };

  return (
    <AppShell title="Admin scheduler (staging)" description="Automatización controlada — sin Producción">
      <div className="mb-3 flex gap-2 text-sm">
        <Link href="/lottery" className="text-primary underline">
          Inicio
        </Link>
        <Link href="/lottery/admin/sync" className="text-primary underline">
          Sync
        </Link>
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
      {status && (
        <Card className="mb-4">
          <CardHeader>
            <CardTitle className="text-base">Estado</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2 text-sm md:grid-cols-2">
            <p>DB: {String(status.allowed_database)}:{String(status.allowed_port)}</p>
            <p>Enabled: {String(status.enabled)}</p>
            <p>Mode: {String(status.mode)}</p>
            <p>Circuit: {String(status.circuit_state)}</p>
            <p>Write: {String(status.sync_write_enabled)}</p>
            <p>Auto write: {String(status.automatic_write_enabled)}</p>
            <p>Interval: {String(status.interval_minutes)} min</p>
            <p>Next: {String(status.next_run_at || "—")}</p>
            <p>Last tick: {String(status.last_tick_at || "—")}</p>
            <p>Max draw: {String(status.max_draw_date || "—")}</p>
            <p>Worker: {String(status.worker_running)}</p>
            <p>TZ: {String(status.timezone)}</p>
          </CardContent>
        </Card>
      )}
      <Card className="mb-4">
        <CardHeader>
          <CardTitle className="text-base">Acciones</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => void runNow()}>Run dry-run now (fixture)</Button>
            <Button variant="secondary" onClick={() => void enableObserve()}>
              Enable observe
            </Button>
            <Button variant="secondary" onClick={() => void disable()}>
              Disable scheduler
            </Button>
            <Button
              variant="secondary"
              onClick={() => void apiClient.postLotteryAdminCircuitReset().then(load)}
            >
              Reset circuit
            </Button>
          </div>
          <label className="block text-xs text-muted-foreground">
            Confirmación guarded_write (escriba exactamente):
            <br />
            ENABLE GUARDED WRITE ON jaios_lottery_staging
            <input
              className="mt-1 w-full rounded border px-2 py-1 text-sm"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              autoComplete="off"
            />
          </label>
          <Button onClick={() => void requestGuarded()}>Request guarded_write</Button>
          {msg && <p className="text-sm text-muted-foreground break-all">{msg}</p>}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Alertas abiertas</CardTitle>
        </CardHeader>
        <CardContent>
          <pre tabIndex={0} className="max-h-80 overflow-auto rounded-md bg-muted p-3 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring">
            {JSON.stringify(alerts, null, 2)}
          </pre>
        </CardContent>
      </Card>
    </AppShell>
  );
}
