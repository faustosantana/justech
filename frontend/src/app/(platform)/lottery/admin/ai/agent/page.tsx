"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

export default function LotteryAIAgentPage() {
  const [config, setConfig] = useState<Record<string, unknown> | null>(null);
  const [draft, setDraft] = useState("");
  const [parseError, setParseError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setMsg(null);
    try {
      const data = await apiClient.getLotteryAIAgent();
      setConfig(data);
      setDraft(JSON.stringify(data, null, 2));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar config del agente");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const validateDraft = (): Record<string, unknown> | null => {
    try {
      const parsed = JSON.parse(draft) as Record<string, unknown>;
      setParseError(null);
      return parsed;
    } catch {
      setParseError("JSON inválido");
      return null;
    }
  };

  const saveDraft = async () => {
    const parsed = validateDraft();
    if (!parsed) return;
    setBusy(true);
    setMsg(null);
    try {
      const updated = await apiClient.putLotteryAIAgent(parsed);
      setConfig(updated);
      setDraft(JSON.stringify(updated, null, 2));
      setMsg("Borrador guardado");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al guardar");
    } finally {
      setBusy(false);
    }
  };

  const publish = async () => {
    if (!window.confirm("¿Publicar configuración del agente en producción?")) return;
    setBusy(true);
    setMsg(null);
    try {
      await apiClient.postLotteryAIAgentPublish();
      setMsg("Configuración publicada");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al publicar");
    } finally {
      setBusy(false);
    }
  };

  const revert = async () => {
    if (!window.confirm("¿Revertir al último estado publicado?")) return;
    setBusy(true);
    setMsg(null);
    try {
      const data = await apiClient.postLotteryAIAgentRevert();
      setConfig(data);
      setDraft(JSON.stringify(data, null, 2));
      setMsg("Configuración revertida");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al revertir");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Agente</h2>
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading || busy}>
          Actualizar
        </Button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {msg && <p className="text-sm text-muted-foreground">{msg}</p>}
      {loading && <p className="text-sm text-muted-foreground">Cargando…</p>}

      {config && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Resumen de configuración</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-1.5 text-sm sm:grid-cols-2">
              <p>Nombre: {String(config.name ?? config.agent_name ?? "—")}</p>
              <p>Versión: {String(config.version ?? "—")}</p>
              <p>Estado: {String(config.status ?? config.state ?? "—")}</p>
              <p>Proveedor: {String(config.provider ?? "—")}</p>
              <p>Modelo: {String(config.model ?? "—")}</p>
              <p>Temperatura: {String(config.temperature ?? "—")}</p>
              <p>Max tokens: {String(config.max_tokens ?? "—")}</p>
              <p>Tools activas: {String(config.tools_count ?? config.tools?.length ?? "—")}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Editor JSON</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <textarea
                className="min-h-64 w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-xs"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                spellCheck={false}
              />
              {parseError && <p className="text-xs text-destructive">{parseError}</p>}
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="outline" onClick={() => void saveDraft()} disabled={busy}>
                  Guardar borrador
                </Button>
                <Button size="sm" onClick={() => void publish()} disabled={busy}>
                  Publicar
                </Button>
                <Button size="sm" variant="ghost" onClick={() => void revert()} disabled={busy}>
                  Revertir
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
