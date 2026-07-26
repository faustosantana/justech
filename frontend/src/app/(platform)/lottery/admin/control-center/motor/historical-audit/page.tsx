"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiClient } from "@/lib/api";

type CaseRow = Record<string, unknown>;

const VERDICT_ES: Record<string, string> = {
  ACIERTO_EXACTO: "Acierto exacto",
  ACIERTO_ALTERNATIVA: "Acierto en alternativas",
  FALLO: "Sin coincidencia",
  PENDIENTE: "Pendiente de evaluar",
};

function todayIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function verdictLabel(v: unknown): string {
  const key = String(v || "");
  return VERDICT_ES[key] || key || "—";
}

export default function MotorHistoricalAuditPage() {
  const [dateFrom, setDateFrom] = useState("2015-01-01");
  const [dateTo, setDateTo] = useState(todayIso());
  const [minCases] = useState(10);
  const [verdictFilter, setVerdictFilter] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [auditId, setAuditId] = useState<string | null>(null);
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [cases, setCases] = useState<CaseRow[]>([]);
  const [selected, setSelected] = useState<CaseRow | null>(null);

  const metrics = useMemo(() => {
    const pop = (summary?.population_metrics as Record<string, unknown>) || {};
    const sample = (summary?.sample_metrics as Record<string, unknown>) || {};
    return { pop, sample };
  }, [summary]);

  const run = async (forceRerun = false) => {
    setBusy(true);
    setError(null);
    setSelected(null);
    try {
      const res = await apiClient.postLotteryNumericRelationsHistoricalAudit({
        use_precomputed: !forceRerun,
        force_rerun: forceRerun,
        date_from: dateFrom || null,
        date_to: dateTo || todayIso(),
        min_cases: minCases,
        include_hits_and_fails: true,
      });
      const id = String(res.audit_id);
      setAuditId(id);
      setSummary((res.summary as Record<string, unknown>) || null);
      const casesRes = await apiClient.getLotteryNumericRelationsHistoricalAuditCases(id, {
        page: 1,
        page_size: 50,
        verdict: verdictFilter || undefined,
      });
      setCases((casesRes.cases as CaseRow[]) || []);
      if (!(casesRes.cases as CaseRow[] | undefined)?.length) {
        setError(null);
      }
    } catch (err) {
      setSummary(null);
      setCases([]);
      setError(err instanceof ApiError ? err.message : "No fue posible ejecutar la auditoría. Intente nuevamente.");
    } finally {
      setBusy(false);
    }
  };

  const exportJson = () => {
    const blob = new Blob([JSON.stringify({ auditId, summary, cases }, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `auditoria-historica-${auditId || "export"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-slate-900">
            Auditoría histórica del motor
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Evalúa cómo se comportó la lógica manual sobre el histórico real. Solo lectura. No modifica el motor.
          </p>
        </div>
        <Button variant="outline" asChild>
          <Link href="/lottery/administracion">Volver a Administración</Link>
        </Button>
      </div>

      <Card className="border-blue-100">
        <CardHeader>
          <CardTitle className="text-base">Período a evaluar</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-xs text-slate-600">Desde</label>
            <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} disabled={busy} />
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-600">Hasta</label>
            <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} disabled={busy} />
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-600">Filtrar estado</label>
            <select
              className="h-10 rounded-md border px-2 text-sm"
              value={verdictFilter}
              onChange={(e) => setVerdictFilter(e.target.value)}
              disabled={busy}
            >
              <option value="">Todos</option>
              <option value="ACIERTO_EXACTO">Acierto exacto</option>
              <option value="ACIERTO_ALTERNATIVA">Acierto en alternativas</option>
              <option value="FALLO">Sin coincidencia</option>
              <option value="PENDIENTE">Pendiente de evaluar</option>
            </select>
          </div>
          <Button className="bg-blue-600 hover:bg-blue-700" disabled={busy} onClick={() => void run(false)}>
            {busy ? "Analizando información…" : "Ejecutar auditoría"}
          </Button>
          <Button variant="outline" disabled={busy} onClick={() => void run(true)}>
            Recalcular
          </Button>
          {auditId && (
            <Button variant="outline" disabled={busy} onClick={exportJson}>
              Exportar JSON
            </Button>
          )}
        </CardContent>
      </Card>

      {error && (
        <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}

      {summary && (
        <div className="grid gap-3 md:grid-cols-3">
          <Card className="border-blue-100">
            <CardContent className="pt-4 text-sm">
              <p className="text-slate-500">Casos evaluados</p>
              <p className="text-2xl font-semibold text-blue-900">
                {String(metrics.pop.n ?? metrics.sample.n ?? cases.length ?? "—")}
              </p>
            </CardContent>
          </Card>
          <Card className="border-blue-100">
            <CardContent className="pt-4 text-sm">
              <p className="text-slate-500">Rango consultado</p>
              <p className="font-medium">
                {dateFrom} → {dateTo}
              </p>
            </CardContent>
          </Card>
          <Card className="border-blue-100">
            <CardContent className="pt-4 text-sm">
              <p className="text-slate-500">Identificador</p>
              <p className="font-medium break-all">{auditId}</p>
            </CardContent>
          </Card>
        </div>
      )}

      {cases.length === 0 && summary && !error && (
        <p className="text-sm text-slate-600">No hay resultados para este período.</p>
      )}

      {cases.length > 0 && (
        <Card className="border-blue-100">
          <CardHeader>
            <CardTitle className="text-base">Resultados</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-slate-600">
                  <th className="py-2 pr-3">Fecha</th>
                  <th className="py-2 pr-3">Entrada</th>
                  <th className="py-2 pr-3">Estado</th>
                  <th className="py-2">Acción</th>
                </tr>
              </thead>
              <tbody>
                {cases.map((row, idx) => (
                  <tr key={idx} className="border-b border-slate-100">
                    <td className="py-2 pr-3">{String(row.date || row.case_date || "—")}</td>
                    <td className="py-2 pr-3">
                      {Array.isArray(row.numbers)
                        ? (row.numbers as unknown[]).join(", ")
                        : String(row.observed || row.input || "—")}
                    </td>
                    <td className="py-2 pr-3">{verdictLabel(row.verdict || row.status)}</td>
                    <td className="py-2">
                      <Button size="sm" variant="outline" onClick={() => setSelected(row)}>
                        Ver
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {selected && (
        <details open className="rounded-lg border p-4 text-sm">
          <summary className="cursor-pointer font-medium">Detalle del caso (administrativo)</summary>
          <pre className="mt-2 max-h-80 overflow-auto rounded bg-slate-50 p-3 text-xs">
            {JSON.stringify(selected, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}
