"use client";

import { useCallback, useEffect, useState } from "react";
import { Brain, ChevronRight, RefreshCw } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import { cn } from "@/lib/utils";

type Card = {
  id: string;
  type: string;
  title: string;
  summary: string;
  priority: string;
  source: string;
  recommendation: string;
  date?: string | null;
  href?: string | null;
  suggested_actions?: { action: string; label: string; requires_approval: boolean }[];
};

const PRIORITY_CLASS: Record<string, string> = {
  critical: "border-destructive/40 bg-destructive/5",
  high: "border-orange-500/40 bg-orange-500/5",
  medium: "border-primary/30 bg-primary/5",
  low: "border-border",
};

export function HermesIntelligenceCenterSection() {
  const [cards, setCards] = useState<Card[]>([]);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.getHermesIntelligenceCenter();
      setCards(res.cards);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const onAction = async (card: Card, action: string) => {
    setActing(`${card.id}-${action}`);
    try {
      if (action === "ignore" || action === "mark_reviewed") {
        setCards((prev) => prev.filter((c) => c.id !== card.id));
        return;
      }
      if (card.href && (action === "view_detail" || action === "search_history")) {
        window.location.href = card.href;
        return;
      }
      alert(
        action.includes("prepare") || action.includes("create") || action.includes("autofill")
          ? "Hermes preparará un borrador. Confirme en el módulo correspondiente — no se ejecuta automáticamente."
          : "Acción registrada como sugerida. Requiere su aprobación para ejecutarse.",
      );
    } finally {
      setActing(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Recomendaciones proactivas con fuente verificable. Hermes no ejecuta acciones sin su aprobación.
        </p>
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          <RefreshCw className={cn("mr-1 h-3.5 w-3.5", loading && "animate-spin")} />
          Actualizar
        </Button>
      </div>

      {cards.map((card) => (
        <Card key={card.id} className={cn(PRIORITY_CLASS[card.priority] ?? "")}>
          <CardHeader className="py-3">
            <div className="flex items-start justify-between gap-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Brain className="h-4 w-4" />
                {card.title}
              </CardTitle>
              <span className="text-[10px] uppercase text-muted-foreground">{card.priority} · {card.source}</span>
            </div>
            <p className="text-sm text-muted-foreground">{card.summary}</p>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <p>{card.recommendation}</p>
            {card.date && <p className="text-xs text-muted-foreground">Fecha: {card.date}</p>}
            <div className="flex flex-wrap gap-1">
              {card.href && (
                <Button size="sm" variant="outline" asChild>
                  <Link href={card.href}>
                    Ver detalle
                    <ChevronRight className="ml-1 h-3 w-3" />
                  </Link>
                </Button>
              )}
              {(card.suggested_actions ?? []).map((a) => (
                <Button
                  key={a.action}
                  size="sm"
                  variant={a.requires_approval ? "outline" : "secondary"}
                  disabled={!!acting}
                  onClick={() => void onAction(card, a.action)}
                >
                  {a.label}
                  {a.requires_approval && " *"}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}

      {!loading && cards.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center text-sm text-muted-foreground">
            Sin alertas proactivas en este momento. Sincronice Odoo y DGCP para enriquecer el centro.
          </CardContent>
        </Card>
      )}
    </div>
  );
}
