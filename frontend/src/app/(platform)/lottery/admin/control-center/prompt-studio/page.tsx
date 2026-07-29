"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { HelpPanel } from "@/components/lottery/control-center/help-panel";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

type BlockMeta = {
  key: string;
  title: string;
  what_is: string;
  purpose: string;
  impact: string;
  do_write?: string;
  dont_write?: string;
  example?: string;
  validation?: { min_chars?: number; max_chars?: number; required?: boolean };
};

export default function PromptStudioBlocksPage() {
  const [blocksMeta, setBlocksMeta] = useState<BlockMeta[]>([]);
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);
  const [draftBlocks, setDraftBlocks] = useState<Record<string, string>>({});
  const [runtime, setRuntime] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const schema = await apiClient.getLotteryPromptStudioSchema();
      setBlocksMeta((schema.blocks || []) as BlockMeta[]);
      const [prompts, rt] = await Promise.all([
        apiClient.getLotteryAIPrompts(),
        apiClient.getLotteryPromptRuntimeStatus().catch(() => null),
      ]);
      setRuntime(rt);
      const items = ((prompts as { items?: Record<string, unknown>[] }).items || []) as Record<
        string,
        unknown
      >[];
      const reasoningDraft = items.find(
        (p) => p.name === "LOTTERY_ANALYST_REASONING_STUDIO" && p.status !== "active",
      );
      const active = items.find((p) => p.status === "active") || items[0] || null;
      const pick = reasoningDraft || active;
      if (pick?.id) {
        const full = await apiClient.getLotteryAIPrompt(String(pick.id));
        setSelected(full);
        setDraftBlocks((full.blocks || {}) as Record<string, string>);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar Prompt Studio");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const createDraft = async () => {
    setBusy(true);
    setMsg(null);
    setError(null);
    try {
      const created = await apiClient.postLotteryAIPrompt({
        from_active: true,
        display_name: `Borrador ${new Date().toISOString().slice(0, 16)}`,
        change_reason: "Creado desde Control Center",
      });
      setSelected(created);
      setDraftBlocks((created.blocks || {}) as Record<string, string>);
      setMsg("Borrador creado desde ACTIVO (la versión activa no cambia).");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear borrador");
    } finally {
      setBusy(false);
    }
  };

  const saveDraft = async () => {
    if (!selected?.id) return;
    setBusy(true);
    setMsg(null);
    setError(null);
    try {
      const updated = await apiClient.putLotteryAIPrompt(String(selected.id), {
        blocks: draftBlocks,
      });
      setSelected(updated);
      setMsg("Borrador guardado (no publicado ni activado).");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar (¿secretos?)");
    } finally {
      setBusy(false);
    }
  };

  const seedCandidate = async () => {
    setBusy(true);
    setMsg(null);
    setError(null);
    try {
      const res = await apiClient.postLotteryPromptRuntimeSeedCandidate();
      const prompt = (res.prompt || {}) as Record<string, unknown>;
      if (prompt.id) {
        setSelected(prompt);
        setDraftBlocks((prompt.blocks || {}) as Record<string, string>);
      }
      setRuntime(await apiClient.getLotteryPromptRuntimeStatus());
      setMsg(
        `Candidato 7.0.0-rc1 listo (draft). Hash: ${String((res.validation as Record<string, unknown>)?.compiled_prompt_hash || "").slice(0, 16)}…`,
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo sembrar candidato");
    } finally {
      setBusy(false);
    }
  };

  const publishImmutable = async () => {
    if (!selected?.id) return;
    setBusy(true);
    setMsg(null);
    setError(null);
    try {
      const res = await apiClient.postLotteryAIPromptPublishImmutable(String(selected.id));
      setSelected((res.prompt || res) as Record<string, unknown>);
      setRuntime(await apiClient.getLotteryPromptRuntimeStatus());
      setMsg("Publicado (inmutable). Runtime sigue en legacy hasta Activar en DEV + flags.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Publicación inmutable falló");
    } finally {
      setBusy(false);
    }
  };

  const activateDev = async () => {
    if (!selected?.id) return;
    setBusy(true);
    setMsg(null);
    setError(null);
    try {
      const res = await apiClient.postLotteryAIPromptActivateDev(String(selected.id), {
        reason: "activate_dev_prompt_studio",
      });
      setSelected((res.prompt || res) as Record<string, unknown>);
      setRuntime(await apiClient.getLotteryPromptRuntimeStatus());
      setMsg("Activado en catálogo DEV. Requiere LOTTERY_ANALYST_PROMPT_STUDIO_ENABLED=true + MODE=studio|shadow.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Activación DEV falló");
    } finally {
      setBusy(false);
    }
  };

  const rollback = async () => {
    if (!selected?.id) return;
    setBusy(true);
    setMsg(null);
    setError(null);
    try {
      const res = await apiClient.postLotteryAIPromptRollback(String(selected.id));
      setSelected(res);
      setRuntime(await apiClient.getLotteryPromptRuntimeStatus());
      setMsg("Rollback aplicado (caché invalidada).");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Rollback falló");
    } finally {
      setBusy(false);
    }
  };

  const statusOf = (key: string, meta: BlockMeta) => {
    const text = draftBlocks[key] || "";
    const min = meta.validation?.min_chars ?? 0;
    if (meta.validation?.required && text.trim().length < min) return "incompleto";
    if (text.trim()) return "completo";
    return meta.validation?.required ? "incompleto" : "opcional";
  };

  const activeRt = (runtime?.active || null) as Record<string, unknown> | null;
  const editable = ["draft", "validated", "approved"].includes(String(selected?.status || ""));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-xl font-semibold">Prompt Studio · Bloques</h1>
          <p className="text-sm text-muted-foreground">
            Guardar ≠ Publicar ≠ Activar. Runtime por defecto: Analyst Reasoning 2.1 (legacy).
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" disabled={busy} onClick={() => void seedCandidate()}>
            Sembrar 7.0.0-rc1
          </Button>
          <Button type="button" variant="outline" disabled={busy} onClick={() => void createDraft()}>
            Crear borrador desde activo
          </Button>
          <Button type="button" disabled={busy || !selected || !editable} onClick={() => void saveDraft()}>
            Guardar borrador
          </Button>
          <Button type="button" variant="outline" disabled={busy || !selected} onClick={() => void publishImmutable()}>
            Publicar
          </Button>
          <Button type="button" variant="outline" disabled={busy || !selected} onClick={() => void activateDev()}>
            Activar en DEV
          </Button>
          <Button type="button" variant="outline" disabled={busy || !selected} onClick={() => void rollback()}>
            Rollback
          </Button>
          <Link className="rounded border px-3 py-2 text-sm" href="/lottery/admin/control-center/prompt-studio/compilado">
            Ver compilado
          </Link>
        </div>
      </div>

      {runtime ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Runtime · Prompt Integration 1.0</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2 text-sm md:grid-cols-3">
            <div>
              <div className="text-muted-foreground">Mode</div>
              <div>{String(runtime.runtime_mode || "legacy")}</div>
            </div>
            <div>
              <div className="text-muted-foreground">Studio enabled</div>
              <div>{runtime.studio_enabled ? "true" : "false"}</div>
            </div>
            <div>
              <div className="text-muted-foreground">Activar Producción</div>
              <div>no disponible en esta fase</div>
            </div>
            <div>
              <div className="text-muted-foreground">Active Reasoning Studio</div>
              <div>
                {activeRt
                  ? `${String(activeRt.version)} · ${String(activeRt.checksum || "").slice(0, 12)}…`
                  : "ninguna"}
              </div>
            </div>
            <div>
              <div className="text-muted-foreground">Draft editando</div>
              <div>
                {selected
                  ? `${String(selected.version)} · ${String(selected.status)} · ${(String(selected.checksum || "")).slice(0, 12)}…`
                  : "—"}
              </div>
            </div>
            <div>
              <div className="text-muted-foreground">Forensics</div>
              <div>{runtime.forensic_trace_enabled ? "ON" : "OFF (default)"}</div>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {selected ? (
        <p className="text-xs text-muted-foreground">
          Editando: {String(selected.display_name || selected.name)} · {String(selected.version)} ·{" "}
          {String(selected.status_label || selected.status)}
        </p>
      ) : null}
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      {msg ? <p className="text-sm text-green-700">{msg}</p> : null}
      <div className="space-y-4">
        {blocksMeta.map((meta) => (
          <Card key={meta.key}>
            <CardHeader>
              <CardTitle className="flex items-center justify-between text-base">
                <span>{meta.title}</span>
                <span className="text-xs font-normal text-muted-foreground">{statusOf(meta.key, meta)}</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 md:grid-cols-2">
              <HelpPanel
                title={meta.title}
                whatIs={meta.what_is}
                purpose={meta.purpose}
                impact={meta.impact}
                example={meta.example}
                doWrite={meta.do_write}
                dontWrite={meta.dont_write}
                validation={`min ${meta.validation?.min_chars ?? 0} · max ${meta.validation?.max_chars ?? "—"}`}
              />
              <div>
                <textarea
                  className="min-h-[180px] w-full rounded border bg-background p-2 text-sm"
                  value={draftBlocks[meta.key] || ""}
                  disabled={!selected || !editable}
                  onChange={(e) =>
                    setDraftBlocks((prev) => ({ ...prev, [meta.key]: e.target.value }))
                  }
                  placeholder="Sin cajas vacías sin explicación — use la ayuda a la izquierda."
                />
                <div className="mt-1 text-xs text-muted-foreground">
                  {(draftBlocks[meta.key] || "").length} caracteres
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
