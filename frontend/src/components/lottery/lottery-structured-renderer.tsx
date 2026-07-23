"use client";

import type { LotteryChatSendResponse } from "@/lib/lottery";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Structured = NonNullable<LotteryChatSendResponse["message"]["structured_content"]>;

function DrawNumbers({ draws }: { draws: Array<Record<string, unknown>> }) {
  return (
    <div className="space-y-3">
      {draws.map((d, i) => {
        const nums = (d.numbers as Array<Record<string, string>> | undefined) || [];
        return (
          <div key={String(d.id || i)} className="rounded-md border p-3">
            <p className="mb-2 text-xs text-muted-foreground">
              {String(d.draw_date || "")}
              {d.draw_time ? ` · ${String(d.draw_time)}` : ""}
              {d.game_name ? ` · ${String(d.game_name)}` : ""}
            </p>
            <div className="flex flex-wrap gap-3">
              {nums.map((n, j) => (
                <div key={`${n.position}-${j}`} className="text-center">
                  <p className="text-[10px] uppercase text-muted-foreground">
                    {n.position_label ||
                      (n.position === "1" || n.position === 1
                        ? "Primera posición"
                        : n.position === "2" || n.position === 2
                          ? "Segunda posición"
                          : n.position === "3" || n.position === 3
                            ? "Tercera posición"
                            : n.position)}
                  </p>
                  <p className="font-mono text-2xl font-semibold">{n.number_raw || n.number_value}</p>
                  {n.number_type && n.number_type !== "principal" && (
                    <p className="text-[10px] text-muted-foreground">{n.number_type}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function OccurrenceRows({ rows }: { rows: Array<Record<string, unknown>> }) {
  if (!rows.length) return null;
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-muted-foreground">
          <th className="py-1">Lotería</th>
          <th>Última aparición</th>
          <th>Resultado</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={`${String(r.lottery)}-${i}`} className="border-t">
            <td className="py-1">{String(r.lottery || "—")}</td>
            <td className="font-mono text-xs">{String(r.last_date || "—")}</td>
            <td className="font-mono text-xs">{String(r.result || "—")}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function LotteryStructuredRenderer({ structured }: { structured?: Structured | null }) {
  if (!structured) return null;
  const type = structured.type || "lottery_result";
  const data = (structured.data || {}) as Record<string, unknown>;
  const warnings = structured.warnings || [];

  if (type === "lottery_error" || type === "lottery_ambiguity" || type === "lottery_no_results") {
    return (
      <Card className="border-amber-500/40">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">
            {type === "lottery_ambiguity"
              ? "Aclaración requerida"
              : type === "lottery_no_results"
                ? "Sin resultados"
                : "Aviso"}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-sm text-muted-foreground">
          {warnings.map((w) => (
            <p key={w.code}>{w.message}</p>
          ))}
        </CardContent>
      </Card>
    );
  }

  const draws = (data.draws as Array<Record<string, unknown>> | undefined) || [];
  const occurrences =
    (data.occurrences as Array<Record<string, unknown>> | undefined) ||
    (data.items as Array<Record<string, unknown>> | undefined) ||
    [];
  const sections = (data.sections as Array<Record<string, unknown>> | undefined) || [];
  const rows = (data.rows as Array<Record<string, unknown>> | undefined) || [];

  if (type === "lottery_result" || type === "lottery_range") {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">
            {type === "lottery_range" ? "Ventana histórica" : "Resultados"}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {draws.length > 0 ? (
            <DrawNumbers draws={draws} />
          ) : occurrences.length > 0 ? (
            <ul className="space-y-1 text-sm">
              {occurrences.slice(0, 12).map((o, i) => (
                <li key={i} className="font-mono text-xs">
                  {String(o.draw_date || "")}
                  {o.position_label || o.position
                    ? ` · ${String(o.position_label || o.position)}`
                    : ""}
                  {o.number_raw || o.number_value
                    ? ` · ${String(o.number_raw || o.number_value)}`
                    : ""}
                </li>
              ))}
            </ul>
          ) : rows.length > 0 ? (
            <OccurrenceRows rows={rows} />
          ) : (
            <p className="text-sm text-muted-foreground">Consulta completada. Ver respuesta arriba.</p>
          )}
        </CardContent>
      </Card>
    );
  }

  if (type === "lottery_repetitions") {
    const items = (data.items as Array<Record<string, unknown>> | undefined) || [];
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Repeticiones</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted-foreground">
                <th className="py-1">Número</th>
                <th>Veces</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it) => (
                <tr key={String(it.number)} className="border-t">
                  <td className="py-1 font-mono">{String(it.number)}</td>
                  <td>{String(it.count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    );
  }

  if (type === "lottery_comparison" || type === "lottery_frequencies" || type === "lottery_analytics") {
    const periodA = data.period_a as Record<string, unknown> | undefined;
    const periodItems = (data.items as Array<Record<string, unknown>> | undefined) || [];
    const freqItems =
      (data.frequencies as Array<Record<string, unknown>> | undefined) ||
      (data.top as Array<Record<string, unknown>> | undefined) ||
      [];

    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">
            {data.intent === "multi_last_occurrence"
              ? "Últimas apariciones"
              : type === "lottery_frequencies"
                ? "Frecuencias"
                : "Comparación"}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {sections.length > 0 &&
            sections.map((sec, i) => (
              <div key={i} className="space-y-2">
                <p className="text-sm font-medium">
                  {String(sec.number || "")}
                  {sec.position_label ? ` · ${String(sec.position_label)}` : ""}
                </p>
                <OccurrenceRows
                  rows={
                    (sec.display_rows as Array<Record<string, unknown>> | undefined) ||
                    (sec.rows as Array<Record<string, unknown>> | undefined) ||
                    []
                  }
                />
              </div>
            ))}
          {sections.length === 0 && rows.length > 0 && <OccurrenceRows rows={rows} />}
          {periodItems.length > 0 && (
            <div className="grid gap-2 sm:grid-cols-2">
              {periodItems.map((p, i) => (
                <div key={i} className="rounded border p-2 text-sm">
                  <p className="text-xs text-muted-foreground">{String(p.label || "")}</p>
                  <p className="font-medium">
                    {String(p.occurrences)} apariciones / {String(p.draws)} sorteos
                  </p>
                  <p className="text-xs">
                    Frecuencia relativa: {String(p.relative_frequency_pct ?? "—")}%
                  </p>
                  <p className="text-[10px] text-muted-foreground">
                    {String(p.from)} → {String(p.to)}
                  </p>
                </div>
              ))}
            </div>
          )}
          {freqItems.length > 0 && (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted-foreground">
                  <th className="py-1">Número</th>
                  <th>Veces</th>
                </tr>
              </thead>
              <tbody>
                {freqItems.slice(0, 20).map((it) => (
                  <tr key={String(it.number)} className="border-t">
                    <td className="py-1 font-mono">{String(it.number)}</td>
                    <td>{String(it.count ?? it.occurrences ?? "—")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {data.metric ? (
            <p className="text-[11px] text-muted-foreground">Métrica: {String(data.metric)}</p>
          ) : null}
          {Array.isArray(data.limitations) && data.limitations.length > 0 ? (
            <p className="text-[11px] text-muted-foreground">
              Limitaciones: {(data.limitations as string[]).join(" · ")}
            </p>
          ) : null}
          {!periodA && sections.length === 0 && rows.length === 0 && freqItems.length === 0 && (
            <p className="text-sm text-muted-foreground">Consulta completada. Ver respuesta arriba.</p>
          )}
        </CardContent>
      </Card>
    );
  }

  return null;
}
