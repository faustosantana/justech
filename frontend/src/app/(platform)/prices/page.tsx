"use client";

import { ExternalLink, GitCompare, Search } from "lucide-react";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { t } from "@/i18n";
import { ApiError, apiClient } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import type { PriceCompareResponse, PriceSearchResponse } from "@/lib/prices";

const m = t();

export default function PricesPage() {
  return (
    <Suspense
      fallback={
        <AppShell title={m.prices.title} description={m.prices.description}>
          <p className="text-sm text-muted-foreground">{m.common.loading}</p>
        </AppShell>
      }
    >
      <PricesPageContent />
    </Suspense>
  );
}

function PricesPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [query, setQuery] = useState(searchParams.get("q") ?? "");
  const [marca, setMarca] = useState(searchParams.get("marca") ?? "");
  const [categoria, setCategoria] = useState(searchParams.get("categoria") ?? "");
  const [ramGb, setRamGb] = useState(searchParams.get("ram_gb") ?? "");
  const [storageGb, setStorageGb] = useState(searchParams.get("almacenamiento_gb") ?? "");
  const [stockOnly, setStockOnly] = useState(searchParams.get("stock_disponible") === "true");
  const [loading, setLoading] = useState(false);
  const [compareLoading, setCompareLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PriceSearchResponse | null>(null);
  const [compare, setCompare] = useState<PriceCompareResponse | null>(null);

  const filters = useMemo(
    () => ({
      q: query.trim() || undefined,
      marca: marca.trim() || undefined,
      categoria: categoria.trim() || undefined,
      ram_gb: ramGb ? Number(ramGb) : undefined,
      almacenamiento_gb: storageGb ? Number(storageGb) : undefined,
      stock_disponible: stockOnly || undefined,
      limit: 50,
    }),
    [query, marca, categoria, ramGb, storageGb, stockOnly],
  );

  const runSearch = useCallback(async () => {
    if (!getAccessToken()) {
      router.replace("/login?session=expired");
      return;
    }
    setLoading(true);
    setError(null);
    setCompare(null);
    try {
      const res = await apiClient.searchPrices(filters);
      setResult(res);
    } catch (err) {
      setResult(null);
      setError(err instanceof ApiError ? err.message : m.prices.searchError);
    } finally {
      setLoading(false);
    }
  }, [router, filters]);

  const runCompare = useCallback(async () => {
    if (!getAccessToken()) return;
    setCompareLoading(true);
    setError(null);
    try {
      const res = await apiClient.comparePrices(filters);
      setCompare(res);
    } catch (err) {
      setCompare(null);
      setError(err instanceof ApiError ? err.message : m.prices.compareError);
    } finally {
      setCompareLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    if (searchParams.get("q") || searchParams.get("categoria")) {
      void runSearch();
    }
  }, [searchParams, runSearch]);

  return (
    <AppShell title={m.prices.title} description={m.prices.description}>
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Search className="h-4 w-4" />
              {m.prices.searchTitle}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              <Input
                placeholder={m.prices.queryPlaceholder}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <Input placeholder={m.prices.brandPlaceholder} value={marca} onChange={(e) => setMarca(e.target.value)} />
              <Input
                placeholder={m.prices.categoryPlaceholder}
                value={categoria}
                onChange={(e) => setCategoria(e.target.value)}
              />
              <Input placeholder="RAM (GB)" value={ramGb} onChange={(e) => setRamGb(e.target.value)} />
              <Input placeholder={m.prices.storagePlaceholder} value={storageGb} onChange={(e) => setStorageGb(e.target.value)} />
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={stockOnly} onChange={(e) => setStockOnly(e.target.checked)} />
                {m.prices.stockOnly}
              </label>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => void runSearch()} disabled={loading}>
                {loading ? m.common.loading : m.common.search}
              </Button>
              <Button variant="outline" onClick={() => void runCompare()} disabled={compareLoading}>
                <GitCompare className="mr-2 h-4 w-4" />
                {compareLoading ? m.common.loading : m.prices.compare}
              </Button>
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </CardContent>
        </Card>

        {compare && (
          <Card className="border-primary/30">
            <CardHeader>
              <CardTitle className="text-base">{m.prices.compareResult}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p>{compare.summary}</p>
              {compare.warnings.map((w) => (
                <p key={w} className="text-amber-500">
                  {w}
                </p>
              ))}
            </CardContent>
          </Card>
        )}

        {result && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                {result.total} {m.prices.results}
              </CardTitle>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="py-2 pr-3">{m.prices.colSupplier}</th>
                    <th className="py-2 pr-3">{m.prices.colProduct}</th>
                    <th className="py-2 pr-3">{m.prices.colPrice}</th>
                    <th className="py-2 pr-3">{m.prices.colStock}</th>
                    <th className="py-2 pr-3">Fecha lista</th>
                    <th className="py-2 pr-3">{m.prices.colSource}</th>
                    <th className="py-2">{m.prices.colActions}</th>
                  </tr>
                </thead>
                <tbody>
                  {result.items.map((item) => (
                    <tr key={item.id} className="border-b border-border/50">
                      <td className="py-2 pr-3">{item.supplier ?? "—"}</td>
                      <td className="py-2 pr-3 max-w-xs truncate" title={item.description ?? item.sku ?? ""}>
                        {item.description ?? item.sku ?? "—"}
                      </td>
                      <td className="py-2 pr-3 font-mono">
                        {(item.preferred_price ?? item.price)
                          ? `${item.currency} ${item.preferred_price ?? item.price}`
                          : "—"}
                      </td>
                      <td className="py-2 pr-3">{item.stock ?? "—"}</td>
                      <td className="py-2 pr-3 text-xs text-muted-foreground">
                        {item.source_file_date
                          ? new Date(item.source_file_date).toLocaleDateString("es-DO")
                          : "—"}
                        {item.source_file_date_estimated ? " *" : ""}
                      </td>
                      <td className="py-2 pr-3 text-xs text-muted-foreground">
                        {item.source_filename}
                        {item.source_sheet ? ` / ${item.source_sheet}` : ""}
                      </td>
                      <td className="py-2">
                        <div className="flex gap-1">
                          <Button size="sm" variant="ghost" onClick={() => router.push(`/prices/${item.id}`)}>
                            {m.common.details}
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => router.push(`/documents?search=${encodeURIComponent(item.source_filename)}`)}
                          >
                            <ExternalLink className="h-3 w-3" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        )}
      </div>
    </AppShell>
  );
}
