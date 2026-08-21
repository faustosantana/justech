"use client";

import Link from "next/link";
import { Loader2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/dgcp";

const MAX = 3;

export function DGCPSupplierCompareView() {
  const search = useSearchParams();
  const initialKeys = useMemo(() => {
    const raw = search.get("keys") || "";
    return raw
      .split(",")
      .map((k) => decodeURIComponent(k.trim()))
      .filter(Boolean)
      .slice(0, MAX);
  }, [search]);
  const institutionKey = search.get("institution_key") || undefined;
  const [keys, setKeys] = useState<string[]>(initialKeys);
  const [input, setInput] = useState("");
  const [windowMonths, setWindowMonths] = useState(Number(search.get("window_months") || 24));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<Awaited<ReturnType<typeof apiClient.compareDGCPSuppliers>> | null>(null);

  const load = useCallback(async () => {
    if (!keys.length) {
      setData(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.compareDGCPSuppliers(keys.slice(0, MAX), windowMonths, institutionKey);
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo comparar");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [keys, windowMonths, institutionKey]);

  useEffect(() => {
    void load();
  }, [load]);

  const addKey = () => {
    const k = input.trim();
    if (!k) return;
    if (keys.length >= MAX) {
      setError(`Máximo ${MAX} proveedores`);
      return;
    }
    if (keys.includes(k)) return;
    setKeys([...keys, k]);
    setInput("");
  };

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4 md:p-6">
      <div className="text-sm text-slate-500">
        <Link href="/dgcp" className="hover:underline">
          Licitaciones
        </Link>
        <span> / Comparar proveedores</span>
      </div>
      <h1 className="text-2xl font-semibold text-slate-900">Comparar proveedores</h1>
      <p className="text-sm text-slate-600">
        Comparación descriptiva de hasta {MAX} proveedores del índice histórico. No es un score ni recomendación.
      </p>
      {institutionKey && (
        <p className="text-sm text-sky-800">Contexto institución: {institutionKey}</p>
      )}

      <div className="flex flex-wrap items-end gap-2">
        <div className="min-w-[220px] flex-1">
          <label className="text-xs text-slate-500">Clave (rpe-… / rnc-…)</label>
          <input
            className="mt-1 w-full rounded border px-3 py-2 text-sm"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="rpe-56446"
            onKeyDown={(e) => e.key === "Enter" && addKey()}
          />
        </div>
        <Button type="button" onClick={addKey} disabled={keys.length >= MAX}>
          Agregar
        </Button>
        {[12, 24, 36, 0].map((w) => (
          <Button key={w} size="sm" variant={windowMonths === w ? "default" : "outline"} onClick={() => setWindowMonths(w)}>
            {w === 0 ? "Todo" : `${w}m`}
          </Button>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        {keys.map((k) => (
          <button
            key={k}
            type="button"
            className="rounded-full border px-3 py-1 text-xs hover:bg-slate-50"
            onClick={() => setKeys(keys.filter((x) => x !== k))}
          >
            {k} ×
          </button>
        ))}
      </div>

      {error && <p className="text-sm text-amber-800">{error}</p>}
      {loading && (
        <p className="flex items-center gap-2 text-sm text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" /> Comparando…
        </p>
      )}

      {data && (
        <>
          <div className="overflow-x-auto rounded border">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b bg-slate-50 text-left text-slate-500">
                  <th className="p-2">Métrica</th>
                  {data.rows.map((r) => (
                    <th key={r.identity.stable_key} className="p-2">
                      <Link
                        href={`/dgcp/intelligence/supplier/${encodeURIComponent(r.identity.stable_key)}?window_months=${windowMonths}${
                          institutionKey ? `&institution_key=${encodeURIComponent(institutionKey)}` : ""
                        }`}
                        className="text-sky-700 hover:underline"
                      >
                        {r.identity.display_name}
                      </Link>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(
                  [
                    ["RNC / RPE", (r) => `${r.identity.rnc || "—"} / ${r.identity.rpe || "—"}`],
                    ["Total adjudicado", (r) => formatCurrency(Number(r.total_amount || 0), r.currency)],
                    ["Adjudicaciones", (r) => String(r.awards_count)],
                    ["Última adjudicación", (r) => formatDate(r.last_award_date)],
                    ["Instituciones distintas", (r) => String(r.institutions_count)],
                    ["Categorías", (r) => String(r.categories_count)],
                    ["Monto 12m", (r) => (r.last_12m_amount != null ? formatCurrency(Number(r.last_12m_amount), r.currency) : "—")],
                    ["Monto 24m", (r) => (r.last_24m_amount != null ? formatCurrency(Number(r.last_24m_amount), r.currency) : "—")],
                    ["Institución principal", (r) => r.primary_institution || "—"],
                    ["Categoría principal", (r) => r.primary_category || "—"],
                    ...(institutionKey
                      ? ([
                          ["Adj. con institución", (r) => String(r.institution_awards ?? "—")],
                          [
                            "Monto con institución",
                            (r) =>
                              r.institution_amount != null
                                ? formatCurrency(Number(r.institution_amount), r.currency)
                                : "—",
                          ],
                          ["Última con institución", (r) => formatDate(r.institution_last_award)],
                        ] as const)
                      : []),
                  ] as const
                ).map(([label, fn]) => (
                  <tr key={label} className="border-b border-slate-100">
                    <td className="p-2 font-medium text-slate-600">{label}</td>
                    {data.rows.map((r) => (
                      <td key={`${label}-${r.identity.stable_key}`} className="p-2">
                        {fn(r)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-slate-500">{data.note}</p>

          <div className="grid gap-4 md:grid-cols-3">
            {data.rows.map((r) => {
              const recent = (data.recent_awards || {})[r.identity.stable_key] || [];
              return (
                <div key={r.identity.stable_key} className="rounded border p-3">
                  <div className="mb-2 text-sm font-medium">{r.identity.display_name}</div>
                  <ul className="space-y-2 text-xs text-slate-600">
                    {recent.length === 0 && <li>Sin adjudicaciones recientes</li>}
                    {recent.map((a: { process_code?: string; award_date?: string; awarded_amount?: number | string }, i: number) => (
                      <li key={`${a.process_code}-${i}`}>
                        {formatDate(a.award_date)} · {a.process_code} ·{" "}
                        {a.awarded_amount != null ? formatCurrency(Number(a.awarded_amount), r.currency) : "—"}
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
