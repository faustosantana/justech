"use client";

import Link from "next/link";
import { ArrowLeft, ClipboardList } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { BulkActionsBar } from "@/components/ui/bulk-actions-bar";
import { UserSelector } from "@/components/work/user-selector";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { t } from "@/i18n";
import { ApiError, apiClient } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import type { PriceQuoteDraft } from "@/lib/prices";
import type { Task } from "@/lib/tasks";
import { cn } from "@/lib/utils";

const m = t();

const STATUS_LABELS: Record<string, string> = {
  draft: "borrador",
  pendiente_revision_vendedor: "pendiente revisión vendedor",
  listo_para_odoo: "listo para Odoo",
  enviado_odoo: "enviado a Odoo",
  descartado: "descartado",
};

const BULK_STATUSES = [
  "draft",
  "pendiente_revision_vendedor",
  "listo_para_odoo",
  "enviado_odoo",
] as const;

export default function PriceDraftsPage() {
  const router = useRouter();
  const [drafts, setDrafts] = useState<PriceQuoteDraft[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [bulkStatus, setBulkStatus] = useState<string>("pendiente_revision_vendedor");
  const [bulkAssignUserId, setBulkAssignUserId] = useState<string | null>(null);
  const [economicTasks, setEconomicTasks] = useState<Task[]>([]);

  const downloadCsv = (csv: string, filename: string) => {
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const load = useCallback(async () => {
    if (!getAccessToken()) {
      router.replace("/login?session=expired");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [res, taskRes] = await Promise.all([
        apiClient.listPriceQuoteDrafts(),
        apiClient.getTasks({ limit: 100 }).catch(() => ({ items: [], total: 0 })),
      ]);
      setDrafts(res.items);
      setEconomicTasks(
        taskRes.items.filter((t) => t.metadata?.task_type === "economic_offer"),
      );
      setSelectedIds([]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : m.common.loading);
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  const activeDrafts = drafts.filter((d) => d.status !== "descartado");

  return (
    <AppShell title="Borradores de cotización" description="Preparados desde Inteligencia de Precios">
      <div className="mb-4 flex flex-wrap gap-2">
        <Link href="/prices" className="text-sm text-primary hover:underline inline-flex items-center gap-1">
          <ArrowLeft className="h-3 w-3" /> Volver a precios
        </Link>
      </div>

      {loading && drafts.length === 0 && (
        <p className="text-sm text-muted-foreground">{m.common.loading}</p>
      )}
      {error && <p className="text-sm text-destructive">{error}</p>}

      {economicTasks.length > 0 && (
        <Card className="mb-6 border-primary/20">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <ClipboardList className="h-4 w-4 text-primary" />
              Borradores DGCP — oferta económica ({economicTasks.length})
            </CardTitle>
            <Link href="/dgcp">
              <Button size="sm" variant="outline">Ver licitaciones</Button>
            </Link>
          </CardHeader>
          <CardContent className="space-y-2">
            {economicTasks.slice(0, 6).map((t) => (
              <Link
                key={t.id}
                href={`/tasks/${t.id}`}
                className="flex items-center justify-between rounded-lg border border-border p-3 hover:bg-muted/30 text-sm"
              >
                <span>{t.title}</span>
                <span className="text-xs text-muted-foreground capitalize">{t.status.replace(/_/g, " ")}</span>
              </Link>
            ))}
          </CardContent>
        </Card>
      )}

      {!loading && drafts.length === 0 && (
        <Card>
          <CardContent className="py-8 text-sm text-muted-foreground">
            No hay borradores. Use «Preparar cotización» en el detalle de un producto cotizable.
          </CardContent>
        </Card>
      )}

      {drafts.length > 0 && (
        <div className="space-y-4">
          <BulkActionsBar
            selectedIds={selectedIds}
            allIds={activeDrafts.map((d) => d.id)}
            onSelectAll={() => setSelectedIds(activeDrafts.map((d) => d.id))}
            onClearSelection={() => setSelectedIds([])}
            actions={[
              {
                id: "assign",
                label: "Asignar vendedor",
                disabled: !bulkAssignUserId,
                onRun: async (ids) => {
                  if (!bulkAssignUserId) return "Seleccione un vendedor.";
                  const res = await apiClient.bulkQuoteDrafts({
                    ids,
                    action: "assign",
                    assigned_user_id: bulkAssignUserId,
                  });
                  await load();
                  return res.message;
                },
              },
              {
                id: "status",
                label: "Cambiar estado",
                onRun: async (ids) => {
                  const res = await apiClient.bulkQuoteDrafts({
                    ids,
                    action: "status",
                    status: bulkStatus,
                  });
                  await load();
                  return res.message;
                },
              },
              {
                id: "discard",
                label: "Descartar",
                variant: "destructive",
                onRun: async (ids) => {
                  const res = await apiClient.bulkQuoteDrafts({ ids, action: "discard" });
                  await load();
                  return res.message;
                },
              },
              {
                id: "export",
                label: "Exportar",
                onRun: async (ids) => {
                  const res = await apiClient.bulkQuoteDrafts({ ids, action: "export" });
                  if (res.export_csv) {
                    downloadCsv(res.export_csv, "borradores-cotizacion.csv");
                  }
                  return res.message;
                },
              },
              {
                id: "create-task",
                label: "Crear tarea",
                onRun: async (ids) => {
                  const res = await apiClient.bulkQuoteDrafts({ ids, action: "create_task" });
                  await load();
                  return res.message;
                },
              },
            ]}
          />

          {selectedIds.length > 0 && (
            <div className="flex flex-wrap items-end gap-4 rounded-lg border border-border bg-muted/20 px-3 py-3">
              <div className="min-w-[220px]">
                <UserSelector
                  label="Vendedor para asignación"
                  value={bulkAssignUserId}
                  onChange={setBulkAssignUserId}
                  placeholder="Buscar usuario…"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-muted-foreground">Estado destino</label>
                <select
                  className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                  value={bulkStatus}
                  onChange={(e) => setBulkStatus(e.target.value)}
                >
                  {BULK_STATUSES.map((s) => (
                    <option key={s} value={s}>
                      {STATUS_LABELS[s] ?? s}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          <Card data-testid="drafts-bulk-panel">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <ClipboardList className="h-4 w-4" />
                Borradores ({drafts.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm" data-testid="drafts-bulk-table">
                  <thead>
                    <tr className="border-b border-border text-left text-muted-foreground">
                      <th className="pb-2 pr-2 w-8" />
                      <th className="pb-2 pr-4">Producto</th>
                      <th className="pb-2 pr-4">Estado</th>
                      <th className="pb-2 pr-4">Cliente</th>
                      <th className="pb-2 pr-4">Venta sugerida</th>
                      <th className="pb-2">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {drafts.map((draft) => (
                      <tr
                        key={draft.id}
                        data-testid={`bulk-row-${draft.id}`}
                        className={cn(
                          "border-b border-border/50 hover:bg-muted/30",
                          draft.status === "descartado" && "opacity-60",
                        )}
                      >
                        <td className="py-3 pr-2">
                          {draft.status !== "descartado" && (
                            <input
                              type="checkbox"
                              checked={selectedIds.includes(draft.id)}
                              onChange={(e) =>
                                setSelectedIds((prev) =>
                                  e.target.checked
                                    ? [...prev, draft.id]
                                    : prev.filter((id) => id !== draft.id),
                                )
                              }
                            />
                          )}
                        </td>
                        <td className="py-3 pr-4">
                          <p className="font-medium">{draft.description ?? "Producto"}</p>
                          <p className="text-xs text-muted-foreground">
                            {draft.source_filename} / fila {draft.source_row}
                          </p>
                        </td>
                        <td className="py-3 pr-4 capitalize">
                          {STATUS_LABELS[draft.status] ?? draft.status}
                        </td>
                        <td className="py-3 pr-4 text-muted-foreground">{draft.client_name ?? "—"}</td>
                        <td className="py-3 pr-4">
                          {draft.currency} {draft.sale_price_suggested}
                        </td>
                        <td className="py-3">
                          <div className="flex flex-wrap gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => router.push(`/prices/${draft.product_id}`)}
                            >
                              Ver producto
                            </Button>
                            {draft.task_id && (
                              <Button size="sm" onClick={() => router.push(`/tasks/${draft.task_id}`)}>
                                Ver tarea
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </AppShell>
  );
}
