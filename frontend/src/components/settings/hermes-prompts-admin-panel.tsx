"use client";

import { useCallback, useEffect, useState } from "react";
import { Eye, History, RefreshCw, Save, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";

type RegistryEntry = Awaited<ReturnType<typeof apiClient.getCopilotPromptsRegistry>>["registry"][number];

const TYPE_LABELS: Record<string, string> = {
  security_base: "Seguridad base",
  global: "Global",
  module: "Módulo",
  role: "Rol",
  user: "Usuario",
  company: "Empresa",
  tool: "Herramienta",
};

export function HermesPromptsAdminPanel() {
  const [registry, setRegistry] = useState<RegistryEntry[]>([]);
  const [prompts, setPrompts] = useState<Record<string, string>>({});
  const [history, setHistory] = useState<Record<string, { content: string; saved_at: string }[]>>({});
  const [securityBase, setSecurityBase] = useState("");
  const [selected, setSelected] = useState<RegistryEntry | null>(null);
  const [draft, setDraft] = useState("");
  const [roleKey, setRoleKey] = useState("ventas");
  const [userTargetId, setUserTargetId] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiClient.getCopilotPromptsRegistry();
      setRegistry(data.registry);
      setPrompts(data.config.prompts ?? {});
      setHistory(data.config.prompt_version_history ?? {});
      setSecurityBase(data.config.security_base_prompt ?? "");
      if (!selected && data.registry.length) {
        const first = data.registry.find((r) => r.editable !== false) ?? data.registry[0];
        selectEntry(first, data.config.prompts ?? {}, data.config);
      }
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al cargar prompts");
    } finally {
      setLoading(false);
    }
  }, [selected]);

  const selectEntry = (
    entry: RegistryEntry,
    p: Record<string, string>,
    cfg?: Awaited<ReturnType<typeof apiClient.getCopilotPromptsRegistry>>["config"],
  ) => {
    setSelected(entry);
    setPreview(null);
    setTestResult(null);
    if (entry.type === "security_base") {
      setDraft(securityBase);
      return;
    }
    if (entry.type === "module" || entry.type === "global") {
      setDraft(p[entry.key] ?? cfg?.default_prompts?.[entry.key] ?? "");
      return;
    }
    const bucket =
      entry.type === "role"
        ? cfg?.role_prompts
        : entry.type === "user"
          ? cfg?.user_prompts
          : entry.type === "tool"
            ? (cfg as { tool_prompts?: Record<string, string> }).tool_prompts
            : (cfg as { company_prompts?: Record<string, string> }).company_prompts;
    setDraft(bucket?.[entry.key] ?? "");
  };

  useEffect(() => {
    void load();
  }, [load]);

  const save = async () => {
    if (!selected || selected.editable === false) return;
    setSaving(true);
    setError(null);
    try {
      if (selected.type === "module" || selected.type === "global") {
        await apiClient.saveHermesPrompt(selected.key, draft);
      } else if (selected.type === "role") {
        await apiClient.saveCopilotTypedPrompt({
          prompt_type: "role",
          key: roleKey,
          content: draft,
          target_id: roleKey,
        });
      } else if (selected.type === "user") {
        await apiClient.saveCopilotTypedPrompt({
          prompt_type: "user",
          key: userTargetId,
          content: draft,
          target_id: userTargetId,
        });
      } else {
        await apiClient.saveCopilotTypedPrompt({
          prompt_type: selected.type,
          key: selected.key,
          content: draft,
          target_id: selected.key,
        });
      }
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  };

  const restore = async (index: number) => {
    if (!selected?.key) return;
    try {
      await apiClient.restoreHermesPrompt(selected.key, index);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al restaurar");
    }
  };

  const doPreview = async () => {
    if (!selected) return;
    const res = await apiClient.previewHermesPrompt(selected.key, draft);
    setPreview(res.preview);
  };

  const testPrompt = async () => {
    setTesting(true);
    try {
      const res = await apiClient.testHermesPrompt({ key: selected?.key ?? "global", content: draft });
      setTestResult(`Respuesta: ${res.answer.slice(0, 300)} (${res.latency_ms ?? "—"} ms)`);
    } catch (e) {
      setTestResult(e instanceof Error ? e.message : "Error");
    } finally {
      setTesting(false);
    }
  };

  const versions = selected?.type === "module" || selected?.type === "global"
    ? (history[selected.key] ?? [])
    : [];

  return (
    <div className="space-y-6">
      {error && <p className="text-sm text-destructive">{error}</p>}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base">Jerarquía de prompts</CardTitle>
            <p className="text-xs text-muted-foreground mt-1">
              Seguridad base → Global → Módulo → Rol → Usuario → Contexto. La seguridad nunca puede ser anulada.
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
            <RefreshCw className={`mr-1 h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Actualizar
          </Button>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-[280px_1fr]">
          <div className="max-h-[520px] overflow-auto rounded-lg border border-border">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-muted/80">
                <tr>
                  <th className="px-2 py-1.5 text-left font-medium">Tipo</th>
                  <th className="px-2 py-1.5 text-left font-medium">Nombre</th>
                  <th className="px-2 py-1.5 text-left font-medium">Estado</th>
                </tr>
              </thead>
              <tbody>
                {registry.map((entry) => (
                  <tr
                    key={entry.id}
                    className={`cursor-pointer border-t border-border hover:bg-muted/40 ${selected?.id === entry.id ? "bg-primary/10" : ""}`}
                    onClick={() => selectEntry(entry, prompts)}
                  >
                    <td className="px-2 py-1.5 text-muted-foreground">{TYPE_LABELS[entry.type] ?? entry.type}</td>
                    <td className="px-2 py-1.5 font-medium">{entry.label || entry.key}</td>
                    <td className="px-2 py-1.5">{entry.active ? "Activo" : "Inactivo"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="space-y-3">
            {selected && (
              <>
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="font-medium">{selected.label || selected.key}</span>
                  <span className="text-muted-foreground">· {TYPE_LABELS[selected.type]}</span>
                  {selected.updated_at && (
                    <span className="text-xs text-muted-foreground">
                      Última edición: {new Date(selected.updated_at).toLocaleString("es-DO")}
                    </span>
                  )}
                </div>

                {(selected.type === "role" || selected.id.startsWith("new-role")) && (
                  <input
                    className="w-full rounded border border-input px-2 py-1 text-sm"
                    placeholder="Rol (ventas, finanzas, compras…)"
                    value={roleKey}
                    onChange={(e) => setRoleKey(e.target.value)}
                  />
                )}
                {selected.type === "user" && (
                  <input
                    className="w-full rounded border border-input px-2 py-1 text-sm"
                    placeholder="UUID del usuario"
                    value={userTargetId}
                    onChange={(e) => setUserTargetId(e.target.value)}
                  />
                )}

                <textarea
                  className="min-h-[280px] w-full rounded-lg border border-input bg-background px-3 py-2 font-mono text-sm"
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  readOnly={selected.editable === false}
                />

                <div className="flex flex-wrap gap-2">
                  {selected.editable !== false && (
                    <Button onClick={() => void save()} disabled={saving}>
                      <Save className="mr-1 h-3.5 w-3.5" />
                      {saving ? "Guardando…" : "Guardar"}
                    </Button>
                  )}
                  <Button variant="outline" onClick={() => void doPreview()}>
                    <Eye className="mr-1 h-3.5 w-3.5" />
                    Vista previa
                  </Button>
                  <Button variant="outline" onClick={() => void testPrompt()} disabled={testing}>
                    <Sparkles className="mr-1 h-3.5 w-3.5" />
                    Probar
                  </Button>
                  {selected.type === "role" && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        setSelected({
                          id: `new-role:${roleKey}`,
                          type: "role",
                          key: roleKey,
                          label: `Rol: ${roleKey}`,
                          active: true,
                          editable: true,
                        })
                      }
                    >
                      + Prompt por rol
                    </Button>
                  )}
                </div>

                {preview && (
                  <pre className="max-h-40 overflow-auto rounded-lg bg-muted/40 p-3 text-xs whitespace-pre-wrap">{preview}</pre>
                )}
                {testResult && (
                  <p className="rounded-lg border border-border bg-muted/30 px-3 py-2 text-xs">{testResult}</p>
                )}

                {versions.length > 0 && (
                  <div className="space-y-2">
                    <p className="flex items-center gap-1 text-xs font-medium text-muted-foreground">
                      <History className="h-3.5 w-3.5" /> Historial ({versions.length})
                    </p>
                    <ul className="space-y-1 text-xs">
                      {versions.map((v, i) => (
                        <li key={i} className="flex items-center justify-between gap-2 rounded border px-2 py-1">
                          <span>{new Date(v.saved_at).toLocaleString("es-DO")}</span>
                          <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={() => void restore(i)}>
                            Restaurar
                          </Button>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
