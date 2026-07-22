"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowRight,
  BarChart3,
  Calendar,
  CheckCircle2,
  Clock,
  Package,
  RefreshCw,
  Search,
  Truck,
  Upload,
} from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api";
import type { PriceIntelligenceDashboard } from "@/lib/licitador";
import {
  INDEXING_SOURCES,
  WEEKDAY_LABELS,
  type PriceCatalogSyncJob,
  type PriceCatalogSyncSchedule,
} from "@/lib/price-catalog-sync";

export default function CentroPreciosPage() {
  const [data, setData] = useState<PriceIntelligenceDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [quickQuery, setQuickQuery] = useState("");
  const [schedule, setSchedule] = useState<PriceCatalogSyncSchedule | null>(null);
  const [jobs, setJobs] = useState<PriceCatalogSyncJob[]>([]);
  const [savingSchedule, setSavingSchedule] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      apiClient
        .getDocumentsHubPrices()
        .then(setData)
        .catch(() => apiClient.getLicitadorPriceDashboard().then(setData).catch(() => setData(null))),
      apiClient.getPriceCatalogSyncSchedule().then(setSchedule).catch(() => setSchedule(null)),
      apiClient.listPriceCatalogSyncJobs(8).then(setJobs).catch(() => setJobs([])),
    ]).finally(() => setLoading(false));
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

  const saveSchedule = async (patch: Partial<PriceCatalogSyncSchedule>) => {
    if (!schedule) return;
    setSavingSchedule(true);
    try {
      const updated = await apiClient.updatePriceCatalogSyncSchedule({
        is_enabled: patch.is_enabled ?? schedule.is_enabled,
        sync_days: patch.sync_days ?? schedule.sync_days,
        sync_hour_utc: patch.sync_hour_utc ?? schedule.sync_hour_utc,
        include_file_lists: patch.include_file_lists ?? schedule.include_file_lists,
        include_omega: patch.include_omega ?? schedule.include_omega,
        include_ingram: patch.include_ingram ?? schedule.include_ingram,
        include_cecomsa: patch.include_cecomsa ?? schedule.include_cecomsa,
      });
      setSchedule(updated);
    } finally {
      setSavingSchedule(false);
    }
  };

  const toggleDay = (day: number) => {
    if (!schedule) return;
    const days = schedule.sync_days.includes(day)
      ? schedule.sync_days.filter((d) => d !== day)
      : [...schedule.sync_days, day].sort();
    void saveSchedule({ sync_days: days });
  };

  return (
    <AppShell title="Inteligencia de precios" description="Indexación de listas Excel/CSV de proveedores">
      <div className="space-y-6">
        <div className="flex flex-wrap items-center gap-3">
          <form
            className="flex min-w-[240px] flex-1 gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (quickQuery.trim()) {
                window.location.href = `/prices?q=${encodeURIComponent(quickQuery.trim())}`;
              }
            }}
          >
            <Input placeholder="Buscar producto…" value={quickQuery} onChange={(e) => setQuickQuery(e.target.value)} />
            <Button type="submit">
              <Search className="h-4 w-4" />
            </Button>
          </form>
          <Button variant="outline" onClick={load} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Actualizar
          </Button>
          <Button onClick={runSync} disabled={syncing}>
            <Upload className={`mr-2 h-4 w-4 ${syncing ? "animate-pulse" : ""}`} />
            Indexar listas
          </Button>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <MetricCard icon={Package} label="Productos indexados" value={data?.total_products ?? 0} />
          <MetricCard icon={Truck} label="Proveedores" value={data?.total_suppliers ?? 0} />
          <MetricCard icon={Clock} label="Listas hoy" value={data?.lists_today ?? 0} highlight />
          <MetricCard icon={BarChart3} label="Pendientes" value={data?.pending_files.length ?? 0} warn />
        </div>

        {/* Programación de catálogos */}
        <Card className="border-primary/25">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Calendar className="h-4 w-4" />
              Indexación programada de listas
            </CardTitle>
            <CardDescription>
              Solo archivos Excel/CSV (local y OneDrive ENTRADAS). Cuando tengas API de proveedor, se conecta en Integraciones.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            {schedule && (
              <>
                <div className="flex flex-wrap items-center gap-4">
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={schedule.is_enabled}
                      disabled={savingSchedule}
                      onChange={(e) => void saveSchedule({ is_enabled: e.target.checked })}
                    />
                    Programación activa
                  </label>
                  <label className="flex items-center gap-2 text-sm">
                    Hora UTC:
                    <Input
                      type="number"
                      min={0}
                      max={23}
                      className="h-8 w-16"
                      value={schedule.sync_hour_utc}
                      disabled={savingSchedule}
                      onChange={(e) => void saveSchedule({ sync_hour_utc: Number(e.target.value) })}
                    />
                  </label>
                  {schedule.next_run_at && (
                    <span className="text-xs text-muted-foreground">
                      Próxima ejecución: {new Date(schedule.next_run_at).toLocaleString("es-DO")}
                    </span>
                  )}
                  {schedule.last_run_at && (
                    <span className="text-xs text-muted-foreground">
                      Última: {new Date(schedule.last_run_at).toLocaleString("es-DO")}
                    </span>
                  )}
                </div>

                <div>
                  <p className="mb-2 text-xs font-medium uppercase text-muted-foreground">Días de sync</p>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(WEEKDAY_LABELS).map(([num, label]) => {
                      const day = Number(num);
                      const active = schedule.sync_days.includes(day);
                      return (
                        <button
                          key={day}
                          type="button"
                          disabled={savingSchedule}
                          onClick={() => toggleDay(day)}
                          className={`rounded-md border px-3 py-1 text-sm transition ${
                            active ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground"
                          }`}
                        >
                          {label}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <p className="text-sm text-muted-foreground">
                  OneDrive ENTRADAS se sincroniza automáticamente cada ~15 min vía{" "}
                  <Link href="/documentos/repositorios" className="text-primary hover:underline">
                    Repositorios
                  </Link>
                  . Activa la programación abajo para reindexar listas locales en días/hora fijos.
                </p>

                <div>
                  <p className="mb-2 text-xs font-medium uppercase text-muted-foreground">Fuente</p>
                  <p className="text-sm">Listas Excel/CSV + OneDrive ENTRADAS</p>
                </div>
              </>
            )}

            {jobs.length > 0 && (
              <div>
                <p className="mb-2 text-xs font-medium uppercase text-muted-foreground">Historial de cargas</p>
                <div className="overflow-x-auto rounded-lg border">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-muted/30 text-left text-xs text-muted-foreground">
                        <th className="p-2">Fecha</th>
                        <th className="p-2">Estado</th>
                        <th className="p-2">Resumen</th>
                      </tr>
                    </thead>
                    <tbody>
                      {jobs.map((job) => (
                        <tr key={job.id} className="border-b border-border/40">
                          <td className="p-2 whitespace-nowrap">
                            {new Date(job.started_at).toLocaleString("es-DO")}
                          </td>
                          <td className="p-2">
                            <Badge variant={job.status === "completed" ? "outline" : "danger"}>{job.status}</Badge>
                          </td>
                          <td className="p-2 text-xs text-muted-foreground">
                            <JobSummary summary={job.summary} />
                            {job.errors.length > 0 && (
                              <span className="text-amber-600"> · {job.errors.length} aviso(s)</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Mapa de fuentes */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Fuentes que alimentan la indexación</CardTitle>
            <CardDescription>
              Páginas del sistema y campos que se guardan por producto en la base local
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {INDEXING_SOURCES.map((src) => (
              <div key={src.id} className="rounded-lg border border-border/60 p-4">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <p className="font-medium">{src.origin}</p>
                  <Badge variant="outline">{src.formats}</Badge>
                </div>
                <p className="text-sm text-muted-foreground">
                  Página:{" "}
                  <Link href={src.page} className="text-primary hover:underline">
                    {src.page}
                  </Link>
                </p>
                <p className="text-xs text-muted-foreground">Ruta: {src.path}</p>
                <p className="mt-1 text-xs text-muted-foreground">Disparador: {src.trigger}</p>
                <ul className="mt-3 grid gap-1 text-xs sm:grid-cols-2">
                  {src.fields.map((f) => (
                    <li key={f} className="text-muted-foreground">
                      · {f}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
            <p className="text-xs text-muted-foreground">
              El Buscador Comercial (<Link href="/prices" className="text-primary hover:underline">/prices</Link>){" "}
              consulta este índice. Omega/Ingram live siguen disponibles como opción manual sin reemplazar el catálogo indexado.
            </p>
          </CardContent>
        </Card>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card className={data?.pending_files.length ? "border-amber-500/40" : undefined}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Upload className="h-4 w-4 text-amber-600" />
                Archivos pendientes
                <Badge variant="outline">{data?.pending_files.length ?? 0}</Badge>
              </CardTitle>
              <CardDescription>03_PROVEEDORES/ENTRADAS (OneDrive)</CardDescription>
            </CardHeader>
            <CardContent>
              {(data?.pending_files.length ?? 0) === 0 ? (
                <p className="flex items-center gap-2 text-sm text-muted-foreground">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  Sin listas pendientes
                </p>
              ) : (
                <div className="divide-y rounded-lg border">
                  {data?.pending_files.map((f) => (
                    <div key={f.id} className="flex items-center justify-between px-4 py-3 text-sm">
                      <div>
                        <p className="font-medium">{f.name}</p>
                        <p className="text-xs text-muted-foreground">{f.parent_path}</p>
                      </div>
                      <Badge variant="outline" className="bg-amber-500/10 text-amber-800">
                        pendiente
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                Procesados
              </CardTitle>
              <CardDescription>03_PROVEEDORES/PROCESADOS</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="max-h-80 divide-y overflow-y-auto rounded-lg border">
                {(data?.processed_files ?? []).slice(0, 15).map((f) => (
                  <div key={f.id} className="flex items-center justify-between gap-2 px-4 py-3 text-sm">
                    <div className="min-w-0">
                      <p className="truncate font-medium">{f.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {f.supplier || "Proveedor"} · {f.records} productos
                      </p>
                    </div>
                    <Badge variant="outline">{f.status}</Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {(data?.recent_errors.length ?? 0) > 0 && (
          <Card className="border-red-500/30">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base text-red-700">
                <AlertCircle className="h-4 w-4" />
                Errores de indexación
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-1 text-sm text-muted-foreground">
                {data?.recent_errors.map((e) => (
                  <li key={e}>• {e}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        <Card className="border-primary/20 bg-gradient-to-r from-primary/5 to-transparent">
          <CardContent className="flex flex-wrap items-center justify-between gap-4 py-6">
            <div>
              <p className="font-medium">Búsqueda comercial</p>
              <p className="text-sm text-muted-foreground">Consulta el índice indexado — live opcional por proveedor</p>
            </div>
            <Button asChild>
              <Link href="/prices">
                Ir al buscador
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}

function JobSummary({ summary }: { summary: Record<string, unknown> }) {
  const providers = summary.providers as Record<string, Record<string, number>> | undefined;
  const fileLists = summary.file_lists as Record<string, unknown> | undefined;
  const parts: string[] = [];
  if (fileLists?.local_fs) {
    const lf = fileLists.local_fs as Record<string, number>;
    parts.push(`Listas: +${lf.records_created ?? 0} productos`);
  }
  if (providers?.omega) {
    parts.push(`Omega: ${providers.omega.indexed ?? 0} (${providers.omega.new ?? 0} nuevos)`);
  }
  if (providers?.ingram) {
    parts.push(`Ingram: ${providers.ingram.indexed ?? 0}`);
  }
  return <span>{parts.join(" · ") || "—"}</span>;
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
