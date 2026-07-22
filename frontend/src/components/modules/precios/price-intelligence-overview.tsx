"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Bell, FileStack, LineChart, Package, RefreshCw, TrendingUp, Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import type { PriceIntelligenceDashboard } from "@/lib/licitador";
import { moduleSectionHref } from "@/lib/modules/types";

/** Resumen operativo de inteligencia de precios — métricas reales del índice. */
export function PriceIntelligenceOverview() {
  const [data, setData] = useState<PriceIntelligenceDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    apiClient
      .getLicitadorPriceIntelligence()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  if (loading) return <p className="text-sm text-muted-foreground">Cargando inteligencia de precios…</p>;
  if (!data) {
    return (
      <p className="text-sm text-muted-foreground">
        No se pudo cargar el panel de precios. Verifica la conexión con listas indexadas.
      </p>
    );
  }

  const kpis = [
    { label: "Productos indexados", value: data.total_products, icon: Package, href: moduleSectionHref("precios", "productos") },
    { label: "Proveedores con listas", value: data.total_suppliers, icon: TrendingUp, href: moduleSectionHref("precios", "proveedores") },
    { label: "Listas cargadas hoy", value: data.lists_today, icon: FileStack, href: moduleSectionHref("precios", "listas") },
    { label: "Pendientes de indexar", value: data.pending_files.length, icon: Upload, tone: data.pending_files.length > 0 ? "warning" : "default", href: moduleSectionHref("precios", "listas") },
  ];

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpis.map((k) => (
          <Link key={k.label} href={k.href}>
            <Card className="transition hover:border-primary/40">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">{k.label}</CardTitle>
                <k.icon className="h-4 w-4 text-primary" />
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">{k.value}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        <Button asChild size="sm">
          <Link href={moduleSectionHref("precios", "buscador")}>
            <LineChart className="mr-2 h-4 w-4" />
            Buscar producto
          </Link>
        </Button>
        <Button asChild variant="outline" size="sm">
          <Link href={moduleSectionHref("precios", "comparaciones")}>
            <TrendingUp className="mr-2 h-4 w-4" />
            Comparar proveedores
          </Link>
        </Button>
        <Button asChild variant="outline" size="sm">
          <Link href={moduleSectionHref("precios", "listas")}>
            <FileStack className="mr-2 h-4 w-4" />
            Ver listas
          </Link>
        </Button>
        <Button variant="ghost" size="sm" onClick={load}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Actualizar
        </Button>
      </div>

      {data.recent_errors.length > 0 && (
        <Card className="border-amber-200 bg-amber-50/50 dark:bg-amber-950/20">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm text-amber-800 dark:text-amber-200">
              <Bell className="h-4 w-4" />
              Alertas recientes
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm text-amber-900 dark:text-amber-100">
            {data.recent_errors.slice(0, 3).map((e, i) => (
              <p key={i}>{e}</p>
            ))}
          </CardContent>
        </Card>
      )}

      {data.processed_files.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-medium">Últimas listas indexadas</h3>
          <ul className="space-y-1 text-sm text-muted-foreground">
            {data.processed_files.slice(0, 5).map((f) => (
              <li key={f.id}>
                {f.name} · {f.supplier || "—"} · {f.records} productos
                {f.indexed_at ? ` · ${new Date(f.indexed_at).toLocaleDateString()}` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
