"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export type WhyStructured = {
  observed_number?: number;
  candidato?: number;
  table1_candidates?: number[];
  related_confirmers?: number[];
  observed_confirmers?: number[];
  confirmation_count?: number;
  historical_cases?: number | null;
  evaluable_cases?: number | null;
  response_within_3?: string | null;
  typical_cycle?: string | null;
  pasos?: string[];
  conclusion?: string;
  numeros_no_modificables_por_ia?: boolean;
};

export function WhyStrengthenedPanel({ why }: { why: WhyStructured }) {
  const steps =
    why.pasos && why.pasos.length
      ? why.pasos
      : buildFallbackSteps(why);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          ¿Por qué se fortaleció el número {String(why.candidato ?? "—")}?
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <ol className="list-decimal space-y-1 pl-5">
          {steps.map((p, i) => (
            <li key={i}>{p}</li>
          ))}
        </ol>
        {why.conclusion ? <p className="font-medium">Conclusión: {why.conclusion}</p> : null}
        <p className="text-xs text-muted-foreground">
          Explicación determinista del motor. Los números, confirmadores y cantidades no pueden
          alterarse por redacción.
        </p>
      </CardContent>
    </Card>
  );
}

function buildFallbackSteps(why: WhyStructured): string[] {
  const n = why.observed_number;
  const c = why.candidato;
  const related = why.related_confirmers || [];
  const observed = why.observed_confirmers || [];
  const steps: string[] = [];
  if (n != null) steps.push(`Salió el número ${n}.`);
  if (c != null) steps.push(`Tabla 1 identificó al ${c} como compañero.`);
  if (related.length) {
    steps.push(`Tabla 2 relaciona al ${c} con ${related.join(", ")}.`);
  }
  if (observed.length) {
    steps.push(`Aparecieron: ${observed.join(", ")}.`);
    steps.push(`El ${c} recibió ${why.confirmation_count ?? observed.length} confirmaciones.`);
  } else if (c != null) {
    steps.push(`En esta ocasión no apareció ningún confirmador de Tabla 2 para el ${c}.`);
  }
  if (why.evaluable_cases != null) {
    steps.push(`Esta condición tiene ${why.evaluable_cases} casos evaluables en el histórico.`);
  }
  if (why.response_within_3) steps.push(why.response_within_3);
  if (why.typical_cycle) steps.push(why.typical_cycle);
  return steps;
}
