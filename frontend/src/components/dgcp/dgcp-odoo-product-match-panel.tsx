"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";

type MatchLine = {
  line_number?: number;
  description?: string;
  reference?: string;
  status?: string;
  confidence?: number;
  suggested_product_name?: string;
  suggested_product_id?: number;
  suggested_default_code?: string;
  approved?: boolean;
  candidates?: Array<{ product_id: number; name?: string; confidence?: number }>;
};

type Props = {
  opportunityId: string;
};

export function DgcpOdooProductMatchPanel({ opportunityId }: Props) {
  const [lines, setLines] = useState<MatchLine[]>([]);
  const [summary, setSummary] = useState<Record<string, number> | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    const res = await apiClient.getDGCPOdooProductMatches(opportunityId);
    setLines((res.lines as MatchLine[]) || []);
    setSummary(res.summary || null);
  }, [opportunityId]);

  useEffect(() => {
    void load().catch(() => setLines([]));
  }, [load]);

  async function run() {
    setBusy(true);
    setMsg(null);
    try {
      const res = await apiClient.runDGCPOdooProductMatches(opportunityId);
      setLines((res.lines as MatchLine[]) || []);
      setSummary(res.summary || null);
      setMsg(res.ok ? "Matching completado" : res.error || "Error");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Error");
    } finally {
      setBusy(false);
    }
  }

  async function decide(lineNumber: number, approve: boolean, productId?: number) {
    setBusy(true);
    try {
      await apiClient.decideDGCPOdooProductMatch(opportunityId, lineNumber, {
        approve,
        productId,
      });
      await load();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="border-primary/20">
      <CardHeader className="flex flex-row items-center justify-between py-3">
        <CardTitle className="text-sm">Productos Odoo (matching)</CardTitle>
        <Button size="sm" variant="outline" disabled={busy} onClick={() => void run()}>
          Ejecutar matching
        </Button>
      </CardHeader>
      <CardContent className="space-y-3 text-xs">
        {summary ? (
          <p className="text-muted-foreground">
            Total {summary.total ?? 0} · MATCHED {summary.matched ?? 0} · REVIEW{" "}
            {summary.review_required ?? 0} · UNMATCHED {summary.unmatched ?? 0}
            {summary.approved != null ? ` · aprobadas ${summary.approved}` : ""}
          </p>
        ) : (
          <p className="text-muted-foreground">Sin matching aún. Ejecute para sugerir productos.</p>
        )}
        {msg ? <p>{msg}</p> : null}
        <ul className="space-y-2">
          {lines.map((ln) => (
            <li key={String(ln.line_number)} className="rounded border p-2">
              <div className="font-medium text-foreground">
                #{ln.line_number} {ln.description || ln.reference || "—"}
              </div>
              <div className="text-muted-foreground">
                Estado: <span className="text-foreground">{ln.status}</span>
                {ln.confidence != null ? ` · ${(Number(ln.confidence) * 100).toFixed(0)}%` : ""}
                {ln.suggested_product_name
                  ? ` → ${ln.suggested_default_code || ""} ${ln.suggested_product_name}`
                  : ""}
                {ln.approved ? " · aprobado" : ""}
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {ln.suggested_product_id && !ln.approved ? (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={busy}
                    onClick={() => void decide(Number(ln.line_number), true, ln.suggested_product_id)}
                  >
                    Usar sugerido
                  </Button>
                ) : null}
                {(ln.candidates || []).slice(0, 3).map((c) => (
                  <Button
                    key={c.product_id}
                    size="sm"
                    variant="ghost"
                    disabled={busy}
                    onClick={() => void decide(Number(ln.line_number), true, c.product_id)}
                  >
                    {c.name?.slice(0, 40)}
                  </Button>
                ))}
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={busy}
                  onClick={() => void decide(Number(ln.line_number), false)}
                >
                  Dejar pendiente
                </Button>
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
