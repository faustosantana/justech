"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { useLotteryAIDevMode } from "@/components/lottery/ai-admin-dev-mode";
import { MetricLine } from "@/components/lottery/ai-admin-display";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

const BLOCK_LABELS: Record<string, string> = {
  identidad: "Identidad",
  dominio: "Dominio",
  memoria: "Memoria",
  aclaraciones: "Aclaraciones",
  analisis: "Análisis",
  seguridad: "Seguridad",
  formato: "Formato",
  tono: "Tono",
};

const DEFAULT_BLOCKS = Object.keys(BLOCK_LABELS);

function simpleDiff(before: string, after: string): string {
  if (before === after) return "(sin cambios)";
  const a = before.split("\n");
  const b = after.split("\n");
  const lines: string[] = [];
  const max = Math.max(a.length, b.length);
  for (let i = 0; i < max; i++) {
    const left = a[i];
    const right = b[i];
    if (left === right) continue;
    if (left !== undefined && right === undefined) lines.push(`- ${left}`);
    else if (left === undefined && right !== undefined) lines.push(`+ ${right}`);
    else {
      lines.push(`- ${left}`);
      lines.push(`+ ${right}`);
    }
  }
  return lines.slice(0, 80).join("\n") || "(cambios en líneas no textuales)";
}

export default function LotteryAIPromptsPage() {
  const { developerMode } = useLotteryAIDevMode();
  const [prompts, setPrompts] = useState<Record<string, unknown>[]>([]);
  const [blockKeys, setBlockKeys] = useState<string[]>(DEFAULT_BLOCKS);
  const [gates, setGates] = useState<{ can_publish: boolean; blockers: { message: string }[] } | null>(null);
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);
  const [baselineBody, setBaselineBody] = useState("");
  const [blocks, setBlocks] = useState<Record<string, string>>({});
  const [body, setBody] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [showDiff, setShowDiff] = useState(false);

  const isDraft = selected && ["draft", "validated"].includes(String(selected.status));
  const publishBlocked = gates ? !gates.can_publish : false;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getLotteryAIPrompts();
      const items = ((res as { items?: unknown[]; versions?: unknown[] }).items
        ?? (res as { versions?: unknown[] }).versions
        ?? []) as Record<string, unknown>[];
      setPrompts(items);
      setBlockKeys(((res as { prompt_blocks?: string[] }).prompt_blocks ?? DEFAULT_BLOCKS) as string[]);
      setGates((res as { publish_gates?: typeof gates }).publish_gates ?? null);
      if (!items.length) {
        setError(
          String(
            (res as { empty_reason?: string }).empty_reason ??
              "No hay versiones de prompt. El seed debería crear v1/v2/v3 — recargue o revise permisos/DB.",
          ),
        );
      }
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
    setShowDiff(false);
    try {
      const p = await apiClient.getLotteryAIPrompt(id);
      setSelected(p);
      const b = String(p.body ?? "");
      setBody(b);
      setBaselineBody(b);
      const rawBlocks = (p.blocks ?? {}) as Record<string, string>;
      const next: Record<string, string> = {};
      for (const k of blockKeys) next[k] = String(rawBlocks[k] ?? "");
      if (!Object.values(next).some(Boolean) && b) next.identidad = b.slice(0, 1200);
      setBlocks(next);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar prompt");
    }
  };

  const createDraft = async (from: "active" | "selected" | "blank") => {
    setBusy(true);
    setMsg(null);
    try {
      const payload: Record<string, unknown> =
        from === "active"
          ? { from_active: true }
          : from === "selected" && selected
            ? { from_prompt_id: selected.id }
            : { body: "", blocks: Object.fromEntries(blockKeys.map((k) => [k, ""])) };
      const p = await apiClient.postLotteryAIPrompt(payload);
      setMsg(`Borrador creado (${String(p.version ?? "draft")})`);
      await load();
      if (p.id) await selectPrompt(String(p.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al crear borrador");
    } finally {
      setBusy(false);
    }
  };

  const saveDraft = async () => {
    if (!selected || !isDraft) return;
    setBusy(true);
    setMsg(null);
    try {
      const updated = await apiClient.putLotteryAIPrompt(String(selected.id), { blocks, body });
      setSelected(updated);
      setBody(String(updated.body ?? body));
      setMsg("Borrador guardado");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al guardar");
    } finally {
      setBusy(false);
    }
  };

  const publish = async () => {
    if (!selected) return;
    if (publishBlocked) {
      setError(
        `Publicación bloqueada: ${(gates?.blockers ?? []).map((b) => b.message).join("; ") || "gates activos"}`,
      );
      return;
    }
    if (!window.confirm("¿Publicar este prompt? Se activará en producción solo si pasan los gates.")) return;
    setBusy(true);
    setMsg(null);
    try {
      await apiClient.postLotteryAIPromptPublish(String(selected.id));
      setMsg("Prompt publicado");
      await load();
      await selectPrompt(String(selected.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al publicar");
    } finally {
      setBusy(false);
    }
  };

  const rollback = async () => {
    if (!selected) return;
    if (!window.confirm("¿Revertir a la versión anterior?")) return;
    setBusy(true);
    setMsg(null);
    try {
      const p = await apiClient.postLotteryAIPromptRollback(String(selected.id));
      setMsg(`Revertido a ${String(p.version ?? "versión anterior")}`);
      await load();
      if (p.id) await selectPrompt(String(p.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al revertir");
    } finally {
      setBusy(false);
    }
  };

  const composedPreview = useMemo(() => {
    const parts = blockKeys
      .map((k) => {
        const v = (blocks[k] || "").trim();
        return v ? `## ${k.toUpperCase()}\n${v}` : "";
      })
      .filter(Boolean);
    return parts.join("\n\n") || body;
  }, [blocks, blockKeys, body]);

  const statusBadge = (status: unknown) => {
    const s = String(status ?? "");
    if (s === "active") return "activo";
    if (s === "draft") return "borrador";
    if (s === "replaced") return "reemplazado";
    if (s === "archived") return "archivado";
    return s || "Sin datos suficientes";
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold">Prompt Studio</h2>
          <p className="text-sm text-muted-foreground">
            Borrador → Validación → Playground → Benchmark → Publicación
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
            Actualizar
          </Button>
          <Button size="sm" variant="outline" onClick={() => void createDraft("active")} disabled={busy}>
            Borrador desde activo
          </Button>
          <Button size="sm" variant="outline" onClick={() => void createDraft("selected")} disabled={busy || !selected}>
            Borrador desde selección
          </Button>
          <Button size="sm" onClick={() => void createDraft("blank")} disabled={busy}>
            Plantilla vacía
          </Button>
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {msg && <p className="text-sm text-muted-foreground">{msg}</p>}

      {gates && (
        <Card>
          <CardHeader className="py-3">
            <CardTitle className="text-sm">
              Gates de publicación: {gates.can_publish ? "OK para publicar" : "Bloqueado"}
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            {gates.can_publish ? (
              <p className="text-muted-foreground">Sin bloqueos P0/P1 conocidos.</p>
            ) : (
              <ul className="list-disc space-y-1 pl-5 text-destructive">
                {(gates.blockers ?? []).map((b, i) => (
                  <li key={i}>{b.message}</li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 xl:grid-cols-[280px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Versiones</CardTitle>
          </CardHeader>
          <CardContent className="max-h-[70vh] space-y-1 overflow-auto">
            {loading && <p className="text-sm text-muted-foreground">Cargando…</p>}
            {prompts.length === 0 && !loading && (
              <p className="text-sm text-muted-foreground">
                Sin versiones en la respuesta API. El seed debería crear v1, v2 y v3 draft — pulse Actualizar.
              </p>
            )}
            {prompts.map((row) => {
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
                  <span className="font-medium">{String(row.version ?? "sin-versión")}</span>{" "}
                  <span className="text-xs text-muted-foreground">{statusBadge(row.status)}</span>
                  {String(row.status) === "active" ? (
                    <span className="ml-1 rounded bg-green-500/15 px-1.5 text-[10px] text-green-700">PROD</span>
                  ) : null}
                  {developerMode ? (
                    <div className="font-mono text-[10px] text-muted-foreground">{String(row.id)}</div>
                  ) : null}
                </button>
              );
            })}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Editor por bloques</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {!selected ? (
              <p className="text-sm text-muted-foreground">Seleccione una versión.</p>
            ) : (
              <>
                <div className="grid gap-2 sm:grid-cols-2">
                  <MetricLine label="Versión" value={selected.version} />
                  <MetricLine label="Estado" value={statusBadge(selected.status)} />
                  <MetricLine label="Modelo recomendado" value={selected.recommended_model} />
                  <MetricLine label="Publicado" value={selected.published_at} />
                </div>

                {blockKeys.map((key) => (
                  <label key={key} className="block space-y-1">
                    <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      {BLOCK_LABELS[key] ?? key}
                    </span>
                    <textarea
                      className="min-h-20 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                      value={blocks[key] ?? ""}
                      disabled={!isDraft}
                      onChange={(e) => setBlocks((prev) => ({ ...prev, [key]: e.target.value }))}
                    />
                  </label>
                ))}

                {developerMode ? (
                  <label className="block space-y-1">
                    <span className="text-xs font-medium text-muted-foreground">Body completo (dev)</span>
                    <textarea
                      className="min-h-32 w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-xs"
                      value={body}
                      disabled={!isDraft}
                      onChange={(e) => setBody(e.target.value)}
                    />
                  </label>
                ) : null}

                {!isDraft && (
                  <p className="text-xs text-muted-foreground">
                    Solo se editan borradores. Cree un borrador desde el activo o esta versión.
                  </p>
                )}

                {showDiff && (
                  <pre className="max-h-48 overflow-auto rounded bg-muted/40 p-2 text-[11px]">
                    {simpleDiff(baselineBody, composedPreview)}
                  </pre>
                )}

                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="outline" onClick={() => void saveDraft()} disabled={busy || !isDraft}>
                    Guardar borrador
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setShowDiff((v) => !v)} disabled={!selected}>
                    {showDiff ? "Ocultar diff" : "Ver diff"}
                  </Button>
                  <Button size="sm" variant="outline" asChild>
                    <Link href="/lottery/admin/ai/playground">Probar en Playground</Link>
                  </Button>
                  <Button size="sm" variant="outline" asChild>
                    <Link href="/lottery/admin/ai/benchmarks">Ejecutar benchmark</Link>
                  </Button>
                  <Button size="sm" onClick={() => void publish()} disabled={busy || publishBlocked}>
                    {publishBlocked ? "Publicar (bloqueado)" : "Publicar"}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => void rollback()} disabled={busy}>
                    Revertir
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <TonePreviewPanel />
    </div>
  );
}

function TonePreviewPanel() {
  const [tones, setTones] = useState<unknown[]>([]);
  const [toneKey, setToneKey] = useState("analitico");
  const [message, setMessage] = useState("¿Cuándo salió el 57 en Leidsa?");
  const [left, setLeft] = useState<Record<string, unknown> | null>(null);
  const [right, setRight] = useState<Record<string, unknown> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    apiClient
      .getLotteryAITones()
      .then((r) => setTones(r.items ?? []))
      .catch(() => setTones([]));
  }, []);

  const run = async () => {
    setErr(null);
    try {
      const [a, b] = await Promise.all([
        apiClient.postLotteryAITonePreview({ message, tone_key: toneKey, prompt_version: "v2" }),
        apiClient.postLotteryAITonePreview({ message, tone_key: toneKey, prompt_version: "v3" }),
      ]);
      setLeft(a);
      setRight(b);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Preview falló");
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Preview de tono (v2 vs v3) — no altera config activa</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap gap-2">
          <select
            className="rounded border border-border bg-background px-2 py-1 text-sm"
            value={toneKey}
            onChange={(e) => setToneKey(e.target.value)}
          >
            {(tones as { key: string; display_name: string }[]).map((t) => (
              <option key={t.key} value={t.key}>
                {t.display_name || t.key}
              </option>
            ))}
            {tones.length === 0 ? <option value="analitico">Analítico</option> : null}
          </select>
          <input
            className="min-w-[240px] flex-1 rounded border border-border bg-background px-2 py-1 text-sm"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
          />
          <Button type="button" size="sm" onClick={() => void run()}>
            Comparar
          </Button>
        </div>
        {err ? <p className="text-sm text-destructive">{err}</p> : null}
        <div className="grid gap-3 md:grid-cols-2">
          {[left, right].map((side, idx) => (
            <div key={idx} className="rounded border border-border/60 p-2 text-xs">
              <p className="font-medium">{idx === 0 ? "v2" : "v3"}</p>
              {side ? (
                <ul className="mt-1 space-y-0.5 text-muted-foreground">
                  <li>Intent: {String((side.understanding as Record<string, unknown>)?.intent ?? "Sin datos suficientes")}</li>
                  <li>
                    Aclaración:{" "}
                    {String((side.understanding as Record<string, unknown>)?.needs_clarification ?? "Sin datos suficientes")}
                  </li>
                  <li>
                    Dominio:{" "}
                    {String((side.understanding as Record<string, unknown>)?.domain_class ?? "Sin datos suficientes")}
                  </li>
                  <li>Safety inmutable: {String(side.safety_immutable ?? true)}</li>
                </ul>
              ) : (
                <p className="mt-1 text-muted-foreground italic">Sin datos suficientes — ejecute Comparar</p>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
