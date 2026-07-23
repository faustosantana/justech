"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiClient } from "@/lib/api";

export default function LotteryAIMemoryPage() {
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [sessionId, setSessionId] = useState("");
  const [sessionData, setSessionData] = useState<Record<string, unknown> | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setStats(await apiClient.getLotteryAIMemory());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar estadísticas de memoria");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const inspectSession = async () => {
    const id = sessionId.trim();
    if (!id) return;
    setBusy(true);
    setSessionData(null);
    setMsg(null);
    try {
      setSessionData(await apiClient.getLotteryAIMemorySession(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sesión no encontrada");
    } finally {
      setBusy(false);
    }
  };

  const clearSession = async () => {
    const id = sessionId.trim();
    if (!id) return;
    if (!window.confirm(`¿Limpiar memoria de la sesión ${id}?`)) return;
    setBusy(true);
    setMsg(null);
    try {
      await apiClient.postLotteryAIMemorySessionClear(id);
      setMsg(`Sesión ${id} limpiada`);
      setSessionData(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al limpiar sesión");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Memoria</h2>
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          Actualizar
        </Button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {msg && <p className="text-sm text-muted-foreground">{msg}</p>}

      {stats && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Estadísticas</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2 text-sm sm:grid-cols-2 md:grid-cols-3">
            <p>Backend: {String(stats.backend ?? stats.memory_backend ?? "—")}</p>
            <p>Sesiones activas: {String(stats.active_sessions ?? stats.sessions_count ?? "—")}</p>
            <p>Total mensajes: {String(stats.total_messages ?? "—")}</p>
            <p>Tamaño: {String(stats.size_bytes ?? stats.memory_size ?? "—")}</p>
            <p>TTL por defecto: {String(stats.default_ttl_seconds ?? "—")} s</p>
            <p>Última limpieza: {String(stats.last_cleanup_at ?? "—")}</p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Inspeccionar sesión</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <Input
              placeholder="UUID de sesión"
              value={sessionId}
              onChange={(e) => setSessionId(e.target.value)}
              className="max-w-xs font-mono text-sm"
            />
            <Button
              size="sm"
              variant="outline"
              onClick={() => void inspectSession()}
              disabled={busy || !sessionId.trim()}
            >
              Inspeccionar
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => void clearSession()}
              disabled={busy || !sessionId.trim()}
            >
              Limpiar
            </Button>
          </div>

          {sessionData && (
            <div className="rounded-lg border border-border/60 p-3">
              <p className="mb-2 text-xs font-medium text-muted-foreground">
                Sesión: {String(sessionData.id ?? sessionId)}
              </p>
              <pre className="overflow-auto text-xs">
                {JSON.stringify(sessionData, null, 2)}
              </pre>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
