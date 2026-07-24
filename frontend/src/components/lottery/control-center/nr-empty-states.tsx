"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function NrEmptyState({
  title,
  body,
}: {
  title: string;
  body: string;
}) {
  return (
    <Card role="status" aria-live="polite">
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">{body}</CardContent>
    </Card>
  );
}

export const NR_EMPTY_COPY = {
  noRecent: {
    title: "Sin resultados recientes",
    body: "No encontramos resultados recientes para esta lotería.",
  },
  noSignals: {
    title: "Sin señales confirmadas",
    body: "Los resultados recientes no generaron señales confirmadas dentro de la ventana seleccionada.",
  },
  noHistory: {
    title: "Histórico insuficiente",
    body: "No existen suficientes registros históricos para analizar esta relación.",
  },
  smallSample: (n: number) => ({
    title: "Muestra pequeña",
    body: `Solo encontramos ${n} casos. La evidencia histórica es limitada.`,
  }),
  incompleteFollowUp: {
    title: "Seguimiento incompleto",
    body: "No habían transcurrido suficientes sorteos para conocer el resultado completo.",
  },
  serviceError: {
    title: "No pudimos completar el análisis",
    body: "Inténtelo nuevamente. Si el problema continúa, revise la conexión o vuelva más tarde.",
  },
} as const;
