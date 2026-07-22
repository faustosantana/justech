"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Bell, Package, TrendingUp } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import type { PriceIntelligenceDashboard } from "@/lib/licitador";
import { moduleSectionHref } from "@/lib/modules/types";

export function PreciosAlertasSection() {
  const [data, setData] = useState<PriceIntelligenceDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    apiClient
      .getLicitadorPriceIntelligence()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, []);

  if (loading) return <p className="text-sm text-muted-foreground">Cargando alertas…</p>;
  if (!data) return <p className="text-sm text-muted-foreground">No se pudo cargar alertas de precios.</p>;

  const alerts: { id: string; title: string; detail: string; tone: "warning" | "danger" | "info"; href?: string }[] = [];

  if (data.pending_files.length > 0) {
    alerts.push({
      id: "pending",
      title: `${data.pending_files.length} lista(s) pendiente(s) de indexar`,
      detail: data.pending_files.slice(0, 3).map((f) => f.name).join(" · "),
      tone: "warning",
      href: moduleSectionHref("precios", "listas"),
    });
  }

  if (data.lists_today === 0 && data.total_products > 0) {
    alerts.push({
      id: "no-today",
      title: "No hay listas cargadas hoy",
      detail: "Los productos indexados provienen de cargas anteriores. Revise sincronización OneDrive.",
      tone: "info",
      href: moduleSectionHref("precios", "listas"),
    });
  }

  data.recent_errors.forEach((e, i) => {
    alerts.push({
      id: `err-${i}`,
      title: "Error de indexación",
      detail: e,
      tone: "danger",
    });
  });

  if (data.total_suppliers > 0 && data.total_products === 0) {
    alerts.push({
      id: "empty-index",
      title: "Proveedores sin productos indexados",
      detail: "Hay proveedores registrados pero el índice de productos está vacío.",
      tone: "warning",
      href: moduleSectionHref("precios", "listas"),
    });
  }

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-dashed bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
        Alertas de <strong>inteligencia de precios</strong>: indexación, listas pendientes y diferencias entre proveedores.
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <Package className="h-8 w-8 text-primary" />
            <div>
              <p className="text-2xl font-bold">{data.total_products}</p>
              <p className="text-xs text-muted-foreground">Productos indexados</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <TrendingUp className="h-8 w-8 text-primary" />
            <div>
              <p className="text-2xl font-bold">{data.total_suppliers}</p>
              <p className="text-xs text-muted-foreground">Proveedores con listas</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <Bell className="h-8 w-8 text-amber-600" />
            <div>
              <p className="text-2xl font-bold">{alerts.length}</p>
              <p className="text-xs text-muted-foreground">Alertas activas</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {alerts.length === 0 ? (
        <Card className="border-emerald-200 bg-emerald-50/30 dark:bg-emerald-950/10">
          <CardContent className="py-6 text-center text-sm text-emerald-800 dark:text-emerald-200">
            No hay alertas críticas. El índice de precios está al día.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {alerts.map((a) => (
            <Card
              key={a.id}
              className={
                a.tone === "danger"
                  ? "border-red-300/60"
                  : a.tone === "warning"
                    ? "border-amber-300/60"
                    : ""
              }
            >
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <AlertTriangle className="h-4 w-4" />
                  {a.title}
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap items-center justify-between gap-2 pt-0">
                <p className="text-sm text-muted-foreground">{a.detail}</p>
                {a.href && (
                  <Button size="sm" variant="outline" asChild>
                    <Link href={a.href}>Revisar</Link>
                  </Button>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <Button size="sm" asChild>
          <Link href={moduleSectionHref("precios", "buscador")}>Buscar producto</Link>
        </Button>
        <Button size="sm" variant="outline" asChild>
          <Link href={moduleSectionHref("precios", "comparaciones")}>Comparar proveedores</Link>
        </Button>
        <Button size="sm" variant="ghost" onClick={load}>
          Actualizar
        </Button>
      </div>
    </div>
  );
}
