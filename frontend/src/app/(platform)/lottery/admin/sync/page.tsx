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

/** Admin sync — worker standalone + backup gate status. */
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

  const gate = (obs?.backup_gate || {}) as Record<string, unknown>;

  return (
    <AppShell
      title="Sincronización"
      description="Worker standalone, backup gate persistente y escritura controlada"
    >
      <div className="mb-3 flex gap-2 text-sm">
        <Link href="/lottery" className="text-primary underline">
          Resumen
        </Link>
        <Link href="/lottery/admin/scheduler" className="text-primary underline">
          Scheduler y fuentes
        </Link>
        <Link href="/lottery/admin/lotteries" className="text-primary underline">
          Loterías
        </Link>
        <Link href="/lottery/admin/ai" className="text-primary underline">
          Centro de IA
        </Link>
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
      {obs && (
        <Card className="mb-4">
          <CardHeader>
            <CardTitle className="text-base">Estado operativo</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2 text-sm md:grid-cols-2">
            <p>Sync enabled: {String(obs.sync_enabled)}</p>
            <p>Write enabled: {String(obs.sync_write_enabled)}</p>
            <p>Automatic write: {String(obs.automatic_write_enabled)}</p>
            <p>Scheduler mode: {String(obs.scheduler_mode)}</p>
            <p>Worker standalone: {String(obs.worker_standalone)}</p>
            <p>Scraping: {String(obs.scraping_enabled)} (debe ser false)</p>
            <p>Sorteos: {String(obs.draws_count)}</p>
            <p>Última fecha: {String(obs.last_draw_date || "—")}</p>
            <p>Último write: {String(obs.last_write_sync || "—")}</p>
          </CardContent>
        </Card>
      )}
      {obs && (
        <Card className="mb-4">
          <CardHeader>
            <CardTitle className="text-base">Backup gate</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2 text-sm md:grid-cols-2">
            <p>Estado: {gate.ok ? "válido" : String(gate.alert || "inválido")}</p>
            <p>Ruta: {String(gate.path || "—")}</p>
            <p>Creado: {String(gate.created_at || "—")}</p>
            <p>
              Edad: {gate.age_hours != null ? `${Number(gate.age_hours).toFixed(2)}h` : "—"} / máx{" "}
              {String(gate.max_age_hours ?? "—")}h
            </p>
            <p>Expira: {String(gate.expires_at || "—")}</p>
            <p>Próximo refresh: {String(gate.next_refresh_at || "—")}</p>
            <p>Checksum: {String(gate.checksum_sha256_12 || "—")}</p>
            <p>Última validación: {String(gate.last_validated_at || "—")}</p>
            <p>Base: {String(gate.database_name || "—")} (esperada {String(gate.expected_database || "—")})</p>
            <p>Auto-refresh: {String(gate.auto_refresh)} · retención {String(gate.retention_keep)}</p>
            <p className="md:col-span-2 text-xs text-muted-foreground">
              Directorio persistente: /var/jaios/backups/lottery-sync-gates/ — el worker crea y rota dumps
              automáticamente; no depende de renovar /tmp manualmente.
            </p>
          </CardContent>
        </Card>
      )}
      <Card className="mb-4">
        <CardHeader>
          <CardTitle className="text-base">Acciones</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-xs text-muted-foreground">
            La escritura productiva la ejecuta el worker (`guarded_write`) con backup gate validado.
            Dry-run fixture es solo diagnóstico.
          </p>
          <Button onClick={() => void dryRun()}>Ejecutar dry-run fixture</Button>
          {msg && <p className="text-sm text-muted-foreground">{msg}</p>}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Runs recientes</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {runs.length === 0 ? (
            <p className="text-muted-foreground">Sin runs.</p>
          ) : (
            runs.slice(0, 12).map((r) => {
              const row = r as Record<string, unknown>;
              return (
                <div key={String(row.id)} className="rounded-lg border border-border/60 p-2 font-mono text-xs">
                  {String(row.started_at)} · {String(row.status)} · dry={String(row.dry_run)} · ins=
                  {String(row.records_inserted)} · new={String(row.records_new)}
                </div>
              );
            })
          )}
        </CardContent>
      </Card>
    </AppShell>
  );
}
