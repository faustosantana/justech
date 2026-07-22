"use client";

import { Network } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { KnowledgeGraphPayload, ResolvedEntity } from "@/lib/search";

interface Props {
  graph?: KnowledgeGraphPayload | null;
  entities?: ResolvedEntity[];
  query?: string;
}

export function KnowledgeGraphPanel({ graph, entities, query }: Props) {
  const summary = graph?.summary ?? {};
  const nodes = graph?.nodes ?? [];
  const edges = graph?.edges ?? [];

  return (
    <Card className="border-primary/20 sticky top-4">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Network className="h-4 w-4 text-primary" />
          Knowledge Graph
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        {query && (
          <p className="text-xs text-muted-foreground">
            Consulta: <span className="text-foreground font-medium">{query}</span>
          </p>
        )}

        {entities && entities.length > 0 && (
          <div>
            <p className="text-xs font-medium uppercase text-muted-foreground mb-2">Entidades resueltas</p>
            <ul className="space-y-2">
              {entities.map((e) => (
                <li key={e.entity_id} className="rounded border px-2 py-1.5">
                  <p className="font-medium">{e.canonical_name}</p>
                  <p className="text-xs text-muted-foreground">
                    {e.entity_type} · {e.match_kind} · {(e.confidence * 100).toFixed(0)}%
                  </p>
                </li>
              ))}
            </ul>
          </div>
        )}

        {Object.keys(summary).length > 0 && (
          <div>
            <p className="text-xs font-medium uppercase text-muted-foreground mb-2">Relaciones</p>
            <ul className="space-y-1">
              {Object.entries(summary).map(([key, count]) => (
                <li key={key} className="flex justify-between text-xs">
                  <span className="capitalize">{key.replace(/_/g, " ")}</span>
                  <span className="font-mono">{count}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {nodes.length > 0 && (
          <div className="max-h-48 overflow-y-auto rounded bg-muted/40 p-2 text-[10px] font-mono leading-relaxed">
            {nodes.slice(0, 12).map((n) => (
              <div key={n.id} className="truncate">
                [{n.type}] {n.label}
              </div>
            ))}
            {edges.length > 0 && (
              <p className="mt-2 text-muted-foreground">{edges.length} relaciones</p>
            )}
          </div>
        )}

        {!entities?.length && !Object.keys(summary).length && (
          <p className="text-xs text-muted-foreground">
            Escriba una consulta para ver entidades y relaciones cross-módulo.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
