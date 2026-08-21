"use client";

import {
  AlertCircle,
  ExternalLink,
  Loader2,
  RefreshCw,
  Trophy,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import {
  formatCurrency,
  formatDate,
  type DGCPHistoricalIntelligence,
  type DGCPHistoricalPurchaseRow,
  type DGCPOpportunity,
} from "@/lib/dgcp";
import { cn } from "@/lib/utils";

interface Props {
  opportunity: DGCPOpportunity;
}

type IntelTab = "resumen" | "compras" | "proveedores" | "productos" | "precios" | "relacionados";

const WINDOWS = [
  { label: "12 meses", value: 12 },
  { label: "24 meses", value: 24 },
  { label: "36 meses", value: 36 },
  { label: "Todo", value: 0 },
] as const;

function qualityBadge(q?: string) {
  if (q === "VERIFICADO") return "bg-emerald-100 text-emerald-800";
  if (q === "PARCIAL") return "bg-amber-100 text-amber-900";
  return "bg-slate-100 text-slate-700";
}

function matchBadge(c?: string | null) {
  if (c === "EXACTA") return "bg-emerald-100 text-emerald-900";
  if (c === "ALTA_SIMILITUD") return "bg-sky-100 text-sky-900";
  return "bg-slate-100 text-slate-700";
}

function SourceLink({ row }: { row?: DGCPHistoricalPurchaseRow | null }) {
  const url = row?.source?.contract_url || row?.source?.process_url || row?.source?.source_url;
  if (!url) return null;
  return (
    <a href={url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm text-sky-700 hover:underline">
      Abrir fuente <ExternalLink className="h-3.5 w-3.5" />
    </a>
  );
}

export function DGCPHistoricalAwardsPanel({ opportunity }: Props) {
  const [data, setData] = useState<DGCPHistoricalIntelligence | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [windowMonths, setWindowMonths] = useState(24);
  const [tab, setTab] = useState<IntelTab>("resumen");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiClient.getDGCPHistoricalIntelligence(opportunity.id, {
        window_months: windowMonths,
      });
      setData(result);
    } catch (e) {
      setData(null);
      setError(e instanceof Error ? e.message : "No se pudo cargar la inteligencia histórica");
    } finally {
      setLoading(false);
    }
  }, [opportunity.id, windowMonths]);

  useEffect(() => {
    void load();
  }, [load]);

  const last = data?.last_purchase;
  const lastSup = data?.last_supplier;
  const prices = data?.price_history;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-slate-900">Inteligencia histórica</h3>
          <p className="text-sm text-slate-500">
            Adjudicaciones/contratos indexados DGCP — sin inferencias presentadas como hechos.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {WINDOWS.map((w) => (
            <Button
              key={w.value}
              size="sm"
              variant={windowMonths === w.value ? "default" : "outline"}
              onClick={() => setWindowMonths(w.value)}
            >
              {w.label}
            </Button>
          ))}
          <Button size="sm" variant="outline" onClick={() => void load()} disabled={loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          </Button>
        </div>
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading && !data && (
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" /> Cargando histórico verificable…
        </div>
      )}

      {data && (
        <>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">Última compra</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                {last?.available && last.purchase ? (
                  <>
                    <div className="text-lg font-semibold">{formatDate(last.purchase.award_date)}</div>
                    <Badge className={matchBadge(last.match_class)}>{last.match_class_label}</Badge>
                    <div className="text-sm text-slate-700">{last.purchase.supplier_name || "—"}</div>
                    <div className="text-sm font-medium">
                      {last.purchase.awarded_amount != null
                        ? formatCurrency(Number(last.purchase.awarded_amount), last.purchase.currency)
                        : "Monto no disponible"}
                    </div>
                    <div className="text-xs text-slate-500">{last.purchase.process_code}</div>
                    <SourceLink row={last.purchase} />
                  </>
                ) : (
                  <p className="text-sm text-slate-500">Sin compra comparable verificable.</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">Proveedor más reciente</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                {lastSup?.available ? (
                  <>
                    <div className="text-lg font-semibold leading-snug">{lastSup.supplier_name}</div>
                    <div className="text-sm">{formatDate(lastSup.award_date)}</div>
                    <div className="text-sm font-medium">
                      {lastSup.awarded_amount != null
                        ? formatCurrency(Number(lastSup.awarded_amount), lastSup.currency)
                        : "—"}
                    </div>
                    <div className="text-xs text-slate-500">{lastSup.process_code}</div>
                    {lastSup.source_url && (
                      <a href={lastSup.source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm text-sky-700 hover:underline">
                        Abrir fuente <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                    )}
                  </>
                ) : (
                  <p className="text-sm text-slate-500">Sin proveedor adjudicado reciente.</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">Precio histórico</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                {prices?.available ? (
                  <>
                    <div className="text-sm">Último: <span className="font-semibold">{formatCurrency(Number(prices.last_unit_price), prices.currency)}</span></div>
                    <div className="text-sm">Promedio: {formatCurrency(Number(prices.avg_unit_price), prices.currency)}</div>
                    <div className="text-sm">Rango: {formatCurrency(Number(prices.min_unit_price), prices.currency)} – {formatCurrency(Number(prices.max_unit_price), prices.currency)}</div>
                    {prices.caveats?.[0] && <p className="text-xs text-amber-700">{prices.caveats[0]}</p>}
                  </>
                ) : (
                  <p className="text-sm text-slate-500">Sin precios unitarios confiables.</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">Procesos similares</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                <div className="text-lg font-semibold">{data.related_processes?.length ?? 0}</div>
                <div className="text-sm text-slate-600">
                  {data.statistics?.unique_processes ?? 0} procesos · {data.statistics?.unique_suppliers ?? 0} proveedores
                </div>
                <div className="text-xs text-slate-500">
                  Calidad: <Badge className={qualityBadge(data.data_quality?.overall)}>{data.data_quality?.overall}</Badge>
                </div>
                {data.latency_ms != null && (
                  <div className="text-xs text-slate-400">{data.latency_ms} ms · {data.indexed_lines_scanned} líneas escaneadas</div>
                )}
              </CardContent>
            </Card>
          </div>

          {(last?.caveats?.length || data.budget_comparison?.caveats?.length) ? (
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600 space-y-1">
              {last?.caveats?.map((c) => <p key={c}>• {c}</p>)}
              {data.budget_comparison?.available && (
                <p>
                  Presupuesto actual (estimado): {formatCurrency(Number(data.budget_comparison.current_estimated_amount), data.budget_comparison.current_currency)}
                  {" · "}
                  Última comparable (adjudicado): {formatCurrency(Number(data.budget_comparison.last_comparable_amount), data.budget_comparison.current_currency)}
                  {data.budget_comparison.variation_pct != null && ` · Variación ${data.budget_comparison.variation_pct}%`}
                </p>
              )}
            </div>
          ) : null}

          <div className="flex flex-wrap gap-1 border-b border-slate-200 pb-1">
            {(
              [
                ["resumen", "Resumen"],
                ["compras", "Compras"],
                ["proveedores", "Proveedores"],
                ["productos", "Productos"],
                ["precios", "Precios"],
                ["relacionados", "Procesos relacionados"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setTab(id)}
                className={cn(
                  "rounded-md px-3 py-1.5 text-sm",
                  tab === id ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100",
                )}
              >
                {label}
              </button>
            ))}
          </div>

          {tab === "resumen" && (
            <div className="space-y-3">
              {data.executive_summary?.paragraphs?.map((p) => (
                <p key={p} className="text-sm leading-relaxed text-slate-700">{p}</p>
              ))}
              {data.frequency?.available && (
                <div className="rounded-md border p-3 text-sm">
                  <div className="font-medium mb-1">Frecuencia de compra</div>
                  <p>{data.frequency.summary}</p>
                  {data.frequency.temporal_pattern && (
                    <p className="mt-1 text-slate-600">{data.frequency.temporal_pattern}</p>
                  )}
                </div>
              )}
              {data.concentration && (
                <div className="rounded-md border p-3 text-sm">
                  <div className="font-medium mb-1">Concentración de proveedores: {data.concentration.level}</div>
                  <p>
                    Top 1: {data.concentration.top1_share_pct ?? "—"}% · Top 3: {data.concentration.top3_share_pct ?? "—"}%
                  </p>
                  <p className="text-xs text-slate-500 mt-1">{data.concentration.note}</p>
                </div>
              )}
              <p className="text-xs text-slate-500">{data.message}</p>
            </div>
          )}

          {tab === "compras" && (
            <PurchasesTable rows={data.institution_purchases || []} />
          )}

          {tab === "proveedores" && (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-slate-500">
                    <th className="py-2 pr-3">Proveedor</th>
                    <th className="py-2 pr-3">RPE</th>
                    <th className="py-2 pr-3">Adjudicaciones</th>
                    <th className="py-2 pr-3">Monto total</th>
                    <th className="py-2 pr-3">Última</th>
                    <th className="py-2">Participación</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.suppliers_ranking || []).map((s) => (
                    <tr key={s.supplier_name} className="border-b border-slate-100">
                      <td className="py-2 pr-3 font-medium">{s.supplier_name}</td>
                      <td className="py-2 pr-3">{s.supplier_rpe || "—"}</td>
                      <td className="py-2 pr-3">{s.awards_count}</td>
                      <td className="py-2 pr-3">{formatCurrency(Number(s.total_amount), s.currency)}</td>
                      <td className="py-2 pr-3">{formatDate(s.last_award_date)}</td>
                      <td className="py-2">
                        <span className="inline-flex items-center gap-1">
                          {s.share_pct}%
                          {s === data.suppliers_ranking?.[0] && <Trophy className="h-3.5 w-3.5 text-amber-500" />}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!data.suppliers_ranking?.length && (
                <p className="text-sm text-slate-500">Sin proveedores en la ventana.</p>
              )}
            </div>
          )}

          {tab === "productos" && (
            <div className="space-y-3">
              {(data.product_lines || []).map((pl) => (
                <div key={`${pl.line_number}-${pl.requested_description.slice(0, 24)}`} className="rounded-md border p-3">
                  <div className="text-sm font-medium">#{pl.line_number} · {pl.requested_description}</div>
                  {pl.last_purchase ? (
                    <div className="mt-2 grid gap-1 text-sm text-slate-700 md:grid-cols-2">
                      <div>
                        <Badge className={matchBadge(pl.match_class)}>{pl.match_class}</Badge>
                        {pl.similarity_pct != null && <span className="ml-2 text-xs">{pl.similarity_pct}% similitud</span>}
                      </div>
                      <div>{pl.last_purchase.supplier_name}</div>
                      <div>{formatDate(pl.last_purchase.award_date)}</div>
                      <div>
                        {pl.last_purchase.unit_price != null
                          ? `${formatCurrency(Number(pl.last_purchase.unit_price), pl.last_purchase.currency)} /u`
                          : "Sin precio unitario"}
                        {pl.last_purchase.quantity != null ? ` · qty ${pl.last_purchase.quantity}` : ""}
                      </div>
                      <div className="md:col-span-2 text-xs text-slate-500">{pl.last_purchase.process_code}</div>
                      <SourceLink row={pl.last_purchase} />
                    </div>
                  ) : (
                    <p className="mt-1 text-sm text-slate-500">Sin compra histórica comparable para esta línea.</p>
                  )}
                </div>
              ))}
            </div>
          )}

          {tab === "precios" && (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-slate-500">
                    <th className="py-2 pr-3">Fecha</th>
                    <th className="py-2 pr-3">Proveedor</th>
                    <th className="py-2 pr-3">Cantidad</th>
                    <th className="py-2 pr-3">Precio unitario</th>
                    <th className="py-2 pr-3">Monto</th>
                    <th className="py-2">Proceso</th>
                  </tr>
                </thead>
                <tbody>
                  {(prices?.points || []).map((p, idx) => (
                    <tr key={`${p.process_code}-${idx}`} className="border-b border-slate-100">
                      <td className="py-2 pr-3">{formatDate(p.award_date)}</td>
                      <td className="py-2 pr-3">{p.supplier_name || "—"}</td>
                      <td className="py-2 pr-3">{p.quantity ?? "—"}</td>
                      <td className="py-2 pr-3">{p.unit_price != null ? formatCurrency(Number(p.unit_price), prices?.currency) : "—"}</td>
                      <td className="py-2 pr-3">{p.awarded_amount != null ? formatCurrency(Number(p.awarded_amount), prices?.currency) : "—"}</td>
                      <td className="py-2">
                        {p.source_url ? (
                          <a href={p.source_url} target="_blank" rel="noreferrer" className="text-sky-700 hover:underline">{p.process_code}</a>
                        ) : (
                          p.process_code
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!prices?.points?.length && <p className="text-sm text-slate-500">Sin serie de precios.</p>}
            </div>
          )}

          {tab === "relacionados" && <PurchasesTable rows={data.related_processes || []} showInstitution />}
        </>
      )}
    </div>
  );
}

function PurchasesTable({
  rows,
  showInstitution = false,
}: {
  rows: DGCPHistoricalPurchaseRow[];
  showInstitution?: boolean;
}) {
  if (!rows.length) {
    return <p className="text-sm text-slate-500">Sin compras en esta vista.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b text-left text-slate-500">
            <th className="py-2 pr-3">Fecha</th>
            <th className="py-2 pr-3">Proceso</th>
            {showInstitution && <th className="py-2 pr-3">Institución</th>}
            <th className="py-2 pr-3">Descripción</th>
            <th className="py-2 pr-3">Proveedor</th>
            <th className="py-2 pr-3">RPE</th>
            <th className="py-2 pr-3">Monto</th>
            <th className="py-2 pr-3">Cant.</th>
            <th className="py-2 pr-3">P. unit.</th>
            <th className="py-2 pr-3">Match</th>
            <th className="py-2">Calidad</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.award_id} className="border-b border-slate-100 align-top">
              <td className="py-2 pr-3 whitespace-nowrap">{formatDate(r.award_date)}</td>
              <td className="py-2 pr-3">
                {r.source?.contract_url || r.source?.process_url ? (
                  <a
                    href={r.source.contract_url || r.source.process_url || undefined}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sky-700 hover:underline"
                  >
                    {r.process_code}
                  </a>
                ) : (
                  r.process_code
                )}
              </td>
              {showInstitution && <td className="py-2 pr-3 max-w-[140px]">{r.institution}</td>}
              <td className="py-2 pr-3 max-w-[220px]">{r.description || "—"}</td>
              <td className="py-2 pr-3">{r.supplier_name || "—"}</td>
              <td className="py-2 pr-3">{r.supplier_rpe || "—"}</td>
              <td className="py-2 pr-3 whitespace-nowrap">
                {r.awarded_amount != null ? formatCurrency(Number(r.awarded_amount), r.currency) : "—"}
              </td>
              <td className="py-2 pr-3">{r.quantity ?? "—"}</td>
              <td className="py-2 pr-3">
                {r.unit_price != null ? formatCurrency(Number(r.unit_price), r.currency) : "—"}
              </td>
              <td className="py-2 pr-3">
                <Badge className={matchBadge(r.match_class)}>{r.match_class}</Badge>
              </td>
              <td className="py-2">
                <Badge className={qualityBadge(r.data_quality)}>{r.data_quality}</Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
