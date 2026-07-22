"use client";

import { Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ConnectorEndpoint } from "@/lib/connectors";

const EMPTY: ConnectorEndpoint = {
  name: "",
  path: "/",
  http_method: "GET",
  query_params: {},
  headers: {},
  assistant_enabled: false,
  sort_order: 0,
};

export function EndpointBuilder({
  endpoints,
  onChange,
}: {
  endpoints: ConnectorEndpoint[];
  onChange: (eps: ConnectorEndpoint[]) => void;
}) {
  const update = (idx: number, patch: Partial<ConnectorEndpoint>) => {
    const next = [...endpoints];
    next[idx] = { ...next[idx], ...patch };
    onChange(next);
  };

  const add = () => onChange([...endpoints, { ...EMPTY, sort_order: endpoints.length }]);
  const remove = (idx: number) => onChange(endpoints.filter((_, i) => i !== idx));

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">Endpoints</CardTitle>
        <Button size="sm" variant="outline" onClick={add}>
          <Plus className="mr-1 h-3.5 w-3.5" />
          Agregar
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {endpoints.length === 0 && (
          <p className="text-sm text-muted-foreground">
            Defina rutas como GET /products/search?q=&#123;&#123;query&#125;&#125;
          </p>
        )}
        {endpoints.map((ep, idx) => (
          <div key={idx} className="rounded-lg border border-border p-4">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-sm font-medium">Endpoint {idx + 1}</span>
              <Button size="sm" variant="ghost" onClick={() => remove(idx)}>
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <input
                className="rounded-lg border border-input px-3 py-2 text-sm"
                placeholder="Nombre (ej: Buscar productos)"
                value={ep.name}
                onChange={(e) => update(idx, { name: e.target.value })}
              />
              <select
                className="rounded-lg border border-input px-3 py-2 text-sm"
                value={ep.http_method}
                onChange={(e) => update(idx, { http_method: e.target.value })}
              >
                {["GET", "POST", "PUT", "PATCH", "DELETE"].map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
              <input
                className="rounded-lg border border-input px-3 py-2 text-sm font-mono md:col-span-2"
                placeholder="/products/search?q={{query}}"
                value={ep.path}
                onChange={(e) => update(idx, { path: e.target.value })}
              />
              <label className="flex items-center gap-2 md:col-span-2">
                <input
                  type="checkbox"
                  checked={ep.assistant_enabled}
                  onChange={(e) => update(idx, { assistant_enabled: e.target.checked })}
                />
                <span className="text-sm">Disponible para el asistente JAIOS</span>
              </label>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
