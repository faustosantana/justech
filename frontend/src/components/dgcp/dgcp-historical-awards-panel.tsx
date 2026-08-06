"use client";

import {
  AlertCircle,
  Database,
  ExternalLink,
  Lightbulb,
  Loader2,
  RefreshCw,
  TrendingUp,
  Trophy,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { useDgcpExpedienteContext } from "@/components/dgcp/dgcp-expediente-context";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import { isDgcpAutoExpedienteContextEnabled } from "@/lib/dgcp-expediente-context";
import {
  formatCurrency,
  formatDate,
  isDGCPOperationalInterest,
  sanitizeClassificationReason,
  sanitizeKeywordList,
  type DGCPHistoricalSimilarResponse,
  type DGCPOpportunity,
} from "@/lib/dgcp";
import { cn } from "@/lib/utils";

interface Props {
  opportunity: DGCPOpportunity;
}

function institutionCodeFromOpportunity(opp: DGCPOpportunity): string | number | undefined {
  const info = opp.full_info as Record<string, unknown> | undefined;
  const code = info?.codigo_unidad_compra;
  if (code !== undefined && code !== null && String(code).trim()) {
    return code as string | number;
  }
  return undefined;
}

export function DGCPHistoricalAwardsPanel({ opportunity }: Props) {
  const ctx = useDgcpExpedienteContext();
  const autoEnabled = isDgcpAutoExpedienteContextEnabled();
  const [data, setData] = useState<DGCPHistoricalSimilarResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [reindexing, setReindexing] = useState(false);
  const [showAll, setShowAll] = useState(false);

  const eligible = isDGCPOperationalInterest(opportunity.status);
  const useAuto = autoEnabled && ctx?.enabled;

  const loadCache = useCallback(async () => {
    if (useAuto) return;
    setLoading(true);
    try {
      const result = await apiClient.getDGCPHistoricalSimilar(opportunity.id);
      setData(result);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [opportunity.id, useAuto]);

  useEffect(() => {
    if (useAuto) {
      if (ctx?.historical) setData(ctx.historical);
      return;
    }
    if (eligible) void loadCache();
  }, [useAuto, ctx?.historical, eligible, loadCache]);

  async function runSearch(refresh = false) {
    if (useAuto && ctx) {
      setSearching(true);
      try {
        await ctx.refresh(refresh);
      } finally {
        setSearching(false);
      }
      return;
    }
    setSearching(true);
    try {
      const result = await apiClient.searchDGCPHistoricalSimilar(opportunity.id, {
        refresh,
        limit: 10,
      });
      setData(result);
    } finally {
      setSearching(false);
    }
  }

  async function runReindex() {
    setReindexing(true);
    try {
      const institutionCode = institutionCodeFromOpportunity(opportunity);
      await apiClient.reindexDGCPHistoricalAwards({
        institution_code: institutionCode,
        institution_name: opportunity.institution ?? undefined,
        max_pages: 60,
      });
      await runSearch(true);
    } finally {
      setReindexing(false);
    }
  }

  const activeData = useAuto && ctx?.historical ? ctx.historical : data;
  const isLoading = useAuto ? ctx?.loading && !activeData : loading && !activeData;
  const indexMeta = activeData?.index_meta;

  const visibleMatches = activeData?.matches
    ? showAll
      ? activeData.matches
      : activeData.matches.slice(0, 10)
    : [];

  const otherMatches = activeData?.other_institution_matches ?? [];
  const visibleOther = showAll ? otherMatches : otherMatches.slice(0, 5);

  const priceRec = activeData?.price_recommendation;
  const indicators = activeData?.indicators;
  const hasInstitutionData = (indexMeta?.institution_indexed ?? 0) > 0;
  const isEmpty = activeData?.status === "empty" && visibleMatches.length === 0;

  if (!eligible) {
    return (
      <Card>
        <CardContent className="pt-6 text-sm text-muted-foreground">
          Marque interés operativo en el proceso para habilitar el histórico de compras de esta
          institución.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {useAuto && ctx?.loading && !activeData && (
        <Card>
          <CardContent className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin shrink-0" />
            Indexando adjudicaciones DGCP de la institución…
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3 pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-primary" />
            Histórico de compras — {opportunity.institution}
          </CardTitle>
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={reindexing || searching || isLoading}
              title="Descarga adjudicaciones DGCP de esta institución e indexa en JAIOS"
              onClick={() => void runReindex()}
            >
              <Database className={cn("mr-1.5 h-3.5 w-3.5", reindexing && "animate-spin")} />
              {reindexing ? "Reindexando…" : "Reindexar histórico"}
            </Button>
            <Button size="sm" disabled={searching || isLoading} title="Busca procesos similares ya adjudicados" onClick={() => void runSearch(true)}>
              <RefreshCw className={cn("mr-1.5 h-3.5 w-3.5", searching && "animate-spin")} />
              {searching ? "Actualizando…" : "Actualizar búsqueda"}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading && !activeData && (
            <p className="text-sm text-muted-foreground">Cargando histórico indexado…</p>
          )}

          {indexMeta && (
            <div className="rounded-lg border border-border/60 bg-muted/20 px-3 py-2 text-xs text-muted-foreground flex flex-wrap gap-x-4 gap-y-1">
              <span>
                <strong className="text-foreground">{indexMeta.institution_indexed}</strong> adjudicaciones
                de esta institución
              </span>
              <span>
                <strong className="text-foreground">{indexMeta.total_indexed}</strong> filas indexadas (global)
              </span>
              {indexMeta.last_indexed_at && (
                <span>Última indexación: {formatDate(indexMeta.last_indexed_at)}</span>
              )}
              <span>Fuente: {indexMeta.source}</span>
            </div>
          )}

          {activeData?.keywords_used && activeData.keywords_used.length > 0 && (
            <p className="text-xs text-muted-foreground">
              Palabras clave del proceso: {sanitizeKeywordList(activeData.keywords_used).slice(0, 10).join(", ")}
              {activeData.keywords_used.length > 10 ? "…" : ""}
            </p>
          )}

          {isEmpty && (
            <div className="rounded-lg border border-border/60 bg-muted/30 p-4 text-sm space-y-3">
              <p className="flex items-center gap-2 font-medium">
                <AlertCircle className="h-4 w-4 text-muted-foreground shrink-0" />
                {hasInstitutionData
                  ? activeData?.message
                  : "No hay adjudicaciones indexadas para esta institución."}
              </p>
              <p className="text-xs text-muted-foreground">
                Siguiente paso: pulse «Reindexar histórico» para importar adjudicaciones DGCP de {opportunity.institution}.
              </p>
            </div>
          )}

          {activeData?.error_message && (
            <p className="text-sm text-destructive">{activeData.error_message}</p>
          )}

          {activeData?.searched_at && !isEmpty && (
            <p className="text-xs text-muted-foreground">
              {activeData.cached ? "Resultado en caché" : "Búsqueda en vivo"} ·{" "}
              {formatDate(activeData.searched_at)}
              {activeData.expires_at && ` · válido hasta ${formatDate(activeData.expires_at)}`}
            </p>
          )}

          {indicators && activeData && activeData.total_matches > 0 && (
            <div className="grid gap-3 sm:grid-cols-3">
              <MetricCard
                label="Precio unit. promedio"
                value={
                  indicators.avg_unit_price
                    ? formatCurrency(indicators.avg_unit_price, "DOP")
                    : "—"
                }
              />
              <MetricCard
                label="Último precio adjudicado"
                value={
                  indicators.last_awarded_unit_price
                    ? formatCurrency(indicators.last_awarded_unit_price, "DOP")
                    : "—"
                }
              />
              <MetricCard label="Coincidencias" value={String(activeData.total_matches)} />
            </div>
          )}

          {priceRec && (
            <Card className="border-primary/20 bg-primary/5">
              <CardContent className="pt-4 space-y-1 text-sm">
                <p className="font-medium flex items-center gap-2">
                  <Lightbulb className="h-4 w-4 text-primary" />
                  Recomendación de precio
                </p>
                <p>{priceRec.summary}</p>
              </CardContent>
            </Card>
          )}

          {activeData?.ai_insights && activeData.ai_insights.length > 0 && visibleMatches.length > 0 && (
            <ul className="space-y-1.5">
              {activeData.ai_insights
                .filter((insight) => !priceRec?.summary || !insight.includes(priceRec.summary.slice(0, 40)))
                .map((insight) => (
                <li
                  key={insight}
                  className="flex items-start gap-2 text-sm rounded-md border border-border/50 px-3 py-2"
                >
                  <Lightbulb className="h-3.5 w-3.5 text-primary mt-0.5 shrink-0" />
                  {insight}
                </li>
              ))}
            </ul>
          )}

          {indicators?.most_frequent_supplier && visibleMatches.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Trophy className="h-4 w-4 text-amber-500" />
                  Proveedor más frecuente
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="font-medium">{indicators.most_frequent_supplier}</p>
              </CardContent>
            </Card>
          )}

          {visibleMatches.length > 0 && (
            <MatchesTable
              title={`Misma institución — ${opportunity.institution}`}
              matches={visibleMatches}
            />
          )}

          {visibleOther.length > 0 && (
            <SimilarProcessesTable matches={visibleOther} />
          )}

          {activeData && (activeData.other_institution_matches?.length ?? 0) === 0 && !isEmpty && (
            <Card className="border-border/60">
              <CardContent className="py-4 text-sm text-muted-foreground">
                <p className="font-medium text-foreground">Procesos similares — otras instituciones</p>
                <p className="mt-1 text-xs">
                  No se encontraron procesos suficientemente similares
                  actual. Solo se muestran coincidencias técnicas claras (misma familia de producto,
                  palabras clave específicas o UNSPSC).
                </p>
              </CardContent>
            </Card>
          )}

          {activeData && activeData.matches.length > 10 && !showAll && (
            <Button size="sm" variant="ghost" onClick={() => setShowAll(true)}>
              Ver más ({activeData.matches.length})
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function SimilarProcessesTable({
  matches,
}: {
  matches: DGCPHistoricalSimilarResponse["matches"];
}) {
  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold uppercase text-muted-foreground">
        Procesos similares — otras instituciones
      </p>
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/40 text-left text-xs uppercase text-muted-foreground">
              <th className="px-3 py-2">Código</th>
              <th className="px-3 py-2">Institución</th>
              <th className="px-3 py-2">Fecha</th>
              <th className="px-3 py-2">Objeto</th>
              <th className="px-3 py-2">Productos / ítems</th>
              <th className="px-3 py-2">Score</th>
              <th className="px-3 py-2">Por qué es similar</th>
              <th className="px-3 py-2">Palabras coincidentes</th>
              <th className="px-3 py-2">Fuente</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {matches.map((m) => (
              <tr key={m.id} className="border-b border-border/40 hover:bg-muted/20 align-top">
                <td className="px-3 py-2 font-mono text-xs whitespace-nowrap">{m.process_code}</td>
                <td className="px-3 py-2 max-w-[140px] text-xs">{m.buyer_institution}</td>
                <td className="px-3 py-2 whitespace-nowrap text-xs">
                  {m.award_date ? formatDate(m.award_date) : "—"}
                </td>
                <td className="px-3 py-2 max-w-[180px] text-xs">
                  {m.contract_object ?? m.item_description ?? "—"}
                </td>
                <td className="px-3 py-2 max-w-[160px] text-xs text-muted-foreground">
                  {m.item_description ?? "—"}
                </td>
                <td className="px-3 py-2 whitespace-nowrap text-xs">
                  <Badge variant="secondary" className="text-[10px]">
                    {m.similarity_score} ({m.similarity_level})
                  </Badge>
                </td>
                <td className="px-3 py-2 max-w-[180px] text-[10px] text-muted-foreground">
                  {m.match_reasons.length > 0 ? m.match_reasons.join(" · ") : "—"}
                </td>
                <td className="px-3 py-2 max-w-[140px] text-[10px]">
                  {(m.matched_keywords ?? []).length > 0
                    ? (m.matched_keywords ?? []).join(", ")
                    : "—"}
                </td>
                <td className="px-3 py-2">
                  <Badge variant="outline" className="text-[10px] whitespace-nowrap">
                    {m.source?.includes("dgcp") ? "DGCP" : m.source ?? "DGCP"}
                  </Badge>
                </td>
                <td className="px-3 py-2">
                  {m.contract_url ? (
                    <a
                      href={m.contract_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline inline-flex items-center gap-1 text-xs"
                      title="Ver contrato en DGCP"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function MatchesTable({
  title,
  matches,
  muted = false,
}: {
  title: string;
  matches: DGCPHistoricalSimilarResponse["matches"];
  muted?: boolean;
}) {
  return (
    <div className="space-y-2">
      <p className={cn("text-xs font-semibold uppercase", muted ? "text-muted-foreground" : "text-primary")}>
        {title}
      </p>
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/40 text-left text-xs uppercase text-muted-foreground">
              <th className="px-3 py-2">Fecha adj.</th>
              <th className="px-3 py-2">Institución</th>
              <th className="px-3 py-2">Proceso</th>
              <th className="px-3 py-2">Objeto / ítem</th>
              <th className="px-3 py-2">Proveedor</th>
              <th className="px-3 py-2">Monto</th>
              <th className="px-3 py-2">Producto</th>
              <th className="px-3 py-2">Fuente</th>
              <th className="px-3 py-2">Días pub→adj</th>
              <th className="px-3 py-2">Por qué coincide</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {matches.map((m) => (
              <tr key={m.id} className="border-b border-border/40 hover:bg-muted/20 align-top">
                <td className="px-3 py-2 whitespace-nowrap text-xs">
                  {m.award_date ? formatDate(m.award_date) : "—"}
                </td>
                <td className="px-3 py-2 max-w-[140px] text-xs">{m.buyer_institution}</td>
                <td className="px-3 py-2 font-mono text-xs whitespace-nowrap">{m.process_code}</td>
                <td className="px-3 py-2 max-w-[200px] text-xs">
                  <p className="line-clamp-2">{m.contract_object ?? m.item_description ?? "—"}</p>
                </td>
                <td className="px-3 py-2 max-w-[120px] truncate text-xs">{m.supplier_name ?? "—"}</td>
                <td className="px-3 py-2 whitespace-nowrap text-xs">
                  {m.awarded_amount ? formatCurrency(m.awarded_amount, "DOP") : "—"}
                </td>
                <td className="px-3 py-2 max-w-[160px] text-xs text-muted-foreground">
                  {m.item_description ?? "—"}
                  {m.quantity && m.unit_measure && (
                    <span className="block text-[10px]">
                      {m.quantity} {m.unit_measure}
                    </span>
                  )}
                </td>
                <td className="px-3 py-2">
                  <Badge variant="outline" className="text-[10px] whitespace-nowrap">
                    DGCP
                  </Badge>
                </td>
                <td className="px-3 py-2 text-xs whitespace-nowrap">
                  {m.publication_to_award_days != null ? `${m.publication_to_award_days} d` : "—"}
                </td>
                <td className="px-3 py-2 max-w-[180px] text-[10px] text-muted-foreground">
                  {m.match_reasons.length > 0 ? m.match_reasons.join(" · ") : "—"}
                </td>
                <td className="px-3 py-2">
                  {m.contract_url ? (
                    <a
                      href={m.contract_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline inline-flex items-center gap-1 text-xs"
                      title="Ver contrato en DGCP"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border/60 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold">{value}</p>
    </div>
  );
}
