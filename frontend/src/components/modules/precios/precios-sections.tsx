"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  Package,
  RefreshCw,
  Search,
  Truck,
  Upload,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api";
import type { PriceIntelligenceDashboard } from "@/lib/licitador";
import type { PriceProduct, PriceQuoteDraft } from "@/lib/prices";
import { cn } from "@/lib/utils";

export function PreciosBuscadorSection({ mode = "search" }: { mode?: "search" | "compare" | "history" }) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<PriceProduct[]>([]);
  const [summary, setSummary] = useState<string | null>(null);

  const run = useCallback(async () => {
    const q = query.trim();
    if (q.length < 2) return;
    setLoading(true);
    try {
      if (mode === "compare") {
        const res = await apiClient.comparePrices({ q, limit: 20, include_indexed: true });
        setSummary(res.summary);
        const rows: PriceProduct[] = [];
        if (res.best_product) rows.push(res.best_product);
        setItems(rows);
      } else {
        const res = await apiClient.searchPrices({
          q,
          limit: 40,
          include_indexed: true,
          include_historical: mode === "history",
        });
        setSummary(res.filter_explanation ?? null);
        setItems(res.items);
      }
    } finally {
      setLoading(false);
    }
  }, [query, mode]);

  return (
    <div className="space-y-4">
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void run();
        }}
      >
        <Input
          placeholder="Buscar producto, SKU, marca…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="max-w-xl"
        />
        <Button type="submit" disabled={loading || query.trim().length < 2}>
          <Search className="mr-2 h-4 w-4" />
          {mode === "compare" ? "Comparar" : "Buscar"}
        </Button>
      </form>
      {summary && <p className="text-sm text-muted-foreground">{summary}</p>}
      {loading && <p className="text-sm text-muted-foreground">Consultando catálogo…</p>}
      <ul className="divide-y rounded-xl border">
        {items.map((p) => (
          <li key={p.id} className="flex flex-wrap items-start justify-between gap-3 px-4 py-3 text-sm">
            <div className="min-w-0 flex-1">
              <p className="font-medium">{p.description ?? p.model ?? p.sku ?? "Producto"}</p>
              <p className="text-xs text-muted-foreground">
                {p.supplier && `${p.supplier} · `}
                {p.brand && `${p.brand} · `}
                {p.source_filename}
              </p>
            </div>
            <div className="shrink-0 text-right">
              <p className="font-semibold text-emerald-700 dark:text-emerald-400">
                {p.preferred_price ?? p.price ?? "—"} {p.currency}
              </p>
              {p.stock != null && <p className="text-xs text-muted-foreground">Stock: {p.stock}</p>}
            </div>
          </li>
        ))}
        {!loading && items.length === 0 && query.trim().length >= 2 && (
          <li className="px-4 py-8 text-center text-muted-foreground">Sin resultados</li>
        )}
      </ul>
    </div>
  );
}

export function PreciosListasSection() {
  const [data, setData] = useState<PriceIntelligenceDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    apiClient
      .getDocumentsHubPrices()
      .then(setData)
      .catch(() => apiClient.getLicitadorPriceDashboard().then(setData).catch(() => setData(null)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const runSync = async () => {
    setSyncing(true);
    try {
      await apiClient.syncPriceLists();
      load();
    } finally {
      setSyncing(false);
    }
  };

  if (loading) return <p className="text-sm text-muted-foreground">Cargando listas…</p>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={cn("mr-2 h-4 w-4", loading && "animate-spin")} />
          Actualizar
        </Button>
        <Button size="sm" onClick={() => void runSync()} disabled={syncing}>
          <Upload className={cn("mr-2 h-4 w-4", syncing && "animate-pulse")} />
          Indexar listas
        </Button>
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard icon={Package} label="Productos indexados" value={data?.total_products ?? 0} />
        <MetricCard icon={Truck} label="Proveedores" value={data?.total_suppliers ?? 0} />
        <MetricCard icon={Upload} label="Listas hoy" value={data?.lists_today ?? 0} highlight />
        <MetricCard icon={Package} label="Pendientes" value={data?.pending_files.length ?? 0} warn />
      </div>
      {(data?.pending_files.length ?? 0) > 0 && (
        <Card className="border-amber-500/40">
          <CardHeader>
            <CardTitle className="text-base">Archivos pendientes de indexar</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            {data!.pending_files.slice(0, 12).map((f) => (
              <p key={f.id} className="truncate text-muted-foreground">{f.name} · {f.parent_path}</p>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export function PreciosDraftsSection() {
  const [drafts, setDrafts] = useState<PriceQuoteDraft[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient
      .listPriceQuoteDrafts()
      .then((r) => setDrafts(r.items))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-muted-foreground">Cargando borradores…</p>;

  return (
    <ul className="divide-y rounded-xl border">
      {drafts.map((d) => (
        <li key={d.id} className="px-4 py-3 text-sm">
          <p className="font-medium">{d.description ?? d.client_name ?? "Borrador"}</p>
          <p className="text-xs text-muted-foreground">
            {d.supplier && `${d.supplier} · `}
            {d.sale_price_suggested && `RD$${d.sale_price_suggested} · `}
            {d.status}
          </p>
        </li>
      ))}
      {!drafts.length && <li className="px-4 py-8 text-center text-muted-foreground">Sin borradores</li>}
    </ul>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
  highlight,
  warn,
}: {
  icon: typeof Package;
  label: string;
  value: number;
  highlight?: boolean;
  warn?: boolean;
}) {
  return (
    <Card className={highlight ? "border-primary/30 bg-primary/5" : warn && value > 0 ? "border-amber-500/30 bg-amber-500/5" : undefined}>
      <CardContent className="flex items-center gap-3 pt-6">
        <Icon className="h-7 w-7 text-muted-foreground" />
        <div>
          <p className="text-2xl font-semibold">{value.toLocaleString()}</p>
          <p className="text-xs text-muted-foreground">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}
