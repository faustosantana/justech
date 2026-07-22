"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw, ShoppingCart } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import type { CommercialSearchItem } from "@/lib/commercial-search";
import { cn } from "@/lib/utils";

interface Props {
  institution: string;
  title: string;
  queryTerms?: string;
}

export function CommercialHistoryPanel({ institution, title, queryTerms }: Props) {
  const [items, setItems] = useState<CommercialSearchItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const search = useCallback(async () => {
    setLoading(true);
    try {
      const q = queryTerms?.trim() || `${institution} ${title}`.slice(0, 120);
      const res = await apiClient.commercialSearch(q, { limit: 20 });
      setItems(res.items);
      setMessage(res.message ?? null);
    } finally {
      setLoading(false);
    }
  }, [institution, title, queryTerms]);

  useEffect(() => {
    void search();
  }, [search]);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between py-3">
        <CardTitle className="text-base flex items-center gap-2">
          <ShoppingCart className="h-4 w-4" />
          Historial comercial Odoo
        </CardTitle>
        <Button variant="outline" size="sm" onClick={() => void search()} disabled={loading}>
          <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
        </Button>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <p className="text-xs text-muted-foreground">
          Ventas y cotizaciones indexadas relacionadas con la entidad u objeto del proceso. Fuente: Odoo (solo lectura).
        </p>
        {message && items.length === 0 && (
          <p className="text-muted-foreground text-xs">{message}</p>
        )}
        {items.map((item) => (
          <div key={item.id} className="rounded border px-2 py-1.5 text-xs">
            <p className="font-medium">{item.product_name || item.description || "—"}</p>
            <p className="text-muted-foreground">
              {item.customer_name} · {item.document_type} {item.document_number}
              {item.unit_price && ` · ${item.currency ?? "RD$"}${item.unit_price}`}
              {item.date && ` · ${item.date}`}
            </p>
            <p className="text-[10px] text-muted-foreground">
              Odoo {item.source_model} #{item.source_id}
              {item.salesperson && ` · ${item.salesperson}`}
            </p>
          </div>
        ))}
        {!loading && items.length === 0 && !message && (
          <p className="text-muted-foreground text-xs">Sin coincidencias en el índice comercial.</p>
        )}
      </CardContent>
    </Card>
  );

}
