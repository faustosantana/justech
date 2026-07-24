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
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const schema = await apiClient.getLotteryPromptStudioSchema();
      setBlocksMeta((schema.blocks || []) as BlockMeta[]);
      const prompts = await apiClient.getLotteryAIPrompts();
      const items = ((prompts as { items?: Record<string, unknown>[] }).items || []) as Record<
        string,
        unknown
      >[];
      const active = items.find((p) => p.status === "active") || items[0] || null;
      if (active?.id) {
        const full = await apiClient.getLotteryAIPrompt(String(active.id));
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
      setMsg("Borrador guardado.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar (¿secretos?)");
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

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-xl font-semibold">Prompt Studio · Bloques</h1>
          <p className="text-sm text-muted-foreground">
            Cada casilla tiene ayuda. Edición solo en borrador — no modifica ACTIVO.
          </p>
        </div>
        <div className="flex gap-2">
          <Button type="button" variant="outline" disabled={busy} onClick={() => void createDraft()}>
            Crear borrador desde activo
          </Button>
          <Button type="button" disabled={busy || !selected} onClick={() => void saveDraft()}>
            Guardar borrador
          </Button>
          <Link className="rounded border px-3 py-2 text-sm" href="/lottery/admin/control-center/prompt-studio/compilado">
            Ver compilado
          </Link>
        </div>
      </div>
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
                  disabled={!selected || !["draft", "validated", "approved"].includes(String(selected.status))}
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
