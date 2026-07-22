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
              {d.source_reference ? ` · ref ${String(d.source_reference)}` : ""}
              {d.game_name ? ` · ${String(d.game_name)}` : ""}
            </p>
            <div className="flex flex-wrap gap-3">
              {nums.map((n, j) => (
                <div key={`${n.position}-${j}`} className="text-center">
                  <p className="text-[10px] uppercase text-muted-foreground">
                    {n.position_label || n.position}
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

  if (type === "lottery_result" || type === "lottery_range") {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">
            {type === "lottery_range" ? "Ventana histórica" : "Resultados"}
            {structured.tool ? ` · ${structured.tool}` : ""}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {draws.length > 0 ? (
            <DrawNumbers draws={draws} />
          ) : (
            <pre tabIndex={0} className="max-h-48 overflow-auto rounded bg-muted/40 p-2 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring">
              {JSON.stringify(data, null, 2).slice(0, 2000)}
            </pre>
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
                <th>Cantidad</th>
                <th>Fechas</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it) => (
                <tr key={String(it.number)} className="border-t">
                  <td className="py-1 font-mono text-lg">{String(it.number)}</td>
                  <td>{String(it.count)}</td>
                  <td className="text-xs text-muted-foreground">
                    {Array.isArray(it.dates) ? it.dates.join(", ") : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    );
  }

  if (type === "lottery_next_occurrences") {
    const items = (data.items as Array<Record<string, unknown>> | undefined) || [];
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Próxima aparición histórica</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-sm">
          <p className="text-xs text-muted-foreground">{String(data.note || "")}</p>
          {items.map((it, i) => (
            <p key={i} className="font-mono">
              {String(it.draw_date)} · pos {String(it.position_label)} · {String(it.number_value)}
            </p>
          ))}
        </CardContent>
      </Card>
    );
  }

  if (type === "lottery_comparison" || type === "lottery_frequency") {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">
            {type === "lottery_frequency" ? "Frecuencias" : "Comparación"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <pre tabIndex={0} className="max-h-56 overflow-auto rounded bg-muted/40 p-2 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring">
            {JSON.stringify(data, null, 2).slice(0, 3000)}
          </pre>
        </CardContent>
      </Card>
    );
  }

  return null;
}
