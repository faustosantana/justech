"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export type SignalCardProps = {
  number: number;
  evidenceLevel: string;
  confirmationCount: number;
  activatorsText: string;
  historicalRateLabel: string;
  typicalCycleLabel: string;
  analysisHref: string;
};

export function SignalCard({
  number,
  evidenceLevel,
  confirmationCount,
  activatorsText,
  historicalRateLabel,
  typicalCycleLabel,
  analysisHref,
}: SignalCardProps) {
  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Número fortalecido
        </p>
        <CardTitle className="font-mono text-4xl tabular-nums leading-none">{number}</CardTitle>
        <p className="text-sm text-muted-foreground">{evidenceLevel}</p>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div>
          <div className="text-xs uppercase text-muted-foreground">Activado por</div>
          <p>{activatorsText}</p>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <div className="text-xs uppercase text-muted-foreground">Confirmaciones</div>
            <p className="font-semibold tabular-nums">{confirmationCount}</p>
          </div>
          <div>
            <div className="text-xs uppercase text-muted-foreground">Ciclo típico</div>
            <p className="font-semibold">{typicalCycleLabel}</p>
          </div>
        </div>
        <div>
          <div className="text-xs uppercase text-muted-foreground">Respuesta histórica</div>
          <p>{historicalRateLabel}</p>
        </div>
        <Button asChild className="min-h-11 w-full">
          <Link href={analysisHref}>Ver análisis</Link>
        </Button>
        <p className="text-xs text-muted-foreground">
          Las señales representan relaciones históricas observadas. No garantizan resultados futuros.
        </p>
      </CardContent>
    </Card>
  );
}
