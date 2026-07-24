"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";

import type { MatchRow } from "./motor-types";

export function TraceExpand({ match }: { match: MatchRow }) {
  const [open, setOpen] = useState(false);
  const [jsonOpen, setJsonOpen] = useState(false);
  const scoreDelta = match.score_delta ?? match.points ?? 1;

  return (
    <div className="rounded border p-2 text-xs">
      <button type="button" className="font-medium underline" onClick={() => setOpen((v) => !v)}>
        {match.observed_number != null
          ? `${match.observed_number} fortaleció al ${match.companion} mediante el ${match.neighbor}`
          : `Compañero ${match.companion} confirmado por ${match.neighbor}`}{" "}
        · fuerza +{scoreDelta}
      </button>
      {open ? (
        <div className="mt-2 space-y-1 text-muted-foreground">
          <div>
            <span className="text-foreground">Número observado:</span> {match.observed_number}
          </div>
          <div>
            <span className="text-foreground">Compañero (Tabla 1):</span> {match.companion}
          </div>
          <div>
            <span className="text-foreground">Confirmador (Tabla 2):</span> {match.neighbor}
          </div>
          <div>
            <span className="text-foreground">Lotería:</span> {match.lottery_name}
          </div>
          <div>
            <span className="text-foreground">Fecha:</span> {match.draw_date} {match.draw_time || ""}
          </div>
          <div>
            <span className="text-foreground">Posición:</span>{" "}
            {match.position_label || match.position}
          </div>
          {match.trace ? <p className="pt-1 italic text-foreground">{match.trace}</p> : null}
          <details className="mt-1">
            <summary className="cursor-pointer text-foreground">Ver evidencia técnica</summary>
            <div className="mt-1 space-y-1">
              <div>draw_id: {match.draw_id}</div>
              <div>mother_code: {match.mother_code}</div>
              <div>table2_code: {match.table2_code}</div>
              <div>dedupe key: {match.dedupe_key || "—"}</div>
              <Button type="button" size="sm" variant="outline" className="mt-1" onClick={() => setJsonOpen((v) => !v)}>
                {jsonOpen ? "Ocultar JSON" : "Ver JSON"}
              </Button>
              {jsonOpen ? (
                <pre className="mt-2 max-h-48 overflow-auto rounded bg-muted p-2 text-[10px]">
                  {JSON.stringify(match, null, 2)}
                </pre>
              ) : null}
            </div>
          </details>
        </div>
      ) : null}
    </div>
  );
}
