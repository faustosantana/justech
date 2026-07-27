"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { IntelligentAnalysisReport } from "@/lib/lottery-intelligent-report";

function pad2(n: number | string | null | undefined): string {
  if (n == null) return "—";
  const s = String(n);
  return s.length <= 2 ? s.padStart(2, "0") : s;
}

function EvidenceBadge({ level }: { level?: string }) {
  const label = level || "—";
  const tone =
    label.toLowerCase().includes("muy")
      ? "bg-emerald-100 text-emerald-900 border-emerald-300"
      : label.toLowerCase().includes("alta")
        ? "bg-sky-100 text-sky-900 border-sky-300"
        : label.toLowerCase().includes("moder")
          ? "bg-blue-50 text-blue-900 border-blue-200"
          : label.toLowerCase().includes("limit")
            ? "bg-amber-50 text-amber-900 border-amber-200"
            : "bg-slate-100 text-slate-800 border-slate-200";
  return (
    <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${tone}`}>
      {label}
    </span>
  );
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-blue-100 bg-white px-3 py-3 text-center shadow-sm">
      <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-blue-900">{value}</p>
    </div>
  );
}

function YesNo({ value }: { value: boolean }) {
  return (
    <span className={value ? "font-medium text-emerald-700" : "text-slate-500"}>
      {value ? "Sí" : "No"}
    </span>
  );
}

function RouteStack({ from, via, to }: { from?: number; via?: string; to?: number }) {
  return (
    <div className="flex flex-col items-center gap-1 rounded-xl border border-blue-100 bg-gradient-to-b from-blue-50 to-white px-4 py-3">
      <span className="text-2xl font-bold tabular-nums text-blue-900">{pad2(from)}</span>
      <span className="text-slate-400">↓</span>
      <span className="rounded-full bg-blue-600 px-2.5 py-0.5 text-[11px] font-semibold text-white">
        {via || "Ruta"}
      </span>
      <span className="text-slate-400">↓</span>
      <span className="text-2xl font-bold tabular-nums text-emerald-700">{pad2(to)}</span>
    </div>
  );
}

export function LotteryIntelligentReport({
  report,
  onAskChat,
  relationsHref,
}: {
  report: IntelligentAnalysisReport;
  onAskChat?: () => void;
  relationsHref?: string;
}) {
  const [showCases, setShowCases] = useState(false);
  const [showMoreCases, setShowMoreCases] = useState(false);
  const primary = report.primary_candidate;
  const observed = report.observed_numbers?.[0];
  const cases = report.recent_equivalent_cases || [];
  const visibleCases = showMoreCases ? cases : cases.slice(0, 5);

  const chatHref = useMemo(() => {
    const params = new URLSearchParams();
    const n = observed ?? "";
    params.set("q", primary != null ? `¿Por qué el ${primary}?` : `Explícame el análisis del ${n}.`);
    if (n !== "") params.set("number", String(n));
    if (report.analysis_date) params.set("date", String(report.analysis_date).slice(0, 10));
    if (report.origin_lottery) params.set("lottery", report.origin_lottery);
    if (primary != null) params.set("highlight", String(primary));
    if (report.confirmer?.number != null) params.set("with", String(report.confirmer.number));
    return `/lottery/chat?${params.toString()}`;
  }, [observed, primary, report]);

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-blue-100 bg-white p-5 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-600">
          Informe inteligente del análisis
        </p>
        <h2 className="mt-2 text-2xl font-semibold text-slate-900">
          Análisis del número {observed != null ? pad2(observed) : "—"}
        </h2>
        <div className="mt-2 space-y-1 text-sm text-slate-600">
          {report.analysis_date_label && <p>{report.analysis_date_label}</p>}
          {(report.origin_lottery || report.origin_position) && (
            <p>
              {[report.origin_lottery, report.origin_position].filter(Boolean).join(" · ")}
            </p>
          )}
        </div>
        {report.confirmer?.number != null && (
          <div className="mt-4 rounded-xl border border-emerald-100 bg-emerald-50/60 px-4 py-3 text-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-800">
              Confirmación encontrada
            </p>
            <p className="mt-1 font-medium text-emerald-950">
              {pad2(report.confirmer.number)}
              {report.confirmer.lottery ? ` · ${report.confirmer.lottery}` : ""}
              {report.confirmer.position ? ` · ${report.confirmer.position}` : ""}
            </p>
          </div>
        )}
      </div>

      <Card className="overflow-hidden border-blue-200 shadow-md">
        <CardContent className="bg-gradient-to-br from-blue-700 via-blue-600 to-sky-500 px-6 py-7 text-white">
          <p className="text-sm font-medium text-blue-100">Número más fortalecido</p>
          <p className="mt-2 text-6xl font-bold tabular-nums tracking-tight">
            {primary != null ? pad2(primary) : "—"}
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <span className="text-sm text-blue-100">Nivel de evidencia</span>
            <EvidenceBadge level={report.evidence_level_label} />
          </div>
          {report.brief_conclusion && (
            <p className="mt-4 max-w-3xl text-sm leading-relaxed text-blue-50">
              {report.brief_conclusion}
            </p>
          )}
          <p className="mt-3 max-w-3xl text-[11px] leading-relaxed text-blue-100/90">
            {report.evidence_level_help}
          </p>
        </CardContent>
      </Card>

      {(report.special_notes || []).length > 0 && (
        <div className="space-y-2">
          {report.special_notes!.map((note) => (
            <p
              key={note}
              className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900"
            >
              {note}
            </p>
          ))}
        </div>
      )}

      {(report.why_evidence || []).length > 0 && primary != null && (
        <Card className="border-blue-100">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-blue-900">¿Por qué el {pad2(primary)}?</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm text-slate-700">
              {report.why_evidence!.map((item) => (
                <li key={item} className="flex gap-2">
                  <span className="mt-0.5 text-emerald-600">✓</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {report.historical_metrics && (
        <Card className="border-blue-100">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-blue-900">Comportamiento histórico</CardTitle>
            {report.historical_sample_quality?.label && (
              <p className="text-xs text-slate-500">{report.historical_sample_quality.label}</p>
            )}
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
              <MetricCard label="Casos equivalentes" value={report.historical_metrics.exact_cases ?? 0} />
              <MetricCard
                label={`Aparición exacta${primary != null ? ` del ${pad2(primary)}` : ""}`}
                value={report.historical_metrics.exact_hits ?? 0}
              />
              <MetricCard label="Familia de Tabla 1" value={report.historical_metrics.t1_family_hits ?? 0} />
              <MetricCard label="Hasta D+1" value={report.historical_metrics.d1_hits ?? 0} />
              <MetricCard label="Hasta D+3" value={report.historical_metrics.d3_hits ?? 0} />
              <MetricCard label="Hasta D+7" value={report.historical_metrics.d7_hits ?? 0} />
            </div>
            <p className="text-xs font-medium text-slate-600">
              {report.historical_metrics.behavior_label}
            </p>
            <p className="text-xs text-slate-500">{report.historical_metrics.behavior_note}</p>
          </CardContent>
        </Card>
      )}

      {(report.candidate_comparison || []).length > 0 && (
        <Card className="border-blue-100">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-blue-900">¿Por qué supera a los demás?</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              {report.candidate_comparison!.map((row, idx) => (
                <div
                  key={`${row.number}-${idx}`}
                  className={`rounded-xl border p-4 ${
                    idx === 0 ? "border-emerald-200 bg-emerald-50/50" : "border-slate-200 bg-slate-50/60"
                  }`}
                >
                  <p className="text-3xl font-bold tabular-nums text-slate-900">{pad2(row.number)}</p>
                  <ul className="mt-3 space-y-1 text-sm text-slate-700">
                    <li>Respaldo de Tabla 1: <YesNo value={row.table1_support} /></li>
                    <li>Confirmación de Tabla 2: <YesNo value={row.table2_support} /></li>
                    <li>Cruce entre loterías: <YesNo value={row.same_day_cross} /></li>
                    <li>
                      Evidencia histórica equivalente:{" "}
                      <span className="font-medium">{row.historical_label || "—"}</span>
                    </li>
                    <li>
                      Nivel de evidencia:{" "}
                      <span className="font-medium">{row.evidence_level_label || "—"}</span>
                    </li>
                  </ul>
                </div>
              ))}
            </div>
            {report.comparison_explanation && (
              <p className="text-sm leading-relaxed text-slate-700">{report.comparison_explanation}</p>
            )}
          </CardContent>
        </Card>
      )}

      {(report.reasoning_timeline || []).length > 0 && (
        <Card className="border-blue-100">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-blue-900">Cómo razonó el motor</CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="relative space-y-0 border-l-2 border-blue-200 pl-5">
              {report.reasoning_timeline!.map((step) => (
                <li key={step.step} className="relative pb-5 last:pb-0">
                  <span className="absolute -left-[1.4rem] top-1 flex h-5 w-5 items-center justify-center rounded-full bg-blue-600 text-[10px] font-bold text-white">
                    {step.step}
                  </span>
                  <p className="text-sm font-semibold text-slate-900">{step.title}</p>
                  <p className="mt-0.5 text-sm text-slate-600">{step.detail}</p>
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      )}

      {(report.mathematical_routes || []).length > 0 && (
        <Card className="border-blue-100">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-blue-900">Rutas matemáticas</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap justify-center gap-4">
              {report.mathematical_routes!.map((r, i) => (
                <RouteStack
                  key={`${r.kind}-${r.from_number}-${i}`}
                  from={r.from_number}
                  via={r.via || r.label}
                  to={r.to_number}
                />
              ))}
            </div>
            {report.routes_converge_text && (
              <p className="text-center text-sm font-medium text-emerald-800">
                {report.routes_converge_text}
              </p>
            )}
            {relationsHref && (
              <div className="text-center">
                <Button asChild variant="outline" size="sm">
                  <Link href={relationsHref}>Ver relaciones completas</Link>
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {cases.length > 0 && (
        <Card className="border-blue-100">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between gap-2">
              <CardTitle className="text-base text-blue-900">Últimos casos equivalentes</CardTitle>
              <Button variant="ghost" size="sm" onClick={() => setShowCases((v) => !v)}>
                {showCases ? "Ocultar" : "Mostrar"}
              </Button>
            </div>
          </CardHeader>
          {showCases && (
            <CardContent className="space-y-3">
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="text-xs uppercase text-slate-500">
                    <tr>
                      <th className="px-2 py-1">Fecha</th>
                      <th className="px-2 py-1">Principal</th>
                      <th className="px-2 py-1">Confirmador</th>
                      <th className="px-2 py-1">Resultado</th>
                      <th className="px-2 py-1">Ventana</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleCases.map((c, i) => (
                      <tr key={`${c.date}-${i}`} className="border-t border-slate-100">
                        <td className="px-2 py-2 tabular-nums">{c.date || "—"}</td>
                        <td className="px-2 py-2 tabular-nums">{pad2(c.primary_number)}</td>
                        <td className="px-2 py-2 tabular-nums">{pad2(c.confirmer)}</td>
                        <td className="px-2 py-2">
                          {c.result_number != null ? pad2(c.result_number) : c.result_label || "—"}
                        </td>
                        <td className="px-2 py-2">{c.window || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {cases.length > 5 && (
                <Button variant="outline" size="sm" onClick={() => setShowMoreCases((v) => !v)}>
                  {showMoreCases ? "Ver menos" : "Ver más casos"}
                </Button>
              )}
            </CardContent>
          )}
        </Card>
      )}

      {report.deterministic_explanation && (
        <Card className="border-blue-100">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-blue-900">Explicación del análisis</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed text-slate-700">
              {report.deterministic_explanation}
            </p>
          </CardContent>
        </Card>
      )}

      <div className="flex flex-wrap gap-2">
        {onAskChat ? (
          <Button className="bg-blue-600 hover:bg-blue-700" onClick={onAskChat}>
            Preguntar sobre este análisis
          </Button>
        ) : (
          <Button asChild className="bg-blue-600 hover:bg-blue-700">
            <Link href={chatHref}>Preguntar sobre este análisis</Link>
          </Button>
        )}
      </div>

      {report.disclaimer && (
        <p className="text-[11px] leading-relaxed text-slate-500">{report.disclaimer}</p>
      )}
    </div>
  );
}
