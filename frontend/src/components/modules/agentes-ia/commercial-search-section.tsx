"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Building2,
  DollarSign,
  Package,
  RefreshCw,
  Search,
  ShoppingCart,
  TrendingUp,
} from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import type { CommercialSearchItem, CommercialSearchResponse } from "@/lib/commercial-search";
import { cn } from "@/lib/utils";

type Tab = "search" | "sales" | "prices" | "customers" | "products";

const SAMPLE_QUERIES = [
  "laptop dell i7 16gb",
  "switch cisco",
  "toner hp",
  "monitor lenovo",
  "banco ademi",
  "capital dbg",
];

const TABS: { id: Tab; label: string; icon: typeof Search }[] = [
  { id: "search", label: "Búsqueda", icon: Search },
  { id: "sales", label: "Historial ventas", icon: ShoppingCart },
  { id: "prices", label: "Precios", icon: DollarSign },
  { id: "customers", label: "Por cliente", icon: Building2 },
  { id: "products", label: "Por producto", icon: Package },
];

export function CommercialSearchSection() {
  const [tab, setTab] = useState<Tab>("search");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [searchResult, setSearchResult] = useState<CommercialSearchResponse | null>(null);
  const [priceStats, setPriceStats] = useState<{ min?: string; max?: string; avg?: string; items: unknown[] } | null>(null);
  const [customerItems, setCustomerItems] = useState<unknown[]>([]);
  const [productItems, setProductItems] = useState<unknown[]>([]);
  const [syncStatus, setSyncStatus] = useState<{ total_items: number; last_sync_at?: string | null } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    try {
      const status = await apiClient.commercialSearchSyncStatus();
      setSyncStatus({ total_items: status.total_items, last_sync_at: status.last_sync_at });
    } catch {
      setSyncStatus(null);
    }
  }, []);

  const runSearch = async (q?: string) => {
    const term = (q ?? query).trim();
    if (!term) return;
    setQuery(term);
    setLoading(true);
    setError(null);
    try {
      if (tab === "search" || tab === "sales") {
        const res = await apiClient.commercialSearch(term);
        setSearchResult(res);
      } else if (tab === "prices") {
        const res = await apiClient.commercialPriceHistory(term);
        setPriceStats({ min: res.min_price ?? undefined, max: res.max_price ?? undefined, avg: res.avg_price ?? undefined, items: res.items });
        setSearchResult(null);
      } else if (tab === "customers") {
        const res = await apiClient.commercialCustomerHistory(term);
        setCustomerItems(res.items);
      } else if (tab === "products") {
        const res = await apiClient.commercialProductHistory(term);
        setProductItems(res.items);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error en búsqueda");
    } finally {
      setLoading(false);
    }
  };

  const runSync = async () => {
    setSyncing(true);
    setError(null);
    try {
      await apiClient.commercialSearchSync({ full_reindex: false });
      await loadStatus();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al sincronizar");
    } finally {
      setSyncing(false);
    }
  };

  useEffect(() => {
    void loadStatus();
  }, [loadStatus]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-1">
          {TABS.map((t) => (
            <Button
              key={t.id}
              size="sm"
              variant={tab === t.id ? "default" : "outline"}
              onClick={() => setTab(t.id)}
            >
              <t.icon className="mr-1 h-3.5 w-3.5" />
              {t.label}
            </Button>
          ))}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link href="/inteligencia/busqueda-comercial">Vista completa</Link>
          </Button>
          <Button variant="outline" size="sm" onClick={() => void runSync()} disabled={syncing}>
            <RefreshCw className={cn("mr-1 h-3.5 w-3.5", syncing && "animate-spin")} />
            Sincronizar Odoo
          </Button>
        </div>
      </div>

      {syncStatus && (
        <p className="text-xs text-muted-foreground">
          Índice: {syncStatus.total_items} registros
          {syncStatus.last_sync_at ? ` · Última sync: ${new Date(syncStatus.last_sync_at).toLocaleString()}` : " · Sin sincronizar aún"}
        </p>
      )}

      <div className="flex gap-2">
        <input
          className="flex-1 rounded-md border border-input px-3 py-2 text-sm"
          placeholder="Buscar historial comercial desde Odoo…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void runSearch()}
        />
        <Button onClick={() => void runSearch()} disabled={loading}>
          <Search className="mr-1 h-4 w-4" />
          Buscar
        </Button>
      </div>

      <div className="flex flex-wrap gap-1">
        {SAMPLE_QUERIES.map((q) => (
          <Button key={q} size="sm" variant="ghost" className="h-7 text-xs" onClick={() => void runSearch(q)}>
            {q}
          </Button>
        ))}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {(tab === "search" || tab === "sales") && searchResult && (
        <SearchResults result={searchResult} />
      )}

      {tab === "prices" && priceStats && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              Historial de precios
            </CardTitle>
            {(priceStats.min || priceStats.max) && (
              <p className="text-xs text-muted-foreground">
                Rango: {priceStats.min ?? "—"} – {priceStats.max ?? "—"}
                {priceStats.avg ? ` · Promedio: ${priceStats.avg}` : ""}
              </p>
            )}
          </CardHeader>
          <CardContent className="space-y-2">
            {(priceStats.items as Record<string, unknown>[]).map((row, i) => (
              <div key={i} className="rounded border px-2 py-1.5 text-xs">
                <p className="font-medium">{String(row.product_name ?? "—")}</p>
                <p className="text-muted-foreground">
                  {String(row.customer_name ?? "—")} · {String(row.unit_price ?? "—")} {String(row.currency ?? "")} · {String(row.date ?? "—")}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {tab === "customers" && customerItems.length > 0 && (
        <Card>
          <CardHeader><CardTitle className="text-base">Historial por cliente</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {(customerItems as Record<string, unknown>[]).map((row, i) => (
              <div key={i} className="rounded border px-2 py-1.5 text-xs">
                <p className="font-medium">{String(row.customer_name ?? "—")}</p>
                <p className="text-muted-foreground">
                  {String(row.product_name ?? "—")} · {String(row.purchase_count ?? 0)} compras · {String(row.total_amount ?? "—")}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {tab === "products" && productItems.length > 0 && (
        <Card>
          <CardHeader><CardTitle className="text-base">Historial por producto</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {(productItems as Record<string, unknown>[]).map((row, i) => (
              <div key={i} className="rounded border px-2 py-1.5 text-xs">
                <p className="font-medium">{String(row.product_name ?? "—")}</p>
                <p className="text-muted-foreground">
                  {String(row.sale_count ?? 0)} ventas · prom. {String(row.avg_unit_price ?? "—")} · último {String(row.last_sale_date ?? "—")}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {!loading && searchResult && searchResult.total === 0 && !searchResult.index_available && (
        <Card>
          <CardContent className="py-6 text-sm text-muted-foreground text-center">
            {searchResult.message ?? "Ejecute sincronización Odoo para indexar historial comercial."}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function SearchResults({ result }: { result: CommercialSearchResponse }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          {result.total} resultados · fuente Odoo
          {result.target_category && (
            <span className="ml-2 text-xs font-normal text-muted-foreground">({result.target_category})</span>
          )}
        </CardTitle>
        {result.message && <p className="text-xs text-muted-foreground">{result.message}</p>}
      </CardHeader>
      <CardContent className="space-y-2">
        {result.items.map((item) => (
          <ResultRow key={item.id} item={item} />
        ))}
      </CardContent>
    </Card>
  );
}

function ResultRow({ item }: { item: CommercialSearchItem }) {
  return (
    <div className="rounded-lg border px-3 py-2 text-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-medium">{item.product_name || item.description || item.customer_name || "—"}</p>
          <p className="text-xs text-muted-foreground">
            {item.customer_name && <span>{item.customer_name} · </span>}
            {item.document_type}: {item.document_number ?? "—"}
            {item.date && <span> · {item.date}</span>}
          </p>
        </div>
        <div className="text-right text-xs">
          {item.unit_price && (
            <p className="font-semibold">
              {item.currency ?? "RD$"}{item.unit_price}
            </p>
          )}
          {item.margin_pct && <p className="text-muted-foreground">Margen {item.margin_pct}%</p>}
          <p className="text-muted-foreground">Score {item.relevance_score}</p>
        </div>
      </div>
      <p className="mt-1 text-[10px] text-muted-foreground">
        Odoo · {item.source_model} #{item.source_id}
        {item.salesperson && ` · ${item.salesperson}`}
        {item.supplier_name && ` · Prov: ${item.supplier_name}`}
      </p>
    </div>
  );
}
