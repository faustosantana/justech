"use client";

import Link from "next/link";
import { ExternalLink, RefreshCw, Search } from "lucide-react";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { t } from "@/i18n";
import { ApiError, apiClient } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import {
  SOURCE_LABELS,
  TYPE_LABELS,
  type EnterpriseSearchResponse,
  type SearchResultGroup,
} from "@/lib/search";
import { cn } from "@/lib/utils";

const m = t();

export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <AppShell title={m.search.title} description={m.search.description}>
          <p className="text-sm text-muted-foreground">{m.common.loading}</p>
        </AppShell>
      }
    >
      <SearchPageContent />
    </Suspense>
  );
}

function SearchPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialQ = searchParams.get("q") ?? "";

  const [query, setQuery] = useState(initialQ);
  const [sourceFilter, setSourceFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [companyFilter, setCompanyFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<EnterpriseSearchResponse | null>(null);

  const runSearch = useCallback(async (qOverride?: string) => {
    if (!getAccessToken()) {
      router.replace("/login?session=expired");
      return;
    }
    const q = (qOverride ?? query).trim();
    if (q.length < 2) {
      setResult(null);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.enterpriseSearch({
        q,
        source: sourceFilter || undefined,
        type: typeFilter || undefined,
        company: companyFilter || undefined,
      });
      setResult(res);
    } catch (err) {
      if (err instanceof Error && err.message === "UNAUTHORIZED") {
        return;
      }
      setResult(null);
      setError(
        err instanceof ApiError
          ? err.message
          : "No se pudo completar la búsqueda. Verifica tu conexión e intenta de nuevo.",
      );
    } finally {
      setLoading(false);
    }
  }, [router, query, sourceFilter, typeFilter, companyFilter]);

  useEffect(() => {
    setQuery(initialQ);
  }, [initialQ]);

  useEffect(() => {
    if (initialQ.trim().length >= 2) {
      void runSearch(initialQ);
    }
  }, [initialQ, sourceFilter, typeFilter, companyFilter, runSearch]);

  const companies = useMemo(() => {
    if (!result) return [];
    const set = new Set<string>();
    for (const group of result.groups) {
      for (const item of group.items) {
        if (item.company) set.add(item.company);
      }
    }
    return Array.from(set).sort();
  }, [result]);

  const filteredGroups: SearchResultGroup[] = useMemo(() => {
    if (!result) return [];
    return result.groups.filter((group) => {
      if (typeFilter && group.type !== typeFilter) return false;
      return true;
    });
  }, [result, typeFilter]);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const q = query.trim();
    if (q.length < 2) return;
    router.push(`/search?q=${encodeURIComponent(q)}`);
    void runSearch(q);
  };

  return (
    <AppShell title={m.search.title} description={m.search.description}>
      <div className="mx-auto max-w-5xl space-y-6">
        <form onSubmit={handleSubmit} className="flex gap-3">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={m.search.placeholder}
              className="h-11 w-full rounded-lg border border-border bg-card pl-10 pr-4 text-sm outline-none ring-primary/20 focus:ring-2"
            />
          </div>
          <Button type="submit" disabled={loading || query.trim().length < 2}>
            {loading ? m.common.loading : m.common.search}
          </Button>
        </form>

        <div className="flex flex-wrap gap-3">
          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            className="h-9 rounded-md border border-border bg-background px-3 text-sm"
            aria-label={m.search.filterSource}
          >
            <option value="">{m.search.allSources}</option>
            {Object.entries(SOURCE_LABELS).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>

          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="h-9 rounded-md border border-border bg-background px-3 text-sm"
            aria-label={m.search.filterType}
          >
            <option value="">{m.search.allTypes}</option>
            {Object.entries(TYPE_LABELS).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>

          {companies.length > 0 && (
            <select
              value={companyFilter}
              onChange={(e) => setCompanyFilter(e.target.value)}
              className="h-9 rounded-md border border-border bg-background px-3 text-sm"
              aria-label={m.search.filterCompany}
            >
              <option value="">{m.search.allCompanies}</option>
              {companies.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          )}

          <Button variant="outline" size="sm" onClick={() => void runSearch()} disabled={loading}>
            <RefreshCw className={cn("mr-2 h-4 w-4", loading && "animate-spin")} />
            {m.common.refresh}
          </Button>
        </div>

        {error && (
          <Card className="border-destructive/40">
            <CardContent className="py-4 text-sm text-destructive">{error}</CardContent>
          </Card>
        )}

        {result && (
          <p className="text-sm text-muted-foreground">
            {result.total} {m.search.resultsFor} «{result.query}»
            {result.future_sources.length > 0 && (
              <span className="ml-2 text-xs">
                ({m.search.futureNote})
              </span>
            )}
          </p>
        )}

        {!loading && !error && query.trim().length >= 2 && result?.total === 0 && (
          <Card>
            <CardContent className="py-10 text-center text-muted-foreground">
              {m.common.noResults}
            </CardContent>
          </Card>
        )}

        {filteredGroups.map((group) => (
          <Card key={group.type}>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">
                {group.label}
                <span className="ml-2 text-sm font-normal text-muted-foreground">
                  ({group.count})
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {group.items.map((item) => (
                <Link
                  key={`${item.type}-${item.id}`}
                  href={item.url}
                  className="flex items-start justify-between gap-4 rounded-lg border border-border/60 p-3 transition hover:bg-muted/50"
                >
                  <div className="min-w-0 flex-1">
                    <p className="font-medium">{item.title}</p>
                    {item.subtitle && (
                      <p className="text-sm text-muted-foreground">{item.subtitle}</p>
                    )}
                    {item.description && (
                      <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
                        {item.description}
                      </p>
                    )}
                    <div className="mt-2 flex flex-wrap gap-2 text-[10px] uppercase tracking-wide text-muted-foreground">
                      <span>{SOURCE_LABELS[item.source] ?? item.source}</span>
                      {item.company && <span>· {item.company}</span>}
                      <span>· {item.type}</span>
                    </div>
                  </div>
                  <ExternalLink className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" />
                </Link>
              ))}
            </CardContent>
          </Card>
        ))}
      </div>
    </AppShell>
  );
}
