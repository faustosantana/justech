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
  const [institutionFilter, setInstitutionFilter] = useState("");
  const [institutionQuery, setInstitutionQuery] = useState("");
  const [institutionMenuOpen, setInstitutionMenuOpen] = useState(false);
  const [institutions, setInstitutions] = useState<string[]>([]);
  const [altInstitutionTotal, setAltInstitutionTotal] = useState<number | null>(null);
  const [openState, setOpenState] = useState<"open" | "closed" | "all">("open");
  const [deadlineFrom, setDeadlineFrom] = useState("");
  const [deadlineTo, setDeadlineTo] = useState("");
  const [deadlinePreset, setDeadlinePreset] = useState<"" | "today" | "3d" | "7d" | "30d">("");
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

      let from = deadlineFrom || undefined;
      let to = deadlineTo || undefined;
      if (deadlinePreset) {
        const today = new Date();
        const iso = (d: Date) => d.toISOString().slice(0, 10);
        from = iso(today);
        const end = new Date(today);
        if (deadlinePreset === "today") {
          to = from;
        } else if (deadlinePreset === "3d") {
          end.setDate(end.getDate() + 3);
          to = iso(end);
        } else if (deadlinePreset === "7d") {
          end.setDate(end.getDate() + 7);
          to = iso(end);
        } else if (deadlinePreset === "30d") {
          end.setDate(end.getDate() + 30);
          to = iso(end);
        }
      }

      // Búsqueda libre: incluir vencidos (comportamiento histórico), salvo que el usuario
      // elija explícitamente solo Abiertas o solo Cerradas vía vigencia.
      const searching = q.length >= 2;
      const effectiveOpenState: "open" | "closed" | "all" = searching && openState === "open" ? "all" : openState;

      const filters = {
        status: statusFilter || undefined,
        funnel_stage: funnelFilter || undefined,
        company,
        search: searching ? q : undefined,
        institution: institutionFilter.trim().length >= 2 ? institutionFilter.trim() : undefined,
        open_state: effectiveOpenState,
        deadline_from: from,
        deadline_to: to,
        limit: searching || institutionFilter ? 100 : 150,
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

      // Si filtro institución + abiertas queda vacío, informar cuántas hay sin filtro de empresa.
      if (
        rows.length === 0 &&
        institutionFilter.trim().length >= 2 &&
        effectiveOpenState === "open" &&
        !searching
      ) {
        try {
          const alt = await apiClient.getDGCPOpportunities({
            institution: institutionFilter.trim(),
            open_state: "open",
            // Sin company: cuenta real de abiertas en todos los RPE visibles.
            limit: 1,
          });
          const altAll = await apiClient.getDGCPOpportunities({
            institution: institutionFilter.trim(),
            open_state: "all",
            limit: 1,
          });
          setAltInstitutionTotal(Math.max(alt.total ?? 0, altAll.total ?? 0));
        } catch {
          setAltInstitutionTotal(null);
        }
      } else {
        setAltInstitutionTotal(null);
      }

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
  }, [
    statusFilter,
    funnelFilter,
    effectiveCompany,
    mode,
    searchQuery,
    institutionFilter,
    openState,
    deadlineFrom,
    deadlineTo,
    deadlinePreset,
  ]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const company =
      effectiveCompany &&
      (["justech", "just_office", "mf_plug_safe", "omni_solutions", "unclassified"] as const).includes(
        effectiveCompany,
      )
        ? effectiveCompany
        : undefined;
    const q = institutionQuery.trim();
    const handle = window.setTimeout(() => {
      apiClient
        .getDGCPInstitutions({
          company,
          search: q.length >= 2 ? q : undefined,
          limit: 500,
        })
        .then((r) => setInstitutions(r.items ?? []))
        .catch(() => setInstitutions([]));
    }, q.length >= 2 ? 250 : 0);
    return () => window.clearTimeout(handle);
  }, [effectiveCompany, institutionQuery]);

  const institutionOptions = useMemo(() => {
    const q = institutionQuery.trim().toLowerCase();
    if (!q) return institutions.slice(0, 80);
    return institutions.filter((n) => n.toLowerCase().includes(q)).slice(0, 80);
  }, [institutions, institutionQuery]);

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

      <div className="flex flex-wrap items-end gap-2">
        <div className="relative flex flex-col gap-1 text-xs text-muted-foreground">
          <span>Institución</span>
          <div className="relative min-w-[280px]">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <input
              type="search"
              className="h-9 w-full rounded-lg border border-input bg-background pl-8 pr-8 text-sm text-foreground outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/10"
              placeholder="Escribe para buscar institución…"
              value={institutionFilter ? institutionFilter : institutionQuery}
              data-testid="dgcp-filter-institution"
              onFocus={() => setInstitutionMenuOpen(true)}
              onBlur={() => window.setTimeout(() => setInstitutionMenuOpen(false), 150)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  const typed = institutionQuery.trim();
                  if (typed.length >= 2) {
                    setInstitutionFilter(typed);
                    setInstitutionQuery("");
                    setInstitutionMenuOpen(false);
                  }
                }
              }}
              onChange={(e) => {
                const v = e.target.value;
                setInstitutionFilter("");
                setInstitutionQuery(v);
                setInstitutionMenuOpen(true);
              }}
            />
            {(institutionFilter || institutionQuery) && (
              <button
                type="button"
                className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground hover:bg-muted"
                aria-label="Limpiar institución"
                onClick={() => {
                  setInstitutionFilter("");
                  setInstitutionQuery("");
                  setInstitutionMenuOpen(false);
                  setAltInstitutionTotal(null);
                }}
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
            {institutionMenuOpen && (
              <ul
                className="absolute z-40 mt-1 max-h-64 w-full overflow-y-auto rounded-lg border bg-background py-1 shadow-lg"
                data-testid="dgcp-filter-institution-menu"
              >
                {institutionOptions.length === 0 ? (
                  <li className="px-3 py-2 text-sm text-muted-foreground">
                    {institutionQuery.trim().length < 2
                      ? "Escribe al menos 2 letras para buscar…"
                      : "Sin coincidencias"}
                  </li>
                ) : (
                  institutionOptions.map((name) => (
                    <li key={name}>
                      <button
                        type="button"
                        className="block w-full px-3 py-1.5 text-left text-sm text-foreground hover:bg-muted"
                        onMouseDown={(e) => e.preventDefault()}
                        onClick={() => {
                          setInstitutionFilter(name);
                          setInstitutionQuery("");
                          setInstitutionMenuOpen(false);
                        }}
                      >
                        {name}
                      </button>
                    </li>
                  ))
                )}
              </ul>
            )}
          </div>
        </div>

        <label className="flex flex-col gap-1 text-xs text-muted-foreground">
          Vigencia
          <select
            className="rounded-lg border border-input bg-background px-2 py-1.5 text-sm text-foreground"
            value={openState}
            onChange={(e) => setOpenState(e.target.value as "open" | "closed" | "all")}
            data-testid="dgcp-filter-open-state"
          >
            <option value="open">Abiertas (plazo vigente)</option>
            <option value="closed">Cerradas / vencidas</option>
            <option value="all">Todas</option>
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs text-muted-foreground">
          Cierra en
          <select
            className="rounded-lg border border-input bg-background px-2 py-1.5 text-sm text-foreground"
            value={deadlinePreset}
            onChange={(e) => {
              const v = e.target.value as "" | "today" | "3d" | "7d" | "30d";
              setDeadlinePreset(v);
              if (v) {
                setDeadlineFrom("");
                setDeadlineTo("");
              }
            }}
            data-testid="dgcp-filter-deadline-preset"
          >
            <option value="">Cualquier fecha</option>
            <option value="today">Hoy</option>
            <option value="3d">Próximos 3 días</option>
            <option value="7d">Próximos 7 días</option>
            <option value="30d">Próximos 30 días</option>
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs text-muted-foreground">
          Cierra desde
          <input
            type="date"
            className="rounded-lg border border-input bg-background px-2 py-1.5 text-sm text-foreground"
            value={deadlineFrom}
            onChange={(e) => {
              setDeadlineFrom(e.target.value);
              setDeadlinePreset("");
            }}
            data-testid="dgcp-filter-deadline-from"
          />
        </label>

        <label className="flex flex-col gap-1 text-xs text-muted-foreground">
          Cierra hasta
          <input
            type="date"
            className="rounded-lg border border-input bg-background px-2 py-1.5 text-sm text-foreground"
            value={deadlineTo}
            onChange={(e) => {
              setDeadlineTo(e.target.value);
              setDeadlinePreset("");
            }}
            data-testid="dgcp-filter-deadline-to"
          />
        </label>

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

        {(institutionFilter || openState !== "open" || deadlinePreset || deadlineFrom || deadlineTo || statusFilter) && (
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => {
              setInstitutionFilter("");
              setInstitutionQuery("");
              setOpenState("open");
              setDeadlinePreset("");
              setDeadlineFrom("");
              setDeadlineTo("");
              setStatusFilter("");
              setAltInstitutionTotal(null);
            }}
          >
            Limpiar filtros
          </Button>
        )}
      </div>

      {!loading && items.length === 0 && institutionFilter && openState === "open" && (altInstitutionTotal ?? 0) > 0 && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-900 dark:text-amber-100">
          No hay procesos <strong>abiertos</strong> para «{institutionFilter}»
          {effectiveCompany ? (
            <>
              {" "}
              con empresa <strong>{effectiveCompany}</strong>. Prueba{" "}
              <button
                type="button"
                className="font-medium underline underline-offset-2"
                onClick={() => {
                  setCompanyFilter("");
                  setRpeFilter("");
                  if (typeof window !== "undefined") {
                    localStorage.removeItem("jaios_dgcp_company_filter");
                    localStorage.removeItem("jaios_dgcp_rpe_filter");
                  }
                  void syncGlobalCompany("");
                }}
              >
                Todas las empresas / Todos los RPE
              </button>
              {" · "}
            </>
          ) : (
            <>
              . Hay <strong>{altInstitutionTotal}</strong> proceso(s) en total (cerrados o de otra
              vigencia).{" "}
            </>
          )}
          <button
            type="button"
            className="font-medium underline underline-offset-2"
            onClick={() => setOpenState("all")}
          >
            Ver todas
          </button>
          {" · "}
          <button
            type="button"
            className="font-medium underline underline-offset-2"
            onClick={() => setOpenState("closed")}
          >
            Ver cerradas
          </button>
        </div>
      )}

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
