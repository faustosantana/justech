"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

export default function LotteryAIPromptsPage() {
  const [prompts, setPrompts] = useState<unknown[]>([]);
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);
  const [body, setBody] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getLotteryAIPrompts();
      setPrompts(res.items ?? []);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar prompts");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const selectPrompt = async (id: string) => {
    setMsg(null);
    try {
      const p = await apiClient.getLotteryAIPrompt(id);
      setSelected(p);
      setBody(String(p.body ?? p.content ?? ""));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar prompt");
    }
  };

  const createDraft = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const p = await apiClient.postLotteryAIPrompt({ body: "", status: "draft" });
      setMsg(`Borrador creado: ${String(p.id ?? "")}`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al crear borrador");
    } finally {
      setBusy(false);
    }
  };

  const saveDraft = async () => {
    if (!selected) return;
    setBusy(true);
    setMsg(null);
    try {
      const updated = await apiClient.putLotteryAIPrompt(String(selected.id), { body });
      setSelected(updated);
      setMsg("Borrador guardado");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al guardar");
    } finally {
      setBusy(false);
    }
  };

  const publish = async () => {
    if (!selected) return;
    if (!window.confirm("¿Publicar este prompt? Se activará como prompt productivo.")) return;
    setBusy(true);
    setMsg(null);
    try {
      await apiClient.postLotteryAIPromptPublish(String(selected.id));
      setMsg("Prompt publicado");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al publicar");
    } finally {
      setBusy(false);
    }
  };

  const rollback = async () => {
    if (!selected) return;
    if (!window.confirm("¿Revertir este prompt?")) return;
    setBusy(true);
    setMsg(null);
    try {
      await apiClient.postLotteryAIPromptRollback(String(selected.id));
      setMsg("Prompt revertido");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al revertir");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Prompts</h2>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
            Actualizar
          </Button>
          <Button size="sm" onClick={() => void createDraft()} disabled={busy}>
            Nuevo borrador
          </Button>
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {msg && <p className="text-sm text-muted-foreground">{msg}</p>}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Versiones</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            {loading && <p className="text-sm text-muted-foreground">Cargando…</p>}
            {prompts.length === 0 && !loading && (
              <p className="text-sm text-muted-foreground">Sin versiones.</p>
            )}
            {prompts.map((p) => {
              const row = p as Record<string, unknown>;
              const isSelected = selected && String(selected.id) === String(row.id);
              return (
                <button
                  key={String(row.id)}
                  type="button"
                  onClick={() => void selectPrompt(String(row.id))}
                  className={`block w-full rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                    isSelected ? "border-primary bg-primary/5" : "border-border/60 hover:bg-muted"
                  }`}
                >
                  <span className="font-medium">v{String(row.version ?? row.id)}</span>{" "}
                  <span className="text-xs text-muted-foreground">
                    {String(row.status ?? "—")} · {String(row.created_at ?? "—")}
                  </span>
                </button>
              );
            })}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Editor</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {!selected ? (
              <p className="text-sm text-muted-foreground">Selecciona una versión para editar.</p>
            ) : (
              <>
                <p className="text-xs text-muted-foreground">
                  ID: {String(selected.id)} · Estado: {String(selected.status ?? "—")}
                </p>
                <textarea
                  className="min-h-48 w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-xs"
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  placeholder="Cuerpo del prompt…"
                  disabled={String(selected.status) !== "draft"}
                />
                {String(selected.status) !== "draft" && (
                  <p className="text-xs text-muted-foreground">
                    Solo se pueden editar borradores.
                  </p>
                )}
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => void saveDraft()}
                    disabled={busy || String(selected.status) !== "draft"}
                  >
                    Guardar borrador
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => void publish()}
                    disabled={busy}
                  >
                    Publicar
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => void rollback()}
                    disabled={busy}
                  >
                    Revertir
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
