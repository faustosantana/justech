"use client";

import Link from "next/link";
import { ExternalLink, RefreshCw, Search } from "lucide-react";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { KnowledgeGraphPanel } from "@/components/search/knowledge-graph-panel";
import {
  ALL_ENTERPRISE_SOURCE_IDS,
  SourceMultiSelect,
  sourcesForApi,
} from "@/components/search/source-multi-select";
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

export function GlobalSearchSection() {
  return (
    <Suspense fallback={<p className="text-sm text-muted-foreground">{m.common.loading}</p>}>
      <GlobalSearchSectionInner />
    </Suspense>
  );
}

function GlobalSearchSectionInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialQ = searchParams.get("q") ?? "";

  const [query, setQuery] = useState(initialQ);
  const [selectedSources, setSelectedSources] = useState<string[]>([...ALL_ENTERPRISE_SOURCE_IDS]);
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
        sources: sourcesForApi(selectedSources),
        type: typeFilter || undefined,
        company: companyFilter || undefined,
      });
      setResult(res);
    } catch (err) {
      if (err instanceof Error && err.message === "UNAUTHORIZED") return;
      setResult(null);
      setError(
        err instanceof ApiError
          ? err.message
          : "No se pudo completar la búsqueda. Verifica tu conexión e intenta de nuevo.",
      );
    } finally {
      setLoading(false);
    }
  }, [router, query, selectedSources, typeFilter, companyFilter]);

  useEffect(() => {
    setQuery(initialQ);
  }, [initialQ]);

  useEffect(() => {
    if (initialQ.trim().length >= 2) void runSearch(initialQ);
  }, [initialQ, selectedSources, typeFilter, companyFilter, runSearch]);

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
    return result.groups.filter((group) => !typeFilter || group.type === typeFilter);
  }, [result, typeFilter]);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const q = query.trim();
    if (q.length < 2) return;
    router.push(`/apps/documentos/busqueda?view=list&q=${encodeURIComponent(q)}`);
    void runSearch(q);
  };

  return (
    <div className="space-y-6">
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

      <div className="grid gap-6 lg:grid-cols-[200px_1fr_280px]">
        <aside className="space-y-3 lg:sticky lg:top-4 lg:self-start">
          <p className="text-xs font-medium uppercase text-muted-foreground">Filtros</p>
          <SourceMultiSelect selected={selectedSources} onChange={setSelectedSources} />
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="h-9 w-full rounded-md border border-border bg-background px-3 text-sm"
          >
            <option value="">{m.search.allTypes}</option>
            {Object.entries(TYPE_LABELS).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
          {companies.length > 0 && (
            <select
              value={companyFilter}
              onChange={(e) => setCompanyFilter(e.target.value)}
              className="h-9 w-full rounded-md border border-border bg-background px-3 text-sm"
            >
              <option value="">{m.search.allCompanies}</option>
              {companies.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          )}
          <Button variant="outline" size="sm" className="w-full" onClick={() => void runSearch()} disabled={loading}>
            <RefreshCw className={cn("mr-2 h-4 w-4", loading && "animate-spin")} />
            {m.common.refresh}
          </Button>
        </aside>

        <div className="min-w-0 space-y-4">
          {error && (
            <Card className="border-destructive/40">
              <CardContent className="py-4 text-sm text-destructive">{error}</CardContent>
            </Card>
          )}
          {result && (
            <p className="text-sm text-muted-foreground">
              {result.total} {m.search.resultsFor} «{result.query}»
            </p>
          )}
          {filteredGroups.map((group) => (
            <Card key={group.type}>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">
                  {group.label}
                  <span className="ml-2 text-sm font-normal text-muted-foreground">({group.count})</span>
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
                      {item.subtitle && <p className="text-sm text-muted-foreground">{item.subtitle}</p>}
                    </div>
                    <ExternalLink className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" />
                  </Link>
                ))}
              </CardContent>
            </Card>
          ))}
        </div>

        <aside className="hidden lg:block">
          <KnowledgeGraphPanel
            graph={result?.knowledge_graph ?? null}
            entities={result?.resolved_entities}
            query={result?.query}
          />
        </aside>
      </div>
    </div>
  );
}
