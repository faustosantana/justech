"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";

type ModelRow = {
  provider?: string;
  model?: string;
  requests?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
  estimated_cost_usd?: number;
  last_used_at?: string | null;
  avg_tokens_per_request?: number;
  avg_cost_per_request?: number;
  usage_pct?: number;
};

type ChartPoint = {
  date?: string;
  requests?: number;
  total_tokens?: number;
  estimated_cost_usd?: number;
  cumulative_cost_usd?: number;
  label?: string;
  provider?: string;
  model?: string;
  usage_pct?: number;
};

function money(n: unknown): string {
  const v = Number(n ?? 0);
  if (!Number.isFinite(v)) return "—";
  return `$${v.toFixed(v >= 1 ? 2 : 6)}`;
}

function num(n: unknown): string {
  const v = Number(n ?? 0);
  if (!Number.isFinite(v)) return "0";
  return v.toLocaleString("es-DO");
}

function BarList({
  items,
  valueKey,
  labelFn,
}: {
  items: ChartPoint[];
  valueKey: "estimated_cost_usd" | "total_tokens" | "requests" | "usage_pct";
  labelFn: (item: ChartPoint) => string;
}) {
  const max = Math.max(1, ...items.map((i) => Number(i[valueKey] ?? 0)));
  return (
    <ul className="space-y-2">
      {items.length === 0 ? (
        <li className="text-sm text-muted-foreground">Sin datos en el periodo.</li>
      ) : (
        items.map((item, idx) => {
          const value = Number(item[valueKey] ?? 0);
          const pct = Math.round((value / max) * 100);
          return (
            <li key={`${labelFn(item)}-${idx}`} className="space-y-1">
              <div className="flex items-center justify-between gap-2 text-xs">
                <span className="truncate font-medium">{labelFn(item)}</span>
                <span className="shrink-0 text-muted-foreground">
                  {valueKey === "estimated_cost_usd" ? money(value) : num(value)}
                  {valueKey === "usage_pct" ? "%" : ""}
                </span>
              </div>
              <div className="h-2 overflow-hidden rounded bg-muted">
                <div className="h-full rounded bg-primary/70" style={{ width: `${pct}%` }} />
              </div>
            </li>
          );
        })
      )}
    </ul>
  );
}

export default function LotteryAIConsumoPage() {
  const [period, setPeriod] = useState("month");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [userId, setUserId] = useState("");
  const [lotteryKey, setLotteryKey] = useState("");
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getLotteryAIConsumo({
        period: period === "range" ? "range" : period,
        date_from: period === "range" && dateFrom ? dateFrom : undefined,
        date_to: period === "range" && dateTo ? dateTo : undefined,
        user_id: userId || undefined,
        lottery_key: lotteryKey || undefined,
      });
      setData(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar el consumo de IA");
    } finally {
      setLoading(false);
    }
  }, [period, dateFrom, dateTo, userId, lotteryKey]);

  useEffect(() => {
    void load();
  }, [load]);

  const summary = (data?.summary ?? {}) as Record<string, unknown>;
  const active = (data?.active_model ?? {}) as Record<string, unknown>;
  const byModel = useMemo(() => (data?.by_model as ModelRow[]) ?? [], [data]);
  const charts = (data?.charts ?? {}) as Record<string, ChartPoint[]>;
  const filterOpts = (data?.filter_options ?? {}) as {
    users?: { id: string; label: string }[];
    lotteries?: { key: string; label: string }[];
  };

  const periodButtons = [
    { id: "today", label: "Hoy" },
    { id: "week", label: "Semana" },
    { id: "month", label: "Mes" },
    { id: "range", label: "Rango" },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Consumo de IA</h2>
          <p className="text-sm text-muted-foreground">
            Tokens reales por proveedor/modelo y costos estimados (histórico en base de datos).
          </p>
        </div>
        <Button size="sm" variant="outline" onClick={() => void load()} disabled={loading}>
          Actualizar
        </Button>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Filtros</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          <div className="flex flex-wrap gap-1.5">
            {periodButtons.map((b) => (
              <button
                key={b.id}
                type="button"
                onClick={() => setPeriod(b.id)}
                className={`rounded-md px-2.5 py-1.5 text-xs ${
                  period === b.id
                    ? "bg-primary/10 font-medium text-primary"
                    : "bg-muted/40 text-foreground/80 hover:bg-muted"
                }`}
              >
                {b.label}
              </button>
            ))}
          </div>
          {period === "range" ? (
            <>
              <label className="text-xs text-muted-foreground">
                Desde
                <input
                  type="date"
                  className="mt-1 block rounded border border-border bg-background px-2 py-1 text-sm"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                />
              </label>
              <label className="text-xs text-muted-foreground">
                Hasta
                <input
                  type="date"
                  className="mt-1 block rounded border border-border bg-background px-2 py-1 text-sm"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                />
              </label>
            </>
          ) : null}
          <label className="text-xs text-muted-foreground">
            Usuario
            <select
              className="mt-1 block min-w-[12rem] rounded border border-border bg-background px-2 py-1 text-sm"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
            >
              <option value="">Todos</option>
              {(filterOpts.users ?? []).map((u) => (
                <option key={u.id} value={u.id}>
                  {u.label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-muted-foreground">
            Licitación / Lotería
            <select
              className="mt-1 block min-w-[12rem] rounded border border-border bg-background px-2 py-1 text-sm"
              value={lotteryKey}
              onChange={(e) => setLotteryKey(e.target.value)}
            >
              <option value="">Todas</option>
              {(filterOpts.lotteries ?? []).map((l) => (
                <option key={l.key} value={l.key}>
                  {l.label}
                </option>
              ))}
            </select>
          </label>
        </CardContent>
      </Card>

      {loading ? <p className="text-sm text-muted-foreground">Cargando…</p> : null}
      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {!loading && !error && data ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="pb-1">
                <CardTitle className="text-xs font-medium text-muted-foreground">Modelo activo</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm font-semibold">
                  {String(active.provider ?? "—")} / {String(active.model ?? "—")}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-1">
                <CardTitle className="text-xs font-medium text-muted-foreground">Costo total</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm font-semibold">{money(summary.estimated_cost_usd)}</p>
                <p className="text-xs text-muted-foreground">{num(summary.requests)} solicitudes</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-1">
                <CardTitle className="text-xs font-medium text-muted-foreground">
                  Promedio / licitación
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm font-semibold">{money(summary.avg_cost_per_lottery)}</p>
                <p className="text-xs text-muted-foreground">
                  {num(summary.unique_lotteries)} loterías
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-1">
                <CardTitle className="text-xs font-medium text-muted-foreground">
                  Promedio / conversación
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm font-semibold">{money(summary.avg_cost_per_conversation)}</p>
                <p className="text-xs text-muted-foreground">
                  {num(summary.unique_conversations)} conversaciones
                </p>
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-3 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Consumo diario</CardTitle>
              </CardHeader>
              <CardContent>
                <BarList
                  items={charts.daily ?? []}
                  valueKey="total_tokens"
                  labelFn={(i) => String(i.date ?? "")}
                />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Costos acumulados</CardTitle>
              </CardHeader>
              <CardContent>
                <BarList
                  items={(charts.cumulative_cost ?? []).map((i) => ({
                    ...i,
                    estimated_cost_usd: Number(i.cumulative_cost_usd ?? i.estimated_cost_usd ?? 0),
                  }))}
                  valueKey="estimated_cost_usd"
                  labelFn={(i) => String(i.date ?? "")}
                />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Consumo por modelo</CardTitle>
              </CardHeader>
              <CardContent>
                <BarList
                  items={charts.by_model ?? []}
                  valueKey="usage_pct"
                  labelFn={(i) => String(i.label ?? `${i.provider}/${i.model}`)}
                />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Consumo por proveedor</CardTitle>
              </CardHeader>
              <CardContent>
                <BarList
                  items={charts.by_provider ?? []}
                  valueKey="usage_pct"
                  labelFn={(i) => String(i.provider ?? "unknown")}
                />
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Detalle por proveedor / modelo</CardTitle>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <table className="w-full min-w-[56rem] text-left text-sm">
                <thead className="border-b border-border text-xs text-muted-foreground">
                  <tr>
                    <th className="px-2 py-2 font-medium">Proveedor</th>
                    <th className="px-2 py-2 font-medium">Modelo</th>
                    <th className="px-2 py-2 font-medium">Solicitudes</th>
                    <th className="px-2 py-2 font-medium">Tokens in</th>
                    <th className="px-2 py-2 font-medium">Tokens out</th>
                    <th className="px-2 py-2 font-medium">Total</th>
                    <th className="px-2 py-2 font-medium">Costo est.</th>
                    <th className="px-2 py-2 font-medium">Último uso</th>
                    <th className="px-2 py-2 font-medium">Prom. / consulta</th>
                    <th className="px-2 py-2 font-medium">% uso</th>
                  </tr>
                </thead>
                <tbody>
                  {byModel.length === 0 ? (
                    <tr>
                      <td colSpan={10} className="px-2 py-4 text-muted-foreground">
                        Sin registros de uso en el periodo. Los tokens se guardan en cada
                        consulta real al chat.
                      </td>
                    </tr>
                  ) : (
                    byModel.map((row) => (
                      <tr
                        key={`${row.provider}-${row.model}`}
                        className="border-b border-border/60"
                      >
                        <td className="px-2 py-2 capitalize">{row.provider}</td>
                        <td className="px-2 py-2 font-medium">{row.model}</td>
                        <td className="px-2 py-2">{num(row.requests)}</td>
                        <td className="px-2 py-2">{num(row.prompt_tokens)}</td>
                        <td className="px-2 py-2">{num(row.completion_tokens)}</td>
                        <td className="px-2 py-2">{num(row.total_tokens)}</td>
                        <td className="px-2 py-2">{money(row.estimated_cost_usd)}</td>
                        <td className="px-2 py-2 text-xs text-muted-foreground">
                          {row.last_used_at
                            ? new Date(row.last_used_at).toLocaleString("es-DO")
                            : "—"}
                        </td>
                        <td className="px-2 py-2">
                          {num(row.avg_tokens_per_request)} tok / {money(row.avg_cost_per_request)}
                        </td>
                        <td className="px-2 py-2">{Number(row.usage_pct ?? 0).toFixed(1)}%</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
              {data.note ? (
                <p className="mt-3 text-xs text-muted-foreground">{String(data.note)}</p>
              ) : null}
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}
