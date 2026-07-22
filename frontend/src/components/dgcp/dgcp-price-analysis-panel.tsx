"use client";

import { Loader2, Sparkles } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import type { DGCPPriceAnalysis } from "@/lib/prices";
import { cn } from "@/lib/utils";

function riskClass(level: string) {
  if (level === "bajo") return "bg-emerald-500/15 text-emerald-700";
  if (level === "medio") return "bg-amber-500/15 text-amber-800";
  return "bg-red-500/15 text-red-700";
}

export function DGCPPriceAnalysisPanel({ opportunityId }: { opportunityId: string }) {
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState<DGCPPriceAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.analyzeDGCPrices(opportunityId);
      setAnalysis(res);
    } catch (e) {
      setAnalysis(null);
      setError(e instanceof Error ? e.message : "Error al analizar precios");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="border-violet-500/20">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Sparkles className="h-4 w-4 text-violet-600" />
          Price Intelligence — listas de precios
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Compare requerimientos de la licitación contra proveedores indexados (Excel/CSV).
        </p>
        <Button onClick={() => void run()} disabled={loading} variant="outline" size="sm">
          {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
          Analizar licitación (precios)
        </Button>
        {error && <p className="text-sm text-destructive">{error}</p>}
        {analysis && (
          <div className="space-y-4 text-sm">
            <p className="rounded-lg bg-muted/50 p-3">{analysis.overall_recommendation}</p>
            {(analysis.total_estimated_cost || analysis.total_suggested_sale) && (
              <div className="grid gap-2 sm:grid-cols-3">
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground">Costo estimado</p>
                  <p className="font-semibold">
                    {analysis.currency} {analysis.total_estimated_cost ?? "—"}
                  </p>
                </div>
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground">Venta sugerida</p>
                  <p className="font-semibold">
                    {analysis.currency} {analysis.total_suggested_sale ?? "—"}
                  </p>
                </div>
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground">Margen</p>
                  <p className="font-semibold">{analysis.estimated_margin_pct ?? "—"}%</p>
                </div>
              </div>
            )}
            {analysis.line_items.map((line) => (
              <div key={line.label} className="rounded-lg border p-3 space-y-2">
                <p className="font-medium">
                  {line.quantity}× {line.label.slice(0, 100)}
                </p>
                {line.compare.recommendation && (
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium", riskClass(line.compare.recommendation.risk_level))}>
                      {line.compare.recommendation.primary_supplier} · score {line.compare.recommendation.confidence}%
                    </span>
                    {line.compare.recommendation.sale_price_suggested && (
                      <span className="text-xs text-muted-foreground">
                        Venta u. {line.compare.recommendation.currency} {line.compare.recommendation.sale_price_suggested}
                      </span>
                    )}
                  </div>
                )}
                {line.compare.offers.length > 0 && (
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-left text-muted-foreground">
                          <th className="py-1 pr-2">Proveedor</th>
                          <th className="py-1 pr-2">Precio</th>
                          <th className="py-1 pr-2">Stock</th>
                          <th className="py-1 pr-2">Score</th>
                          <th className="py-1">Margen</th>
                        </tr>
                      </thead>
                      <tbody>
                        {line.compare.offers.slice(0, 5).map((o) => (
                          <tr key={o.product.id} className="border-t border-border/40">
                            <td className="py-1 pr-2">{o.product.supplier}</td>
                            <td className="py-1 pr-2 font-mono">
                              {o.product.currency} {o.product.preferred_price ?? o.product.price}
                            </td>
                            <td className="py-1 pr-2">{o.product.stock ?? "—"}</td>
                            <td className="py-1 pr-2">{o.score}</td>
                            <td className="py-1">{String(o.margin.margin_pct_actual ?? "—")}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
