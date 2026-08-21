"use client";

import Link from "next/link";
import { ExternalLink, Loader2, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/dgcp";
import { institutionProfileHref } from "@/lib/dgcp-historical-keys";
import { cn } from "@/lib/utils";

type Tab = "resumen" | "adjudicaciones" | "instituciones" | "productos" | "evolucion";

const WINDOWS = [
  { label: "12m", value: 12 },
  { label: "24m", value: 24 },
  { label: "36m", value: 36 },
  { label: "Todo", value: 0 },
] as const;

export function DGCPSupplierProfileView({
  supplierKey,
  backHref,
}: {
  supplierKey: string;
  backHref?: string;
}) {
  const search = useSearchParams();
  const [windowMonths, setWindowMonths] = useState(Number(search.get("window_months") || 24));
  const institutionKey = search.get("institution_key") || undefined;
  const [tab, setTab] = useState<Tab>("resumen");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<Awaited<ReturnType<typeof apiClient.getDGCPSupplierProfile>> | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getDGCPSupplierProfile(supplierKey, {
        window_months: windowMonths,
        institution_key: institutionKey,
      });
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo cargar el perfil");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [supplierKey, windowMonths, institutionKey]);

  useEffect(() => {
    void load();
  }, [load]);

  const total = data?.totals_by_currency?.[0];

  const crumbs = useMemo(
    () => (
      <div className="flex flex-wrap items-center gap-2 text-sm text-slate-500">
        <Link href="/dgcp" className="hover:underline">
          Licitaciones
        </Link>
        <span>/</span>
        {backHref ? (
          <Link href={backHref} className="hover:underline">
            Histórico
          </Link>
        ) : (
          <span>Inteligencia</span>
        )}
        <span>/</span>
        <span className="text-slate-800">Proveedor</span>
      </div>
    ),
    [backHref],
  );

  return (
    <div className="space-y-4">
      {crumbs}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">{data?.identity.display_name || "Proveedor"}</h1>
          <div className="mt-1 flex flex-wrap gap-2 text-sm text-slate-600">
            <span>RNC: {data?.identity.rnc || "No disponible en la fuente"}</span>
            <span>·</span>
            <span>RPE: {data?.identity.rpe || "No disponible en la fuente"}</span>
            <span>·</span>
            <Badge variant="outline">{data?.identity.identity_confidence || "—"}</Badge>
            <Badge>{data?.data_quality?.overall || "—"}</Badge>
          </div>
          {data?.identity.note && <p className="mt-1 text-xs text-amber-700">{data.identity.note}</p>}
        </div>
        <div className="flex flex-wrap gap-2">
          {WINDOWS.map((w) => (
            <Button key={w.value} size="sm" variant={windowMonths === w.value ? "default" : "outline"} onClick={() => setWindowMonths(w.value)}>
              {w.label}
            </Button>
          ))}
          <Button size="sm" variant="outline" onClick={() => void load()} disabled={loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          </Button>
        </div>
      </div>

      {error && <p className="text-sm text-amber-800">{error}</p>}
      {loading && !data && (
        <p className="flex items-center gap-2 text-sm text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" /> Cargando perfil…
        </p>
      )}

      {data && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <Kpi title="Total adjudicado" value={total ? formatCurrency(Number(total.amount), total.currency) : "—"} hint={data.totals_by_currency.length > 1 ? "Hay múltiples monedas; se muestra la principal." : undefined} />
            <Kpi title="Adjudicaciones" value={String(data.awards_count)} />
            <Kpi title="Última adjudicación" value={formatDate(data.last_award_date)} />
            <Kpi title="Instituciones" value={String(data.institutions_count)} />
            <Kpi title="Categoría principal" value={data.primary_category || "—"} />
            <Kpi
              title="Últimos 12 meses"
              value={`${formatCurrency(Number(data.last_12m_amount || 0), data.last_12m_currency)} / ${data.last_12m_awards}`}
            />
          </div>

          <div className="rounded-md border bg-slate-50 p-3 text-sm space-y-1">
            {data.executive_summary?.map((p) => (
              <p key={p}>{p}</p>
            ))}
            {data.indexed_at && <p className="text-xs text-slate-500">Datos indexados: {formatDate(data.indexed_at)} · {data.latency_ms} ms{data.cache_hit ? " · cache" : ""}</p>}
          </div>

          {data.pair && (
            <div className="rounded-md border border-sky-200 bg-sky-50 p-3 text-sm">
              <div className="font-medium">Histórico con {data.pair.institution_name}</div>
              <p>
                {data.pair.process_count} procesos · {formatCurrency(Number(data.pair.total_amount), data.pair.currency)} ·{" "}
                {formatDate(data.pair.first_award_date)} → {formatDate(data.pair.last_award_date)}
              </p>
            </div>
          )}

          <div className="flex flex-wrap gap-1 border-b pb-1">
            {(
              [
                ["resumen", "Resumen"],
                ["adjudicaciones", "Adjudicaciones"],
                ["instituciones", "Instituciones"],
                ["productos", "Productos"],
                ["evolucion", "Evolución"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                className={cn("rounded-md px-3 py-1.5 text-sm", tab === id ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100")}
                onClick={() => setTab(id)}
              >
                {label}
              </button>
            ))}
          </div>

          {tab === "resumen" && (
            <div className="space-y-2 text-sm">
              <p>
                Diversificación: <strong>{data.diversification.level}</strong> · Top1 {data.diversification.top1_share_pct ?? "—"}% · Top3{" "}
                {data.diversification.top3_share_pct ?? "—"}%
              </p>
              <p className="text-xs text-slate-500">{data.diversification.note}</p>
              <p className="text-slate-600">{data.message}</p>
            </div>
          )}

          {tab === "adjudicaciones" && (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-slate-500">
                    <th className="py-2 pr-3">Fecha</th>
                    <th className="py-2 pr-3">Institución</th>
                    <th className="py-2 pr-3">Proceso</th>
                    <th className="py-2 pr-3">Descripción</th>
                    <th className="py-2 pr-3">Monto</th>
                    <th className="py-2">Fuente</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.awards || []).map((r) => (
                    <tr key={r.award_id} className="border-b border-slate-100 align-top">
                      <td className="py-2 pr-3 whitespace-nowrap">{formatDate(r.award_date)}</td>
                      <td className="py-2 pr-3">
                        <Link
                          href={institutionProfileHref({ name: r.institution, windowMonths })}
                          className="text-sky-700 hover:underline"
                        >
                          {r.institution}
                        </Link>
                      </td>
                      <td className="py-2 pr-3">{r.process_code}</td>
                      <td className="py-2 pr-3 max-w-[240px]">{r.description || "—"}</td>
                      <td className="py-2 pr-3 whitespace-nowrap">
                        {r.awarded_amount != null ? formatCurrency(Number(r.awarded_amount), r.currency) : "—"}
                      </td>
                      <td className="py-2">
                        {(r.source?.contract_url || r.source?.process_url) && (
                          <a href={r.source.contract_url || r.source.process_url || undefined} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sky-700">
                            Abrir <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {tab === "instituciones" && (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-slate-500">
                    <th className="py-2 pr-3">Institución</th>
                    <th className="py-2 pr-3">Adj.</th>
                    <th className="py-2 pr-3">Monto</th>
                    <th className="py-2 pr-3">Última</th>
                    <th className="py-2">%</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.institutions || []).map((r) => (
                    <tr key={r.stable_key} className="border-b border-slate-100">
                      <td className="py-2 pr-3">
                        <Link href={`/dgcp/intelligence/institution/${encodeURIComponent(r.stable_key)}?window_months=${windowMonths}`} className="text-sky-700 hover:underline">
                          {r.name}
                        </Link>
                      </td>
                      <td className="py-2 pr-3">{r.awards_count}</td>
                      <td className="py-2 pr-3">{formatCurrency(Number(r.total_amount), r.currency)}</td>
                      <td className="py-2 pr-3">{formatDate(r.last_award_date)}</td>
                      <td className="py-2">{r.share_pct}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {tab === "productos" && (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-slate-500">
                    <th className="py-2 pr-3">Descripción original</th>
                    <th className="py-2 pr-3">Cant.</th>
                    <th className="py-2 pr-3">P. unit.</th>
                    <th className="py-2 pr-3">Monto</th>
                    <th className="py-2 pr-3">Institución</th>
                    <th className="py-2">Fecha</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.products || []).map((p, i) => (
                    <tr key={`${p.process_code}-${i}`} className="border-b border-slate-100 align-top">
                      <td className="py-2 pr-3 max-w-[280px]">{p.description_original}</td>
                      <td className="py-2 pr-3">{p.quantity ?? "—"}</td>
                      <td className="py-2 pr-3">{p.unit_price != null ? formatCurrency(Number(p.unit_price), p.currency) : "—"}</td>
                      <td className="py-2 pr-3">{p.awarded_amount != null ? formatCurrency(Number(p.awarded_amount), p.currency) : "—"}</td>
                      <td className="py-2 pr-3">
                        {p.institution_key ? (
                          <Link href={`/dgcp/intelligence/institution/${encodeURIComponent(p.institution_key)}?window_months=${windowMonths}`} className="text-sky-700 hover:underline">
                            {p.institution}
                          </Link>
                        ) : (
                          p.institution
                        )}
                      </td>
                      <td className="py-2">{formatDate(p.award_date)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {tab === "evolucion" && (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-slate-500">
                    <th className="py-2 pr-3">Periodo</th>
                    <th className="py-2 pr-3">Adjudicaciones</th>
                    <th className="py-2">Monto</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.timeline || []).map((t) => (
                    <tr key={`${t.period}-${t.currency}`} className="border-b border-slate-100">
                      <td className="py-2 pr-3">{t.period}</td>
                      <td className="py-2 pr-3">{t.awards_count}</td>
                      <td className="py-2">{formatCurrency(Number(t.amount), t.currency)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-2 text-xs text-slate-500">Tendencia histórica descriptiva; no es predicción.</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Kpi({ title, value, hint }: { title: string; value: string; hint?: string }) {
  return (
    <Card>
      <CardHeader className="pb-1">
        <CardTitle className="text-sm font-medium text-slate-500">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-lg font-semibold leading-snug">{value}</div>
        {hint && <p className="mt-1 text-xs text-amber-700">{hint}</p>}
      </CardContent>
    </Card>
  );
}
