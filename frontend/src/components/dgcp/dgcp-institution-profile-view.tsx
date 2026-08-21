"use client";

import Link from "next/link";
import { ExternalLink, Loader2, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/dgcp";
import { supplierProfileHref } from "@/lib/dgcp-historical-keys";
import { cn } from "@/lib/utils";

type Tab = "resumen" | "compras" | "proveedores" | "productos" | "precios" | "procesos";

const WINDOWS = [
  { label: "12m", value: 12 },
  { label: "24m", value: 24 },
  { label: "36m", value: 36 },
  { label: "Todo", value: 0 },
] as const;

export function DGCPInstitutionProfileView({
  institutionKey,
  backHref,
}: {
  institutionKey: string;
  backHref?: string;
}) {
  const search = useSearchParams();
  const [windowMonths, setWindowMonths] = useState(Number(search.get("window_months") || 24));
  const [tab, setTab] = useState<Tab>("resumen");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<Awaited<ReturnType<typeof apiClient.getDGCPInstitutionProfile>> | null>(null);
  const [compareKeys, setCompareKeys] = useState<string[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getDGCPInstitutionProfile(institutionKey, { window_months: windowMonths });
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo cargar el perfil");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [institutionKey, windowMonths]);

  useEffect(() => {
    void load();
  }, [load]);

  const total = data?.totals_by_currency?.[0];

  return (
    <div className="space-y-4">
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
        <span className="text-slate-800">Institución</span>
      </div>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">{data?.identity.display_name || "Institución"}</h1>
          <div className="mt-1 flex flex-wrap gap-2 text-sm text-slate-600">
            <span>Código: {data?.identity.institution_code || "No disponible en la fuente"}</span>
            <Badge>{data?.data_quality?.overall || "—"}</Badge>
            <Badge variant="outline">{data?.identity.identity_confidence || "—"}</Badge>
          </div>
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
            <Kpi title="Última compra" value={`${formatDate(data.last_award_date)}${data.last_purchase?.awarded_amount != null ? ` · ${formatCurrency(Number(data.last_purchase.awarded_amount), data.last_purchase.currency)}` : ""}`} />
            <Kpi
              title="Último proveedor"
              value={data.last_supplier_name || "—"}
              link={
                data.last_supplier_key
                  ? `/dgcp/intelligence/supplier/${encodeURIComponent(data.last_supplier_key)}?window_months=${windowMonths}&institution_key=${encodeURIComponent(data.identity.stable_key)}`
                  : undefined
              }
            />
            <Kpi title="Total adjudicado" value={total ? formatCurrency(Number(total.amount), total.currency) : "—"} hint={data.totals_by_currency.length > 1 ? "Múltiples monedas; se muestra la principal." : undefined} />
            <Kpi title="Proveedores" value={String(data.suppliers_count)} />
            <Kpi title="Procesos / adjudicaciones" value={`${data.process_count} / ${data.awards_count}`} />
            <Kpi title="Categoría más comprada" value={data.primary_category || "—"} />
          </div>

          <div className="rounded-md border bg-slate-50 p-3 text-sm space-y-1">
            {data.executive_summary?.map((p) => (
              <p key={p}>{p}</p>
            ))}
            {data.frequency?.available && <p className="text-slate-700">{data.frequency.summary}</p>}
            {data.frequency?.temporal_pattern && <p className="text-slate-600">{data.frequency.temporal_pattern}</p>}
            {data.indexed_at && <p className="text-xs text-slate-500">Datos indexados: {formatDate(data.indexed_at)} · {data.latency_ms} ms{data.cache_hit ? " · cache" : ""}</p>}
          </div>

          <div className="flex flex-wrap gap-1 border-b pb-1">
            {(
              [
                ["resumen", "Resumen"],
                ["compras", "Compras"],
                ["proveedores", "Proveedores"],
                ["productos", "Productos"],
                ["precios", "Precios"],
                ["procesos", "Procesos"],
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
                Concentración: <strong>{data.concentration.level}</strong> · Top1 {data.concentration.top1_share_pct ?? "—"}% · Top3{" "}
                {data.concentration.top3_share_pct ?? "—"}%
              </p>
              <p className="text-xs text-slate-500">{data.concentration.note}</p>
              {(data.modalities || []).slice(0, 6).map((m) => (
                <p key={m.modality}>
                  {m.modality}: {m.process_count} procesos · {formatCurrency(Number(m.total_amount), total?.currency || "DOP")}
                </p>
              ))}
            </div>
          )}

          {tab === "compras" && (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-slate-500">
                    <th className="py-2 pr-3">Fecha</th>
                    <th className="py-2 pr-3">Proceso</th>
                    <th className="py-2 pr-3">Descripción</th>
                    <th className="py-2 pr-3">Proveedor</th>
                    <th className="py-2 pr-3">Monto</th>
                    <th className="py-2">Fuente</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.awards || []).map((r) => (
                    <tr key={r.award_id} className="border-b border-slate-100 align-top">
                      <td className="py-2 pr-3 whitespace-nowrap">{formatDate(r.award_date)}</td>
                      <td className="py-2 pr-3">{r.process_code}</td>
                      <td className="py-2 pr-3 max-w-[220px]">{r.description || "—"}</td>
                      <td className="py-2 pr-3">
                        <Link
                          href={supplierProfileHref({
                            name: r.supplier_name,
                            rpe: r.supplier_rpe,
                            rnc: r.supplier_rnc,
                            windowMonths,
                          })}
                          className="text-sky-700 hover:underline"
                        >
                          {r.supplier_name || "—"}
                        </Link>
                      </td>
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

          {tab === "proveedores" && (
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2">
                <Button size="sm" disabled={compareKeys.length < 1 || compareKeys.length > 3} asChild={compareKeys.length >= 1}>
                  {compareKeys.length >= 1 && compareKeys.length <= 3 ? (
                    <Link
                      href={`/dgcp/intelligence/compare?keys=${compareKeys.map(encodeURIComponent).join(",")}&window_months=${windowMonths}&institution_key=${encodeURIComponent(data.identity.stable_key)}`}
                    >
                      Comparar en esta institución ({compareKeys.length}/3)
                    </Link>
                  ) : (
                    <span>Comparar en esta institución</span>
                  )}
                </Button>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-slate-500">
                      <th className="py-2 pr-2 w-8" />
                      <th className="py-2 pr-3">Proveedor</th>
                      <th className="py-2 pr-3">RPE</th>
                      <th className="py-2 pr-3">Adj.</th>
                      <th className="py-2 pr-3">Monto</th>
                      <th className="py-2 pr-3">Última</th>
                      <th className="py-2">%</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.suppliers || []).map((s) => {
                      const checked = compareKeys.includes(s.stable_key);
                      return (
                        <tr key={s.stable_key} className="border-b border-slate-100">
                          <td className="py-2 pr-2">
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() => {
                                if (checked) setCompareKeys(compareKeys.filter((k) => k !== s.stable_key));
                                else if (compareKeys.length < 3) setCompareKeys([...compareKeys, s.stable_key]);
                              }}
                            />
                          </td>
                          <td className="py-2 pr-3">
                            <Link
                              href={`/dgcp/intelligence/supplier/${encodeURIComponent(s.stable_key)}?window_months=${windowMonths}&institution_key=${encodeURIComponent(data.identity.stable_key)}`}
                              className="text-sky-700 hover:underline"
                            >
                              {s.name}
                            </Link>
                          </td>
                          <td className="py-2 pr-3">{s.rpe || "—"}</td>
                          <td className="py-2 pr-3">{s.awards_count}</td>
                          <td className="py-2 pr-3">{formatCurrency(Number(s.total_amount), s.currency)}</td>
                          <td className="py-2 pr-3">{formatDate(s.last_award_date)}</td>
                          <td className="py-2">{s.share_pct}%</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {tab === "productos" && (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-slate-500">
                    <th className="py-2 pr-3">Descripción</th>
                    <th className="py-2 pr-3">Cant.</th>
                    <th className="py-2 pr-3">P. unit.</th>
                    <th className="py-2 pr-3">Proveedor</th>
                    <th className="py-2">Fecha</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.products || []).map((p, i) => (
                    <tr key={`${p.process_code}-${i}`} className="border-b border-slate-100 align-top">
                      <td className="py-2 pr-3 max-w-[280px]">{p.description_original}</td>
                      <td className="py-2 pr-3">{p.quantity ?? "—"}</td>
                      <td className="py-2 pr-3">{p.unit_price != null ? formatCurrency(Number(p.unit_price), p.currency) : "—"}</td>
                      <td className="py-2 pr-3">
                        {p.supplier_key ? (
                          <Link href={`/dgcp/intelligence/supplier/${encodeURIComponent(p.supplier_key)}?window_months=${windowMonths}`} className="text-sky-700 hover:underline">
                            {p.supplier_name}
                          </Link>
                        ) : (
                          p.supplier_name
                        )}
                      </td>
                      <td className="py-2">{formatDate(p.award_date)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {tab === "precios" && (
            <div className="overflow-x-auto">
              {data.price_history?.available ? (
                <>
                  <p className="mb-2 text-sm">
                    Último {formatCurrency(Number(data.price_history.last_unit_price), data.price_history.currency)} · Promedio{" "}
                    {formatCurrency(Number(data.price_history.avg_unit_price), data.price_history.currency)} · Rango{" "}
                    {formatCurrency(Number(data.price_history.min_unit_price), data.price_history.currency)}–
                    {formatCurrency(Number(data.price_history.max_unit_price), data.price_history.currency)}
                  </p>
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-slate-500">
                        <th className="py-2 pr-3">Fecha</th>
                        <th className="py-2 pr-3">Proveedor</th>
                        <th className="py-2 pr-3">Cant.</th>
                        <th className="py-2 pr-3">P. unit.</th>
                        <th className="py-2">Proceso</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(data.price_history.points || []).map((p, i) => (
                        <tr key={`${p.process_code}-${i}`} className="border-b border-slate-100">
                          <td className="py-2 pr-3">{formatDate(p.award_date)}</td>
                          <td className="py-2 pr-3">{p.supplier_name}</td>
                          <td className="py-2 pr-3">{p.quantity ?? "—"}</td>
                          <td className="py-2 pr-3">{p.unit_price != null ? formatCurrency(Number(p.unit_price), data.price_history.currency) : "—"}</td>
                          <td className="py-2">{p.process_code}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              ) : (
                <p className="text-sm text-slate-500">Sin precios unitarios confiables.</p>
              )}
            </div>
          )}

          {tab === "procesos" && (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-slate-500">
                    <th className="py-2 pr-3">Fecha</th>
                    <th className="py-2 pr-3">Proceso</th>
                    <th className="py-2 pr-3">Proveedor</th>
                    <th className="py-2 pr-3">Monto</th>
                    <th className="py-2">Modalidad</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.awards || []).slice(0, 40).map((r) => (
                    <tr key={r.award_id} className="border-b border-slate-100">
                      <td className="py-2 pr-3">{formatDate(r.award_date)}</td>
                      <td className="py-2 pr-3">
                        {(r.source?.contract_url || r.source?.process_url) ? (
                          <a href={r.source.contract_url || r.source.process_url || undefined} target="_blank" rel="noreferrer" className="text-sky-700 hover:underline">
                            {r.process_code}
                          </a>
                        ) : (
                          r.process_code
                        )}
                      </td>
                      <td className="py-2 pr-3">{r.supplier_name}</td>
                      <td className="py-2 pr-3">{r.awarded_amount != null ? formatCurrency(Number(r.awarded_amount), r.currency) : "—"}</td>
                      <td className="py-2">{r.modality || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Kpi({ title, value, hint, link }: { title: string; value: string; hint?: string; link?: string }) {
  return (
    <Card>
      <CardHeader className="pb-1">
        <CardTitle className="text-sm font-medium text-slate-500">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {link ? (
          <Link href={link} className="text-lg font-semibold leading-snug text-sky-800 hover:underline">
            {value}
          </Link>
        ) : (
          <div className="text-lg font-semibold leading-snug">{value}</div>
        )}
        {hint && <p className="mt-1 text-xs text-amber-700">{hint}</p>}
      </CardContent>
    </Card>
  );
}
