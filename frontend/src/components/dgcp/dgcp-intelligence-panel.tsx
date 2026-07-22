"use client";

import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Circle,
  Loader2,
  RefreshCw,
  Sparkles,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import {
  ACTION_LABELS,
  hasJaiosIntelligence,
  type DGCPIntelligence,
  type OpportunityAction,
  probabilityBandLabel,
  scoreColor,
  trafficLightBg,
  trafficLightLabel,
} from "@/lib/dgcp";
import { cn } from "@/lib/utils";

const STORAGE_KEY = "jaios-dgcp-analysis-expanded";

interface DGCPIntelligencePanelProps {
  opportunityId: string;
  initial?: DGCPIntelligence | null;
  /** @deprecated Usar acordeón colapsable; se ignora. */
  compact?: boolean;
  onUpdated?: (intel: DGCPIntelligence) => void;
}

function usePersistedExpanded(defaultExpanded = false) {
  const [expanded, setExpandedState] = useState(defaultExpanded);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === "true") setExpandedState(true);
      else if (stored === "false") setExpandedState(false);
    } catch {
      /* ignore */
    }
    setReady(true);
  }, []);

  const setExpanded = useCallback((value: boolean) => {
    setExpandedState(value);
    try {
      localStorage.setItem(STORAGE_KEY, value ? "true" : "false");
    } catch {
      /* ignore */
    }
  }, []);

  const toggle = useCallback(() => {
    setExpandedState((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(STORAGE_KEY, next ? "true" : "false");
      } catch {
        /* ignore */
      }
      return next;
    });
  }, []);

  return { expanded: ready ? expanded : defaultExpanded, setExpanded, toggle, ready };
}

function oportunidadLevelLabel(band: string): string {
  const map: Record<string, string> = {
    alta: "Oportunidad Alta",
    media: "Oportunidad Media",
    baja: "Oportunidad Baja",
  };
  return map[band] ?? "Oportunidad";
}

function humanizeFactorKey(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function isIntelPending(intel: DGCPIntelligence | null): boolean {
  return !intel || (!intel.analyzed_at && (intel.premium_score ?? 0) === 0);
}

function buildCollapsedSummary(intel: DGCPIntelligence, recLabel: string): string {
  const parts: string[] = [];
  const executive = intel.executive ?? {};
  if (executive.summary) parts.push(executive.summary.trim());
  if (intel.participation?.reason) parts.push(intel.participation.reason.trim());
  if (parts.length === 0) {
    parts.push(`Recomendación: ${recLabel}.`);
  }
  return parts.join(" ").slice(0, 280);
}

function recommendationEntries(recommendations: Record<string, unknown>): string[] {
  const items: string[] = [];
  for (const [key, value] of Object.entries(recommendations ?? {})) {
    if (value == null || value === "") continue;
    if (Array.isArray(value)) {
      value.forEach((v) => {
        if (typeof v === "string" && v.trim()) items.push(v.trim());
      });
      continue;
    }
    if (typeof value === "string" && value.trim()) {
      items.push(`${humanizeFactorKey(key)}: ${value.trim()}`);
      continue;
    }
    if (typeof value === "object") {
      items.push(`${humanizeFactorKey(key)}: ${JSON.stringify(value)}`);
    }
  }
  return items.slice(0, 8);
}

export function DGCPIntelligencePanel({
  opportunityId,
  initial,
  onUpdated,
}: DGCPIntelligencePanelProps) {
  const validInitial = hasJaiosIntelligence(initial) ? initial : null;
  const [intel, setIntel] = useState<DGCPIntelligence | null>(validInitial);
  const [loading, setLoading] = useState(!validInitial);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { expanded, setExpanded, toggle } = usePersistedExpanded(false);

  const load = useCallback(
    async (refresh = false) => {
      if (refresh) setRefreshing(true);
      else if (!validInitial) setLoading(true);
      setError(null);
      try {
        const data = refresh
          ? await apiClient.analyzeDGCPIntelligence(opportunityId)
          : await apiClient.getDGCPIntelligence(opportunityId);
        setIntel(data);
        if (!isIntelPending(data)) onUpdated?.(data);
      } catch (err) {
        const msg =
          err instanceof Error && err.message !== "UNAUTHORIZED"
            ? err.message
            : "No se pudo cargar el análisis JAIOS.";
        setError(refresh ? msg : null);
        if (!refresh && validInitial) setIntel(validInitial);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [opportunityId, onUpdated, validInitial],
  );

  useEffect(() => {
    if (validInitial) return;
    void load(false);
  }, [validInitial, load]);

  const participation = intel?.participation ?? { recommendation: "revisar", reason: "" };
  const rec = participation.recommendation as OpportunityAction | string;
  const recLabel = ACTION_LABELS[rec as OpportunityAction] ?? rec;
  const collapsedSummary = intel ? buildCollapsedSummary(intel, recLabel) : "";
  const factorEntries = intel
    ? Object.entries(intel.score_factors ?? {}).sort((a, b) => b[1] - a[1])
    : [];
  const recommendationLines = intel ? recommendationEntries(intel.recommendations ?? {}) : [];

  if (loading && !validInitial) {
    return (
      <Card className="border-primary/20 max-h-[7.5rem]">
        <CardContent className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Cargando análisis guardado…
        </CardContent>
      </Card>
    );
  }

  if (error && refreshing) {
    return (
      <Card className="border-destructive/30 max-h-[7.5rem]">
        <CardContent className="flex items-center justify-between gap-3 py-3 text-sm">
          <span className="text-muted-foreground">{error}</span>
          <Button size="sm" variant="outline" onClick={() => void load(true)}>
            Reintentar
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (isIntelPending(intel)) {
    return (
      <Card className="border-primary/20 max-h-[8rem]">
        <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4 text-sm">
          <span className="text-muted-foreground">
            Sin análisis JAIOS calculado. Use «Actualizar análisis» (puede tardar 1–2 min).
          </span>
          <Button size="sm" variant="outline" disabled={refreshing} onClick={() => void load(true)}>
            {refreshing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Analizando…
              </>
            ) : (
              <>
                <RefreshCw className="mr-2 h-4 w-4" />
                Actualizar análisis
              </>
            )}
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!intel) {
    return null;
  }

  const participationResolved = intel.participation ?? {
    recommendation: "revisar",
    reason: "",
  };
  const expediente = intel.expediente ?? {
    traffic_light: "yellow",
    stage_label: "Sin etapa",
    completeness_pct: 0,
    checklist: [],
  };
  const executive = intel.executive ?? {};
  const score = intel.premium_score ?? 0;
  const levelLabel = oportunidadLevelLabel(intel.probability_band ?? "baja");

  return (
    <Card
      className={cn(
        "border-primary/25 transition-[max-height] duration-200",
        trafficLightBg(expediente.traffic_light),
        expanded ? "" : "max-h-[8rem] overflow-hidden",
      )}
    >
      <CardHeader
        className="cursor-pointer select-none space-y-0 px-4 py-3 pb-2"
        onClick={toggle}
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            toggle();
          }
        }}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1 space-y-1">
            <CardTitle className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm font-semibold sm:text-base">
              {expanded ? (
                <ChevronUp className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
              ) : (
                <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
              )}
              <Sparkles className="h-4 w-4 shrink-0 text-primary" aria-hidden />
              <span className="truncate">
                Análisis JAIOS ({score}/100 — {levelLabel})
              </span>
            </CardTitle>
            {!expanded && (
              <p className="line-clamp-2 text-xs leading-snug text-muted-foreground">{collapsedSummary}</p>
            )}
            {expanded && intel.analyzed_at && (
              <p className="text-xs text-muted-foreground">
                Actualizado {new Date(intel.analyzed_at).toLocaleString("es-DO")}
              </p>
            )}
          </div>
          <div className="flex shrink-0 items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
            <Badge variant="outline" className={cn("text-xs", scoreColor(score))}>
              {score}/100
            </Badge>
            <Badge variant="muted" className="hidden text-xs sm:inline-flex">
              {probabilityBandLabel(intel.probability_band ?? "baja")}
            </Badge>
            <Button
              size="sm"
              variant="ghost"
              className="h-8 w-8 p-0"
              disabled={refreshing}
              onClick={() => void load(true)}
              title="Actualizar análisis"
            >
              <RefreshCw className={cn("h-4 w-4", refreshing && "animate-spin")} />
            </Button>
          </div>
        </div>
      </CardHeader>

      {!expanded ? (
        <div className="flex items-center justify-between gap-2 px-4 pb-3 pt-0">
          <div className="flex min-w-0 items-center gap-2 text-xs text-muted-foreground">
            <TrafficLight light={expediente.traffic_light} />
            <span className="truncate">{recLabel}</span>
          </div>
          <Button
            size="sm"
            variant="outline"
            className="h-7 shrink-0 text-xs"
            onClick={(e) => {
              e.stopPropagation();
              setExpanded(true);
            }}
          >
            Expandir análisis
          </Button>
        </div>
      ) : (
        <CardContent className="space-y-4 px-4 pb-4 pt-0 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <TrafficLight light={expediente.traffic_light} />
            <span className="font-medium">{expediente.stage_label}</span>
            <span className="text-muted-foreground">· {expediente.completeness_pct}% expediente</span>
          </div>

          <div className="rounded-lg border border-border/60 bg-background/60 p-3 space-y-2">
            <p className="font-medium text-foreground">
              Recomendación: <span className="text-primary">{recLabel}</span>
            </p>
            <p className="text-muted-foreground">{participationResolved.reason}</p>
            {executive.summary && <p className="text-foreground leading-relaxed">{executive.summary}</p>}
          </div>

          {(executive.questions || executive.key_questions) && (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Preguntas clave
              </p>
              <ul className="space-y-1.5">
                {executive.questions
                  ? Object.values(executive.questions).map((q) => (
                      <li key={q.label} className="border-l-2 border-primary/30 pl-3 text-muted-foreground">
                        <span className="font-medium text-foreground">{q.label}</span>
                        {" — "}
                        {typeof q.detail === "string" ? q.detail : String(q.detail ?? "")}
                      </li>
                    ))
                  : (executive.key_questions ?? []).map((q) => (
                      <li key={q} className="border-l-2 border-primary/30 pl-3 text-muted-foreground">
                        {q}
                      </li>
                    ))}
              </ul>
            </div>
          )}

          <div className="grid gap-3 sm:grid-cols-2">
            <IntelList
              title="Riesgos"
              items={(executive.risks ?? []).map((r) => (typeof r === "string" ? r : r.descripcion))}
              variant="risk"
            />
            <IntelList title="Oportunidades" items={executive.opportunities ?? []} variant="ok" />
          </div>

          {recommendationLines.length > 0 && (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Recomendaciones
              </p>
              <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
                {recommendationLines.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </div>
          )}

          {factorEntries.length > 0 && (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Factores de decisión
              </p>
              <div className="grid gap-1.5 sm:grid-cols-2">
                {factorEntries.map(([key, pts]) => (
                  <div
                    key={key}
                    className="flex items-center justify-between rounded-md border border-border/50 px-2.5 py-1.5 text-xs"
                  >
                    <span className="text-muted-foreground">{humanizeFactorKey(key)}</span>
                    <span className="font-medium tabular-nums">+{pts}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(expediente.checklist?.length ?? 0) > 0 && (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Checklist corporativo (análisis)
              </p>
              <div className="grid gap-1 sm:grid-cols-2">
                {expediente.checklist.map((item) => (
                  <ChecklistRow key={item.id} label={item.label} status={item.status} />
                ))}
              </div>
            </div>
          )}

          {(executive.next_actions?.length ?? 0) > 0 && (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Próximas acciones
              </p>
              <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
                {executive.next_actions!.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="rounded-lg border border-border/50 bg-muted/20 px-3 py-2 text-xs text-muted-foreground">
            <p className="font-medium text-foreground">Historial de análisis</p>
            <p className="mt-1">
              {intel.analyzed_at
                ? `Último cálculo: ${new Date(intel.analyzed_at).toLocaleString("es-DO")}.`
                : "Sin fecha de análisis registrada."}{" "}
              Use la pestaña Historial del expediente para ver cambios operativos.
            </p>
          </div>

          <div className="flex justify-end">
            <Button size="sm" variant="ghost" className="text-xs" onClick={() => setExpanded(false)}>
              Contraer análisis
            </Button>
          </div>
        </CardContent>
      )}
    </Card>
  );
}

function TrafficLight({ light }: { light: string }) {
  const colors = {
    green: "bg-success",
    yellow: "bg-warning",
    red: "bg-destructive",
  } as const;
  return (
    <span
      className={cn(
        "inline-block h-3 w-3 shrink-0 rounded-full",
        colors[light as keyof typeof colors] ?? "bg-muted",
      )}
      title={trafficLightLabel(light)}
    />
  );
}

function ChecklistRow({ label, status }: { label: string; status: string }) {
  const Icon =
    status === "ok" ? CheckCircle2 : status === "expired" ? AlertTriangle : XCircle;
  const color =
    status === "ok"
      ? "text-success"
      : status === "expired"
        ? "text-warning"
        : "text-muted-foreground";
  return (
    <div className="flex items-center gap-2 py-0.5 text-xs">
      <Icon className={cn("h-3.5 w-3.5 shrink-0", color)} />
      <span>{label}</span>
    </div>
  );
}

function IntelList({
  title,
  items,
  variant,
}: {
  title: string;
  items: string[];
  variant: "risk" | "ok";
}) {
  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-border/50 p-3 text-xs text-muted-foreground">
        {title}: ninguno
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-border/50 p-3">
      <p className="mb-2 text-xs font-semibold">{title}</p>
      <ul className="space-y-1">
        {items.slice(0, 5).map((item) => (
          <li key={item} className="flex items-start gap-1.5 text-xs text-muted-foreground">
            {variant === "risk" ? (
              <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-warning" />
            ) : (
              <Circle className="mt-0.5 h-3 w-3 shrink-0 text-primary" />
            )}
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
