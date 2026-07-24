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
        +{scoreDelta} punto — vecino {match.neighbor} (compañero {match.companion}) · draw{" "}
        {String(match.draw_id || "").slice(0, 8)}
      </button>
      {open ? (
        <div className="mt-2 space-y-1 text-muted-foreground">
          <div>
            <span className="text-foreground">observed_number:</span> {match.observed_number}
          </div>
          <div>
            <span className="text-foreground">draw_id:</span> {match.draw_id}
          </div>
          <div>
            <span className="text-foreground">source_reference:</span>{" "}
            {match.source_reference || "—"}
          </div>
          <div>
            <span className="text-foreground">lotería:</span> {match.lottery_name}
          </div>
          <div>
            <span className="text-foreground">fecha:</span> {match.draw_date}
          </div>
          <div>
            <span className="text-foreground">hora:</span> {match.draw_time || "—"}
          </div>
          <div>
            <span className="text-foreground">posición:</span>{" "}
            {match.position_label || match.position}
          </div>
          <div>
            <span className="text-foreground">números del sorteo:</span>{" "}
            {Array.isArray(match.draw_numbers)
              ? JSON.stringify(match.draw_numbers).slice(0, 120)
              : "—"}
          </div>
          <div>
            <span className="text-foreground">peers / neighbors:</span>{" "}
            {(match.neighbors || []).join(", ")}
          </div>
          <div>
            <span className="text-foreground">mother_code:</span> {match.mother_code}
          </div>
          <div>
            <span className="text-foreground">companion:</span> {match.companion}
          </div>
          <div>
            <span className="text-foreground">table2_code:</span> {match.table2_code}
          </div>
          <div>
            <span className="text-foreground">table2_group:</span>{" "}
            {(match.table2_group || []).join(", ")}
          </div>
          <div>
            <span className="text-foreground">neighbor_found:</span> {match.neighbor}
          </div>
          <div>
            <span className="text-foreground">score_delta:</span> {scoreDelta}
          </div>
          <div>
            <span className="text-foreground">dedupe key:</span> {match.dedupe_key || "—"}
          </div>
          <div>
            <span className="text-foreground">timestamp análisis:</span>{" "}
            {match.analyzed_at || "—"}
          </div>
          {match.trace ? <p className="pt-1 italic text-foreground">{match.trace}</p> : null}
          <Button type="button" size="sm" variant="outline" onClick={() => setJsonOpen((v) => !v)}>
            {jsonOpen ? "Ocultar JSON" : "Ver JSON"}
          </Button>
          {jsonOpen ? (
            <pre className="mt-2 max-h-48 overflow-auto rounded bg-muted p-2 text-[10px]">
              {JSON.stringify(match, null, 2)}
            </pre>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
