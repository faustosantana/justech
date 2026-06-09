"use client";

import { RefreshCw } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { KPIGrid } from "@/components/dgcp/kpi-grid";
import { OpportunitiesTable } from "@/components/dgcp/opportunities-table";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import {
  COMPANY_LABELS,
  formatDateTime,
  PRIORITY_LABELS,
  STATUS_LABELS,
  type DGCPAuditLog,
  type DGCPOpportunity,
  type DGCPSummary,
  type DGCPSyncJob,
  type DGCPSyncSchedule,
  type OpportunityCompany,
  type OpportunityPriority,
  type OpportunityStatus,
} from "@/lib/dgcp";

const EMPTY_SUMMARY: DGCPSummary = {
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

export default function DGCPDashboardPage() {
  const router = useRouter();
  const [items, setItems] = useState<DGCPOpportunity[]>([]);
  const [summary, setSummary] = useState<DGCPSummary>(EMPTY_SUMMARY);
  const [syncJobs, setSyncJobs] = useState<DGCPSyncJob[]>([]);
  const [schedule, setSchedule] = useState<DGCPSyncSchedule | null>(null);
  const [audit, setAudit] = useState<DGCPAuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<OpportunityStatus | "">("");
  const [companyFilter, setCompanyFilter] = useState<OpportunityCompany | "">("");
  const [priorityFilter, setPriorityFilter] = useState<OpportunityPriority | "">("");
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const loadData = useCallback(async () => {
    if (!getAccessToken()) {
      router.replace("/login");
      return;
    }

    setError(null);
    const filters = {
      status: statusFilter || undefined,
      company: companyFilter || undefined,
      priority: priorityFilter || undefined,
      limit: 100,
    };

    const results = await Promise.allSettled([
      apiClient.getDGCPOpportunities(filters),
      apiClient.getDGCPDashboard(),
      apiClient.getDGCPSyncJobs(5),
      apiClient.getDGCPSyncSchedule(),
      apiClient.getDGCPAudit(15),
    ]);

    if (!mountedRef.current) return;

    const failures = results.filter((r) => r.status === "rejected");
    if (failures.length === results.length) {
      const first = failures[0];
      if (first.status === "rejected" && first.reason instanceof Error) {
        if (first.reason.message === "UNAUTHORIZED") {
          router.replace("/login");
          return;
        }
      }
      setError("No se pudo cargar los datos DGCP. Verifica que el backend esté activo.");
      return;
    }

    if (results[0].status === "fulfilled") {
      setItems(results[0].value.items);
      setSummary(results[0].value.summary);
    }
    if (results[1].status === "fulfilled") setSummary(results[1].value);
    if (results[2].status === "fulfilled") setSyncJobs(results[2].value);
    if (results[3].status === "fulfilled") setSchedule(results[3].value);
    if (results[4].status === "fulfilled") setAudit(results[4].value);

    if (failures.length > 0) {
      setError("Algunos datos no se cargaron. La vista puede estar incompleta.");
    }
  }, [statusFilter, companyFilter, priorityFilter, router]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    loadData()
      .catch(() => {
        if (active) setError("Error inesperado al cargar DGCP.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [loadData]);

  async function handleSync() {
    setSyncing(true);
    setError(null);
    try {
      await apiClient.triggerDGCPSync(schedule?.max_pages ?? 5, schedule?.page_size ?? 50);
      await loadData();
    } catch {
      setError("La sincronización falló.");
    } finally {
      setSyncing(false);
    }
  }

  async function handleReclassify() {
    setSyncing(true);
    setError(null);
    try {
      await apiClient.reclassifyDGCPOpportunities();
      await loadData();
    } catch {
      setError("La reclasificación falló.");
    } finally {
      setSyncing(false);
    }
  }

  async function toggleSchedule() {
    if (!schedule) return;
    try {
      const updated = await apiClient.updateDGCPSyncSchedule({
        is_enabled: !schedule.is_enabled,
      });
      setSchedule(updated);
    } catch {
      setError("No se pudo actualizar el schedule.");
    }
  }

  return (
    <AppShell
      title="Centro de Inteligencia DGCP"
      description="Oportunidades reales de Compras Públicas RD"
    >
      <div className="space-y-8">
        {error && (
          <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-3">
          <Button onClick={handleSync} disabled={syncing || loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${syncing ? "animate-spin" : ""}`} />
            {syncing ? "Sincronizando…" : "Sincronizar DGCP"}
          </Button>
          <Button variant="outline" onClick={handleReclassify} disabled={syncing || loading}>
            Reclasificar
          </Button>
          {schedule && (
            <Button variant="outline" onClick={toggleSchedule} disabled={loading}>
              Sync automático: {schedule.is_enabled ? "Activo" : "Inactivo"}
            </Button>
          )}
          {schedule?.last_run_at && (
            <span className="text-sm text-muted-foreground">
              Última sync: {formatDateTime(schedule.last_run_at)}
            </span>
          )}
        </div>

        {loading ? (
          <p className="text-muted-foreground">Cargando oportunidades…</p>
        ) : (
          <>
            <KPIGrid summary={summary} />

            <div className="flex flex-wrap gap-2">
              <FilterSelect
                label="Estado"
                value={statusFilter}
                options={Object.entries(STATUS_LABELS).map(([k, v]) => ({ value: k, label: v }))}
                onChange={(v) => setStatusFilter(v as OpportunityStatus | "")}
              />
              <FilterSelect
                label="Empresa"
                value={companyFilter}
                options={Object.entries(COMPANY_LABELS).map(([k, v]) => ({ value: k, label: v }))}
                onChange={(v) => setCompanyFilter(v as OpportunityCompany | "")}
              />
              <FilterSelect
                label="Prioridad"
                value={priorityFilter}
                options={Object.entries(PRIORITY_LABELS).map(([k, v]) => ({ value: k, label: v }))}
                onChange={(v) => setPriorityFilter(v as OpportunityPriority | "")}
              />
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Oportunidades ({items.length})</CardTitle>
              </CardHeader>
              <CardContent>
                <OpportunitiesTable items={items} />
              </CardContent>
            </Card>

            <div className="grid gap-4 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Historial de sincronización</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {syncJobs.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Sin sincronizaciones aún.</p>
                  ) : (
                    syncJobs.map((job) => (
                      <div
                        key={job.id}
                        className="flex justify-between rounded-lg border border-border/50 p-3 text-sm"
                      >
                        <div>
                          <p className="font-medium capitalize">
                            {job.trigger} — {job.status}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            +{job.created_count} nuevas, {job.updated_count} actualizadas
                            {job.error_message && ` — ${job.error_message}`}
                          </p>
                        </div>
                        <span className="text-xs text-muted-foreground whitespace-nowrap">
                          {formatDateTime(job.started_at)}
                        </span>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Auditoría</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {audit.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Sin eventos registrados.</p>
                  ) : (
                    audit.map((log) => (
                      <div
                        key={log.id}
                        className="rounded-lg border border-border/50 p-3 text-sm"
                      >
                        <div className="flex justify-between gap-2">
                          <span className="font-mono text-xs text-primary">{log.action}</span>
                          <span className="text-xs text-muted-foreground">
                            {formatDateTime(log.created_at)}
                          </span>
                        </div>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}

function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: Array<{ value: string; label: string }>;
  onChange: (value: string) => void;
}) {
  return (
    <select
      className="h-9 rounded-md border border-border bg-background px-3 text-sm text-foreground"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      aria-label={label}
    >
      <option value="">{label}: Todos</option>
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}
