"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiClient } from "@/lib/api";

export default function PromptPlaygroundPage() {
  const [message, setMessage] = useState("Dame la predicción del 34 en Leidsa usando las últimas 20");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const run = async (mode: "draft" | "active") => {
    setBusy(true);
    setError(null);
    try {
      const res = await apiClient.postLotteryControlCenterPlayground({ message, mode });
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Playground falló");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Playground (borrador vs activo)</h1>
      <p className="text-sm text-muted-foreground">
        Prueba intent/planificación sin alterar la versión ACTIVA. No publica.
      </p>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Consulta</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Input value={message} onChange={(e) => setMessage(e.target.value)} />
          <div className="flex flex-wrap gap-2">
            <Button type="button" disabled={busy} onClick={() => void run("draft")}>
              Ejecutar con borrador
            </Button>
            <Button type="button" variant="outline" disabled={busy} onClick={() => void run("active")}>
              Ejecutar con activo
            </Button>
          </div>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          {result ? (
            <pre className="max-h-96 overflow-auto rounded bg-muted p-3 text-xs">
              {JSON.stringify(result, null, 2)}
            </pre>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
