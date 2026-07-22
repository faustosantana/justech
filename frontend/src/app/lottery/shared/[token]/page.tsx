"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getApiUrl } from "@/lib/api";

/** Vista pública limitada de un share — sin shell JAIOS. */
export default function LotterySharedPublicPage() {
  const params = useParams<{ token: string }>();
  const [data, setData] = useState<{
    title: string;
    query_type: string;
    expires_at: string;
    disclaimer: string;
    branding: string;
    result: { rows?: unknown[]; meta?: Record<string, unknown> };
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = params.token;
    if (!token) return;
    fetch(`${getApiUrl()}/lottery/shared/${encodeURIComponent(token)}`)
      .then(async (r) => {
        if (!r.ok) {
          const body = await r.json().catch(() => ({}));
          throw new Error(body.detail || `Error ${r.status}`);
        }
        return r.json();
      })
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Enlace no disponible"));
  }, [params.token]);

  return (
    <main className="mx-auto min-h-screen max-w-3xl bg-background p-6 text-foreground">
      <p className="mb-4 text-sm text-muted-foreground">JAIOS · Resultados de Loterías (enlace temporal)</p>
      {error && (
        <Card className="border-destructive/40">
          <CardContent className="py-4 text-sm text-destructive">{String(error)}</CardContent>
        </Card>
      )}
      {data && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{data.title}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p>Tipo: {data.query_type}</p>
              <p>Expira: {data.expires_at}</p>
              <pre tabIndex={0} className="max-h-[480px] overflow-auto rounded-md bg-muted p-3 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring">
                {JSON.stringify(data.result, null, 2)}
              </pre>
              <p className="text-xs text-muted-foreground">{data.disclaimer}</p>
            </CardContent>
          </Card>
        </div>
      )}
    </main>
  );
}
