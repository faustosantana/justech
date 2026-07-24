"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiClient } from "@/lib/api";

export default function PromptCompiledPage() {
  const [promptId, setPromptId] = useState<string | null>(null);
  const [compiled, setCompiled] = useState<Record<string, unknown> | null>(null);
  const [q, setQ] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [technical, setTechnical] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const prompts = await apiClient.getLotteryAIPrompts();
      const items = ((prompts as { items?: Record<string, unknown>[] }).items || []) as Record<
        string,
        unknown
      >[];
      const active = items.find((p) => p.status === "active") || items[0];
      if (!active?.id) {
        setError("No hay versiones de prompt");
        return;
      }
      setPromptId(String(active.id));
      const res = await apiClient.getLotteryPromptCompiled(String(active.id), q || undefined);
      setCompiled(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar prompt compilado");
    }
  }, [q]);

  useEffect(() => {
    void load();
  }, [load]);

  const body = String((compiled?.compiled as { body?: string } | undefined)?.body || "");

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Prompt compilado</h1>
      <p className="text-sm text-muted-foreground">
        Prompt funcional final de Lottery IA. Sin secretos ni credenciales.
      </p>
      <div className="flex flex-wrap gap-2">
        <Input
          placeholder="Buscar en prompt"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="max-w-xs"
        />
        <Button type="button" variant="outline" onClick={() => void load()}>
          Buscar
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => void navigator.clipboard.writeText(body)}
        >
          Copiar
        </Button>
        <Button type="button" variant="outline" onClick={() => setTechnical((v) => !v)}>
          {technical ? "Vista normal" : "Vista técnica"}
        </Button>
      </div>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Versión activa · id {technical ? promptId : "(oculto)"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap rounded bg-muted p-3 text-xs">
            {body || "—"}
          </pre>
          {technical && compiled ? (
            <pre className="mt-3 max-h-64 overflow-auto rounded border p-2 text-[10px]">
              {JSON.stringify(compiled, null, 2)}
            </pre>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
