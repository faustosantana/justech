"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import { NrEmptyState, NR_EMPTY_COPY } from "./nr-empty-states";

export type ChartBar = { label: string; value: number; hint?: string };

function Bars({
  title,
  question,
  summary,
  items,
  emptyTitle,
  emptyBody,
}: {
  title: string;
  question?: string;
  summary?: string;
  items: ChartBar[];
  emptyTitle?: string;
  emptyBody?: string;
}) {
  const hasItems = items.length > 0;
  if (!hasItems) {
    return (
      <NrEmptyState
        title={emptyTitle || title}
        body={emptyBody || NR_EMPTY_COPY.noHistory.body}
      />
    );
  }
  const max = Math.max(1, ...items.map((i) => i.value));
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        {question ? <p className="text-sm text-muted-foreground">{question}</p> : null}
        {summary ? <p className="text-sm">{summary}</p> : null}
      </CardHeader>
      <CardContent className="space-y-2" role="img" aria-label={title}>
        {items.map((item) => (
          <div key={item.label} className="grid grid-cols-[7rem_1fr_4.5rem] items-center gap-2 text-sm">
            <span className="truncate" title={item.label}>
              {item.label}
            </span>
            <div className="h-3 rounded bg-muted" aria-hidden>
              <div
                className="h-3 rounded bg-primary/80"
                style={{ width: `${Math.max(item.value === 0 ? 0 : 4, (100 * item.value) / max)}%` }}
              />
            </div>
            <span className="text-right tabular-nums">
              {item.value}
              {item.hint ? ` (${item.hint})` : ""}
            </span>
          </div>
        ))}
        <ul className="sr-only">
          {items.map((i) => (
            <li key={i.label}>
              {i.label}: {i.value}
              {i.hint ? ` (${i.hint})` : ""}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

type Charts = Record<string, unknown>;

export function PrimaryHistoricalCharts({
  number,
  header,
  charts,
  condition,
  sampleWarning,
}: {
  number: string | number;
  header: Record<string, unknown>;
  charts: Charts;
  condition: Record<string, unknown>;
  sampleWarning?: string | null;
}) {
  const total = Number(header.aparecio ?? condition.total_apariciones ?? 0);
  const periodo = String(header.periodo || "el período seleccionado");
  const seven = (charts.respuesta_en_siete_sorteos || {}) as Record<string, unknown>;
  const porPos = (seven.por_posicion || []) as Record<string, unknown>[];
  const evaluablesSeven = Number(seven.casos_evaluables ?? 0);

  return (
    <div className="space-y-4">
      {sampleWarning ? (
        <NrEmptyState title="Muestra pequeña" body={sampleWarning} />
      ) : null}
      <div className="grid gap-4 lg:grid-cols-2">
        <Bars
          title="¿Cuántas veces salió este número?"
          question="Apariciones por año"
          summary={`El número ${number} apareció ${total} veces en ${periodo}.`}
          items={((charts.apariciones_por_anio || []) as Record<string, unknown>[]).map((r) => ({
            label: String(r.anio),
            value: Number(r.cantidad || 0),
          }))}
        />
        <Bars
          title="¿En cuáles loterías salió más?"
          question="Distribución por lotería"
          summary={`Total observado: ${total} apariciones.`}
          items={((charts.apariciones_por_loteria || []) as Record<string, unknown>[]).map((r) => ({
            label: String(r.loteria),
            value: Number(r.cantidad || 0),
            hint: r.porcentaje != null ? `${r.porcentaje}%` : undefined,
          }))}
        />
        <Bars
          title="¿Cuántas veces se dio la condición?"
          question="Sí / parcial / no (censurados aparte)"
          summary={
            condition.texto
              ? String(condition.texto)
              : `Positivas ${condition.positivas ?? 0}, parciales ${condition.parciales ?? 0}, negativas ${condition.negativas ?? 0}.`
          }
          items={[
            ...(((charts.condicion || []) as Record<string, unknown>[]).map((r) => ({
              label: String(r.etiqueta),
              value: Number(r.cantidad || 0),
            })) || []),
            {
              label: "Seguimiento incompleto",
              value: Number((charts.condicion_censurados as number) ?? seven.sin_seguimiento_suficiente ?? 0),
            },
          ]}
        />
        <Bars
          title="¿Cuáles compañeros fueron fortalecidos más veces?"
          question="Candidatos de Tabla 1 con confirmación"
          items={((charts.candidatos_fortalecidos || []) as Record<string, unknown>[]).map((r) => ({
            label: `Nº ${r.candidato}`,
            value: Number(r.veces || 0),
            hint:
              r.casos_evaluables != null
                ? `${r.casos_evaluables} eval.`
                : r.respuesta_en_3 != null
                  ? `3s: ${r.respuesta_en_3}`
                  : undefined,
          }))}
          emptyBody="Ningún compañero recibió confirmación en este período."
        />
        <Bars
          title="¿Qué ocurrió en los siete sorteos posteriores?"
          question="Aparición del candidato por posición 1–7"
          summary={
            evaluablesSeven
              ? `Casos evaluables: ${evaluablesSeven}. Sin aparición en 7: ${Number(seven.no_aparecio_en_7 || 0)}. Seguimiento incompleto: ${Number(seven.sin_seguimiento_suficiente || 0)}.`
              : undefined
          }
          items={[
            ...porPos.map((r) => {
              const cant = Number(r.cantidad || 0);
              const den = Number(r.evaluables ?? evaluablesSeven ?? 0);
              const pct = den ? `${Math.round((1000 * cant) / den) / 10}%` : undefined;
              return {
                label: `Sorteo ${r.sorteo}`,
                value: cant,
                hint: pct,
              };
            }),
            {
              label: "No en 7",
              value: Number(seven.no_aparecio_en_7 || 0),
            },
            {
              label: "Sin seguimiento",
              value: Number(seven.sin_seguimiento_suficiente || 0),
            },
          ]}
        />
      </div>
    </div>
  );
}
