"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

export default function PromptVersionsPage() {
  const [items, setItems] = useState<Record<string, unknown>[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [compare, setCompare] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await apiClient.getLotteryAIPrompts();
      setItems(((res as { items?: Record<string, unknown>[] }).items || []) as Record<string, unknown>[]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar versiones");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const toggleSel = (id: string) => {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 2) return [prev[1], id];
      return [...prev, id];
    });
  };

  const runCompare = async () => {
    if (selected.length !== 2) {
      setError("Seleccione exactamente 2 versiones");
      return;
    }
    try {
      const res = await apiClient.getLotteryPromptCompare(selected[0], selected[1]);
      setCompare(res);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Compare falló");
    }
  };

  const duplicate = async (id: string) => {
    try {
      await apiClient.postLotteryAIPrompt({ from_prompt_id: id, display_name: "Copia" });
      setMsg("Versión duplicada como borrador");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Duplicar falló");
    }
  };

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Versiones de prompt</h1>
      <p className="rounded border bg-muted/40 p-3 text-sm">
        Una versión es una fotografía completa del prompt, sus herramientas, motores y
        configuración en un momento determinado.
      </p>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      {msg ? <p className="text-sm text-green-700">{msg}</p> : null}
      <div className="flex gap-2">
        <Button type="button" variant="outline" disabled={selected.length !== 2} onClick={() => void runCompare()}>
          Comparar seleccionadas
        </Button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left">
              <th className="py-2 pr-2" />
              <th className="py-2 pr-2">Nombre</th>
              <th className="py-2 pr-2">Versión</th>
              <th className="py-2 pr-2">Estado</th>
              <th className="py-2 pr-2">Modelo</th>
              <th className="py-2 pr-2">Fecha</th>
              <th className="py-2 pr-2">Notas / motivo</th>
              <th className="py-2">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {items.map((p) => {
              const id = String(p.id);
              return (
                <tr key={id} className="border-b border-border/40 align-top">
                  <td className="py-2 pr-2">
                    <input
                      type="checkbox"
                      checked={selected.includes(id)}
                      onChange={() => toggleSel(id)}
                    />
                  </td>
                  <td className="py-2 pr-2 font-medium">{String(p.display_name || p.name)}</td>
                  <td className="py-2 pr-2">{String(p.version)}</td>
                  <td className="py-2 pr-2">{String(p.status_label || p.status)}</td>
                  <td className="py-2 pr-2">{String(p.recommended_model || "—")}</td>
                  <td className="py-2 pr-2 text-xs">{String(p.updated_at || p.created_at || "—")}</td>
                  <td className="py-2 pr-2 text-xs">
                    {String(p.change_reason || p.notes || p.changelog || "—")}
                  </td>
                  <td className="py-2">
                    <Button type="button" size="sm" variant="outline" onClick={() => void duplicate(id)}>
                      Duplicar
                    </Button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {compare ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Comparación</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="max-h-96 overflow-auto text-xs">{JSON.stringify(compare, null, 2)}</pre>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
