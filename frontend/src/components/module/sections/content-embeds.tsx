"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";

import { DocumentsHubM365Panel } from "@/components/documents/documents-hub-m365-panel";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import { DOCUMENTOS_SUBMODULES, type DocumentsHubDashboard } from "@/lib/documents-hub";
import { cn } from "@/lib/utils";

export function DocumentsHubEmbed() {
  const [data, setData] = useState<DocumentsHubDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await apiClient.getDocumentsHubDashboard());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-4">
      <DocumentsHubM365Panel />
      <div className="flex justify-end">
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          <RefreshCw className={cn("mr-2 h-4 w-4", loading && "animate-spin")} />
          Actualizar
        </Button>
      </div>
      {data && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data.submodule_cards?.map((card) => (
            <Card key={card.key}>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">{card.label}</CardTitle>
                <CardDescription>{String(card.value)}</CardDescription>
              </CardHeader>
              {card.href && (
                <CardContent>
                  <Link href={card.href} className="text-sm text-primary hover:underline">
                    Abrir →
                  </Link>
                </CardContent>
              )}
            </Card>
          ))}
        </div>
      )}
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {DOCUMENTOS_SUBMODULES.map((m) => (
          <Link
            key={m.key}
            href={m.href}
            className="rounded-xl border border-border/60 bg-card px-4 py-3 text-sm font-medium transition hover:border-primary/30"
          >
            {m.label}
          </Link>
        ))}
      </div>
    </div>
  );
}

export function EmpresasEmbed() {
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">Directorio de empresas y contactos del grupo.</p>
      <Link href="/apps/empresas-grupo/empresas" className="inline-flex rounded-xl bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">
        Abrir directorio completo
      </Link>
    </div>
  );
}

export function TasksListEmbed({ sectionId }: { sectionId: string }) {
  const [tasks, setTasks] = useState<Awaited<ReturnType<typeof apiClient.getTasks>>["items"]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const params: Record<string, string> = {};
    if (sectionId === "vencidas") params.status = "vencida";
    apiClient
      .getTasks(params)
      .then((r) => setTasks(r.items))
      .finally(() => setLoading(false));
  }, [sectionId]);

  if (loading) return <p className="text-sm text-muted-foreground">Cargando tareas…</p>;
  if (!tasks.length) return <p className="text-sm text-muted-foreground">Sin tareas.</p>;

  return (
    <ul className="divide-y rounded-xl border border-border">
      {tasks.slice(0, 50).map((t) => (
        <li key={t.id} className="px-4 py-3">
          <Link href={`/tasks/${t.id}`} className="text-sm font-medium hover:text-primary">
            {t.title}
          </Link>
          <p className="text-xs text-muted-foreground">{t.status}</p>
        </li>
      ))}
    </ul>
  );
}

export function PricesSearchEmbed() {
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">Buscador comercial de precios e indexación.</p>
      <div className="flex flex-wrap gap-2">
        <Link href="/prices/drafts" className="rounded-xl border px-4 py-2 text-sm hover:border-primary/30">
          Borradores de cotización
        </Link>
        <Link href="/documentos/precios" className="rounded-xl border px-4 py-2 text-sm hover:border-primary/30">
          Listas indexadas
        </Link>
      </div>
    </div>
  );
}

export function ExecutiveReportEmbed() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<Awaited<ReturnType<typeof apiClient.getExecutiveDashboard>> | null>(null);

  useEffect(() => {
    apiClient
      .getExecutiveDashboard()
      .then(setData)
      .catch(() => setError("No se pudo cargar el centro de mando."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-muted-foreground">Cargando…</p>;
  if (error || !data) return <p className="text-sm text-destructive">{error ?? "Sin datos"}</p>;

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {data.kpis.slice(0, 8).map((k) => (
        <Card key={k.id}>
          <CardContent className="py-4">
            <p className="text-2xl font-semibold">{k.value}</p>
            <p className="text-xs text-muted-foreground">{k.label}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export function InteligenciaBandejaEmbed() {
  const [items, setItems] = useState<Awaited<ReturnType<typeof apiClient.listObservations>>["items"]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient
      .listObservations({ limit: 50 })
      .then((r) => setItems(r.items))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-muted-foreground">Cargando bandeja…</p>;

  return (
    <ul className="divide-y rounded-xl border border-border">
      {items.map((row) => (
        <li key={row.id} className="px-4 py-3 text-sm">
          <p className="font-medium">{row.summary}</p>
          <p className="text-xs text-muted-foreground">{row.channel} · {row.status}</p>
        </li>
      ))}
      {!items.length && <li className="px-4 py-8 text-center text-muted-foreground">Sin detecciones.</li>}
    </ul>
  );
}
