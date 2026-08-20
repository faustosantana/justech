"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { RefreshCw, Search, X } from "lucide-react";

import { FunnelStageTabs } from "@/components/dgcp/dgcp-funnel-header";
import { CreateLicitationDialog } from "@/components/dgcp/create-licitation-dialog";
import { MutateButton } from "@/components/permissions/mutate-button";
import { DgcpRpeFilterBar, loadSavedCompanyFilter, loadSavedRpeFilter, resolveCompanyFromRpe } from "@/components/dgcp/dgcp-rpe-filter-bar";
import { KPIGrid } from "@/components/dgcp/kpi-grid";
import { OpportunitiesTable } from "@/components/dgcp/opportunities-table";
import { Button } from "@/components/ui/button";
import { usePlatformAccess } from "@/hooks/use-platform-access";
import { apiClient } from "@/lib/api";
import { useCompanyContext } from "@/lib/company-context";
import type { CompanyProfile } from "@/lib/settings";
import {
  formatDateTime,
  PIPELINE_STATUSES,
  STATUS_LABELS,
  type DGCPOpportunity,
  type DGCPSummary,
  type DGCPProcessUpdateDashboardResponse,
  type OpportunityCompany,
  type OpportunityStatus,
} from "@/lib/dgcp";
import {
  EXPEDIENTE_FUNNEL_STAGES,
  FUNNEL_STAGES,
  FUNNEL_STAGE_LABELS,
  getOpportunityFunnelStage,
  type FunnelStage,
} from "@/lib/dgcp-funnel";
import { dgcpProcessUpdatesEnabled } from "@/lib/dgcp-feature-flags";
import { cn } from "@/lib/utils";

const EMPTY: DGCPSummary = {
  total_opportunities: 0,
  total_potential_amount: "0",
  by_status: {},
  by_company: {},
  by_priority: {},
  amount_by_company: {},
  to_bid: 0,
  to_review: 0,
  discarded: 0,
  won: 0,
  lost: 0,
};

type Mode = "list" | "kanban" | "calendar" | "won";

export function LicitacionesProcesosSection({ mode = "list" }: { mode?: Mode }) {
  const { access } = usePlatformAccess();
  const { context: companyCtx, setSelection } = useCompanyContext();
  const searchParams = useSearchParams();
  const urlQuery = searchParams.get("q")?.trim() ?? "";
  const [items, setItems] = useState<DGCPOpportunity[]>([]);
  const [summary, setSummary] = useState<DGCPSummary>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [funnelFilter, setFunnelFilter] = useState<FunnelStage | "">("");
  const [statusFilter, setStatusFilter] = useState<OpportunityStatus | "">("");
  const [companyFilter, setCompanyFilter] = useState<OpportunityCompany | "">("");
  const [rpeFilter, setRpeFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState(urlQuery);
  const [profiles, setProfiles] = useState<CompanyProfile[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [processUpdatesDash, setProcessUpdatesDash] = useState<DGCPProcessUpdateDashboardResponse | null>(null);

  const refreshProfiles = useCallback(() => {
    apiClient.getCompanyProfiles().then(setProfiles).catch(() => setProfiles([]));
  }, []);

  useEffect(() => {
    setRpeFilter(loadSavedRpeFilter());
    setCompanyFilter(loadSavedCompanyFilter());
    refreshProfiles();
  }, [refreshProfiles]);

  const effectiveCompany = useMemo(() => {
    if (companyFilter) return companyFilter;
    if (rpeFilter.trim()) {
      const c = resolveCompanyFromRpe(rpeFilter, profiles);
      if (c) return c;
    }
    return "" as OpportunityCompany | "";
  }, [companyFilter, rpeFilter, profiles]);

  /** Alinea el header multiempresa con el filtro Empresa/RPE de licitaciones. */
  const syncGlobalCompany = useCallback(
    async (company: OpportunityCompany | "") => {
      const allowed = companyCtx?.allowed_companies ?? [];
      if (!company) {
        if (companyCtx?.can_select_all) {
          try {
            await setSelection({
              selection_mode: "all",
              selected_company_ids: allowed.map((c) => c.id),
            });
          } catch {
            /* no bloquear listado */
          }
        }
        return;
      }
      const match = allowed.find((c) => {
        const n = c.name.toLowerCase();
        if (company === "just_office") return n.includes("just office") || n.includes("justoffice");
        if (company === "justech") return n.includes("justech") && !n.includes("office");
        if (company === "mf_plug_safe") return n.includes("plug");
        if (company === "omni_solutions") return n.includes("omni");
        return false;
      });
      if (!match) return;
      if (
        companyCtx?.selection_mode === "single" &&
        (companyCtx.active_company_id === match.id || companyCtx.selected_company_ids?.[0] === match.id)
      ) {
        return;
      }
      try {
        await setSelection({
          selection_mode: "single",
          active_company_id: match.id,
          selected_company_ids: [match.id],
        });
      } catch {
        /* no bloquear listado */
      }
    },
    [companyCtx, setSelection],
  );

  useEffect(() => {
    if (!companyCtx?.odoo_connected) return;
    void syncGlobalCompany(effectiveCompany);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [companyCtx?.odoo_connected, companyCtx?.allowed_companies?.length, effectiveCompany]);

  useEffect(() => {
    setSearchQuery(urlQuery);
  }, [urlQuery]);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const q = searchQuery.trim();
      const company =
        effectiveCompany &&
        (["justech", "just_office", "mf_plug_safe", "omni_solutions", "unclassified"] as const).includes(
          effectiveCompany,
        )
          ? effectiveCompany
          : undefined;
      const filters = {
        status: statusFilter || undefined,
        funnel_stage: funnelFilter || undefined,
        company,
        search: q.length >= 2 ? q : undefined,
        include_expired: q.length >= 2 ? true : undefined,
        limit: q.length >= 2 ? 50 : 150,
      };

      const listResult = await apiClient.getDGCPOpportunities(filters).then(
        (list) => ({ ok: true as const, list }),
        (err) => ({ ok: false as const, err }),
      );
      const dashResult = await apiClient.getDGCPDashboard({ company }).then(
        (dash) => ({ ok: true as const, dash }),
        (err) => ({ ok: false as const, err }),
      );
      const updatesDash = dgcpProcessUpdatesEnabled()
        ? await (typeof apiClient.getDGCPProcessUpdatesDashboard === "function"
            ? apiClient.getDGCPProcessUpdatesDashboard().catch(() => null)
            : Promise.resolve(null))
        : null;

      if (!listResult.ok) {
        setItems([]);
        setSummary(dashResult.ok ? dashResult.dash : EMPTY);
        setProcessUpdatesDash(updatesDash);
        const err = listResult.err as { message?: string; status?: number; name?: string } | undefined;
        const msg = err?.message || "";
        if (msg === "UNAUTHORIZED" || err?.status === 401) {
          setLoadError("Sesión expirada. Vuelva a iniciar sesión e intente actualizar.");
        } else if (err?.status === 408 || /tardó demasiado|timeout/i.test(msg)) {
          setLoadError("La carga de procesos tardó demasiado. Intente actualizar de nuevo.");
        } else {
          setLoadError("No se pudieron cargar los procesos DGCP. Intente actualizar.");
        }
        return;
      }

      let rows = Array.isArray(listResult.list.items) ? listResult.list.items : [];
      if (mode === "won") {
        rows = rows.filter((o) => {
          const stage = getOpportunityFunnelStage(o.status);
          return stage === "adjudicadas" || stage === "no_adjudicadas";
        });
      }
      setItems(rows);
      if (dashResult.ok) {
        setSummary(dashResult.dash);
      } else {
        setSummary(EMPTY);
        setLoadError("Los procesos cargaron, pero el resumen DGCP no está disponible.");
      }
      setProcessUpdatesDash(updatesDash);
    } catch {
      setItems([]);
      setSummary(EMPTY);
      setLoadError("No se pudieron cargar los procesos DGCP. Intente actualizar.");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, funnelFilter, effectiveCompany, mode, searchQuery]);

  useEffect(() => {
    void load();
  }, [load]);

  async function sync() {
    setSyncing(true);
    try {
      await apiClient.triggerDGCPSync(5, 50);
      await load();
    } finally {
      setSyncing(false);
    }
  }

  const kanbanGroups = useMemo(() => {
    const groups: Record<string, DGCPOpportunity[]> = {};
    for (const stage of FUNNEL_STAGES) {
      groups[stage] = [];
    }
    for (const o of items) {
      const k = getOpportunityFunnelStage(o.status);
      groups[k].push(o);
    }
    return groups;
  }, [items]);

  const funnelCounts = useMemo(() => {
    const counts: Partial<Record<FunnelStage, number>> = {};
    for (const o of items) {
      const stage = getOpportunityFunnelStage(o.status);
      counts[stage] = (counts[stage] ?? 0) + 1;
    }
    return counts;
  }, [items]);

  const calendarItems = useMemo(
    () =>
      [...items]
        .filter((o) => o.deadline)
        .sort((a, b) => a.deadline.localeCompare(b.deadline)),
    [items],
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <MutateButton
          permission="mutate_dgcp"
          access={access}
          variant="outline"
          size="sm"
          onClick={() => void sync()}
          disabled={syncing || loading}
        >
          <RefreshCw className={cn("mr-2 h-4 w-4", (syncing || loading) && "animate-spin")} />
          Sincronizar DGCP
        </MutateButton>
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          Actualizar
        </Button>
        <CreateLicitationDialog access={access} onCreated={() => void load()} />
      </div>

      {loadError ? (
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm">
          <p className="font-medium text-destructive">{loadError}</p>
          <p className="mt-1 text-muted-foreground">
            Los indicadores pueden aparecer en cero porque la carga falló; no representan un vacío real.
          </p>
          <Button variant="outline" size="sm" className="mt-2" onClick={() => void load()} disabled={loading}>
            Reintentar
          </Button>
        </div>
      ) : (
        <KPIGrid summary={summary} variant="compact" />
      )}

      {dgcpProcessUpdatesEnabled() && processUpdatesDash?.enabled && processUpdatesDash.total_pending > 0 && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm">
          <p className="font-medium text-destructive">
            Actualizaciones del portal DGCP pendientes de revisión
          </p>
          <p className="mt-1 text-muted-foreground">
            {processUpdatesDash.total_pending} cambio(s) en {processUpdatesDash.items.length} proceso(s)
            {processUpdatesDash.total_critical > 0
              ? ` — ${processUpdatesDash.total_critical} crítico(s)`
              : ""}
            . Revise el expediente → Actualizaciones.
          </p>
          <ul className="mt-2 space-y-1">
            {processUpdatesDash.items.slice(0, 5).map((item) => (
              <li key={item.opportunity_id}>
                <Link
                  href={`/dgcp/${item.opportunity_id}?tab=expediente&section=actualizaciones`}
                  className="text-primary hover:underline"
                >
                  {item.process_code}: {item.title}
                </Link>
                <span className="ml-2 text-xs text-muted-foreground">
                  ({item.pending_count} pendiente{item.pending_count !== 1 ? "s" : ""}
                  {item.critical_count > 0 ? `, ${item.critical_count} crítico(s)` : ""})
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <DgcpRpeFilterBar
        profiles={profiles}
        companyValue={companyFilter}
        rpeValue={rpeFilter}
        onFilterChange={(company, rpe) => {
          setCompanyFilter(company);
          setRpeFilter(rpe);
          void syncGlobalCompany(company);
        }}
        onProfilesRefresh={refreshProfiles}
      />

      <form
        className="relative max-w-xl"
        onSubmit={(e) => {
          e.preventDefault();
          void load();
        }}
      >
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          type="search"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Buscar por código DGCP, título, institución o UUID…"
          className="h-10 w-full rounded-lg border border-border bg-background pl-9 pr-9 text-sm outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/10"
        />
        {searchQuery && (
          <button
            type="button"
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground hover:bg-muted"
            onClick={() => setSearchQuery("")}
            aria-label="Limpiar búsqueda"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </form>
      {searchQuery.trim().length >= 2 && (
        <p className="text-sm text-muted-foreground">
          {loading ? "Buscando…" : `${items.length} resultado(s) para «${searchQuery.trim()}» (incluye procesos vencidos)`}
        </p>
      )}

      <FunnelStageTabs active={funnelFilter} onChange={setFunnelFilter} counts={funnelCounts} />

      <select
        className="rounded-lg border border-input bg-background px-2 py-1.5 text-sm"
        value={statusFilter}
        onChange={(e) => setStatusFilter(e.target.value as OpportunityStatus | "")}
      >
        <option value="">Estado detallado (todos)</option>
        {PIPELINE_STATUSES.map((s) => (
          <option key={s} value={s}>
            {STATUS_LABELS[s]}
          </option>
        ))}
      </select>

      {mode === "kanban" && (
        <div className="flex gap-3 overflow-x-auto pb-2">
          {FUNNEL_STAGES.map((stage) => {
            const rows = kanbanGroups[stage] ?? [];
            return (
            <div key={stage} className="min-w-[240px] shrink-0 rounded-xl border bg-muted/20 p-3">
              <p className="mb-2 text-xs font-semibold uppercase text-muted-foreground">
                {FUNNEL_STAGE_LABELS[stage]} ({rows.length})
              </p>
              <div className="space-y-2 max-h-[420px] overflow-y-auto">
                {rows.map((o) => (
                  <Link key={o.id} href={`/dgcp/${o.id}`} className="block rounded-lg border bg-card p-2 text-sm hover:border-primary/40">
                    <p className="font-medium line-clamp-2">{o.title}</p>
                    <p className="text-[10px] text-muted-foreground">{o.institution}</p>
                    <p className="text-[10px] text-muted-foreground">{formatDateTime(o.deadline)}</p>
                  </Link>
                ))}
              </div>
            </div>
            );
          })}
        </div>
      )}

      {mode === "calendar" && (
        <ul className="divide-y rounded-xl border">
          {calendarItems.map((o) => (
            <li key={o.id} className="flex items-center justify-between gap-4 px-4 py-3 text-sm">
              <Link href={`/dgcp/${o.id}`} className="font-medium hover:text-primary">{o.title}</Link>
              <span className="shrink-0 text-muted-foreground">{formatDateTime(o.deadline)}</span>
            </li>
          ))}
          {!calendarItems.length && <li className="px-4 py-8 text-center text-muted-foreground">Sin fechas límite</li>}
        </ul>
      )}

      {(mode === "list" || mode === "won") && (
        <>
          {loading && (
            <p className="text-sm text-muted-foreground py-6 text-center">Cargando procesos…</p>
          )}
          {loadError && (
            <p className="text-sm text-destructive py-4 text-center">{loadError}</p>
          )}
          {!loading && !loadError && <OpportunitiesTable items={items} />}
        </>
      )}
    </div>
  );
}

export function LicitacionesExpedientesSection() {
  const [items, setItems] = useState<DGCPOpportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [bandeja, setBandeja] = useState<FunnelStage>("interesadas");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await apiClient.getDGCPOpportunities({
        funnel_stage: bandeja,
        limit: 100,
        include_expired: true,
      });
      setItems(r.items);
    } finally {
      setLoading(false);
    }
  }, [bandeja]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Bandejas de expedientes por etapa del embudo. Desde «Interesadas» en adelante cada proceso
        aparece aquí al marcar interés.
      </p>
      <div className="flex flex-wrap gap-1 border-b border-border pb-2">
        {EXPEDIENTE_FUNNEL_STAGES.map((stage) => (
          <Button
            key={stage}
            type="button"
            size="sm"
            variant={bandeja === stage ? "default" : "ghost"}
            className="h-8"
            onClick={() => setBandeja(stage)}
          >
            {FUNNEL_STAGE_LABELS[stage]}
          </Button>
        ))}
      </div>
      {loading ? (
        <p className="text-sm text-muted-foreground">Cargando expedientes…</p>
      ) : (
        <OpportunitiesTable items={items} />
      )}
    </div>
  );
}

export function LicitacionesAnalisisSection() {
  const [items, setItems] = useState<DGCPOpportunity[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient
      .getDGCPOpportunities({ limit: 50 })
      .then((r) => setItems(r.items.filter((o) => o.score >= 50).sort((a, b) => b.score - a.score)))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-muted-foreground">Cargando análisis…</p>;

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Procesos con mayor score IA. Abra el detalle para inteligencia premium y historial comercial Odoo.
      </p>
      <OpportunitiesTable items={items} />
    </div>
  );
}

export function LicitacionesCompetidoresSection() {
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Adjudicaciones históricas DGCP — consulte el tab Histórico en cada proceso para competidores y montos.
      </p>
      <LicitacionesProcesosSection mode="won" />
    </div>
  );
}
