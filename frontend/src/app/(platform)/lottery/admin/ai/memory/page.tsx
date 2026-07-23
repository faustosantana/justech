"use client";

import { useCallback, useEffect, useState } from "react";

import { useLotteryAIDevMode } from "@/components/lottery/ai-admin-dev-mode";
import { MetricLine } from "@/components/lottery/ai-admin-display";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiClient } from "@/lib/api";

type SessionRow = Record<string, unknown>;

export default function LotteryAIMemoryPage() {
  const { developerMode } = useLotteryAIDevMode();
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [q, setQ] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [sessionData, setSessionData] = useState<Record<string, unknown> | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [st, sess] = await Promise.all([
        apiClient.getLotteryAIMemory(),
        apiClient.getLotteryAISessions({ limit: 50, q: q || undefined }),
      ]);
      setStats(st);
      setSessions((sess.items ?? []) as SessionRow[]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar memoria");
    } finally {
      setLoading(false);
    }
  }, [q]);

  useEffect(() => {
    void load();
  }, [load]);

  const openSession = async (id: string) => {
    setBusy(true);
    setSelectedId(id);
    setSessionData(null);
    try {
      setSessionData(await apiClient.getLotteryAIMemorySession(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sesión no encontrada");
    } finally {
      setBusy(false);
    }
  };

  const clearSession = async (id: string) => {
    if (!window.confirm("¿Limpiar memoria de esta sesión?")) return;
    setBusy(true);
    try {
      await apiClient.postLotteryAIMemorySessionClear(id);
      setMsg("Sesión limpiada");
      setSessionData(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al limpiar");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
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
          <CardContent className="grid gap-2 sm:grid-cols-3">
            <MetricLine label="Backend" value={stats.memory_backend ?? stats.backend} />
            <MetricLine label="Sesiones" value={stats.sessions_total ?? stats.active_sessions} />
            <MetricLine label="Mensajes" value={stats.total_messages} />
            <MetricLine
              label="TTL"
              value={
                stats.default_ttl_seconds != null
                  ? `${Math.round(Number(stats.default_ttl_seconds) / 3600)} h`
                  : null
              }
            />
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Conversaciones recientes</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <Input
              placeholder="Buscar por usuario, correo, título…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="max-w-md"
            />
            <Button size="sm" variant="outline" onClick={() => void load()}>
              Buscar
            </Button>
          </div>
          <div className="overflow-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs text-muted-foreground">
                <tr>
                  <th className="py-1 pr-2">Usuario</th>
                  <th className="py-1 pr-2">Última actividad</th>
                  <th className="py-1 pr-2">Turnos</th>
                  <th className="py-1 pr-2">Loterías</th>
                  <th className="py-1 pr-2">Número</th>
                  <th className="py-1 pr-2">Contexto</th>
                  <th className="py-1">Acción</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((s) => (
                  <tr key={String(s.id)} className="border-t border-border/40">
                    <td className="py-1.5 pr-2">
                      {String(s.user_name ?? s.user_email ?? "Usuario")}
                      {developerMode ? (
                        <div className="font-mono text-[10px] text-muted-foreground">{String(s.id)}</div>
                      ) : null}
                    </td>
                    <td className="py-1.5 pr-2 text-xs">{String(s.updated_at ?? "Sin datos suficientes")}</td>
                    <td className="py-1.5 pr-2">{String(s.turns ?? 0)}</td>
                    <td className="py-1.5 pr-2 text-xs">
                      {Array.isArray(s.active_lotteries) && s.active_lotteries.length
                        ? (s.active_lotteries as string[]).join(", ")
                        : "Sin datos suficientes"}
                    </td>
                    <td className="py-1.5 pr-2 text-xs">
                      {Array.isArray(s.active_numbers) && s.active_numbers.length
                        ? (s.active_numbers as string[]).join(", ")
                        : "Sin datos suficientes"}
                    </td>
                    <td className="py-1.5 pr-2">{s.context_reused ? "reutilizado" : "nuevo"}</td>
                    <td className="py-1.5">
                      <Button size="sm" variant="outline" disabled={busy} onClick={() => void openSession(String(s.id))}>
                        Abrir
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {sessions.length === 0 && !loading && (
              <p className="py-3 text-sm text-muted-foreground">Sin sesiones para este filtro.</p>
            )}
          </div>
        </CardContent>
      </Card>

      {sessionData && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between text-sm">
              <span>Detalle de sesión</span>
              <Button size="sm" variant="ghost" disabled={busy || !selectedId} onClick={() => selectedId && void clearSession(selectedId)}>
                Limpiar memoria
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <MetricLine label="Título" value={sessionData.title} />
            <MetricLine
              label="Loterías activas"
              value={Array.isArray(sessionData.active_lotteries) ? (sessionData.active_lotteries as string[]).join(", ") : null}
            />
            <MetricLine
              label="Números activos"
              value={Array.isArray(sessionData.active_numbers) ? (sessionData.active_numbers as string[]).join(", ") : null}
            />
            <div>
              <p className="mb-1 text-xs font-medium text-muted-foreground">Línea de tiempo</p>
              <ul className="max-h-64 space-y-1 overflow-auto text-xs">
                {((sessionData.timeline ?? []) as Record<string, unknown>[]).map((t, i) => (
                  <li key={i} className="rounded border border-border/40 px-2 py-1">
                    <span className="font-medium">{String(t.role)}</span>: {String(t.content_preview ?? "")}
                  </li>
                ))}
              </ul>
            </div>
            {developerMode && (
              <pre className="overflow-auto rounded bg-muted/30 p-2 text-[10px]">
                {JSON.stringify(sessionData.conversation_v4 ?? {}, null, 2)}
              </pre>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
