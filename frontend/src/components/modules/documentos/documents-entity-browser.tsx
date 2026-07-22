"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Building2, FileSearch, Scale, UserCircle } from "lucide-react";

import { VigencyBadge } from "@/components/documents/vigency-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import type { DocumentPendingItem } from "@/lib/documents-hub";
import { moduleSectionHref } from "@/lib/modules/types";

type EntityFilter = "all" | "internal_company" | "customer" | "supplier" | "licitacion";

const FILTERS: { id: EntityFilter; label: string; icon: typeof Building2 }[] = [
  { id: "all", label: "Todos", icon: FileSearch },
  { id: "internal_company", label: "Empresas del grupo", icon: Building2 },
  { id: "customer", label: "Clientes", icon: UserCircle },
  { id: "supplier", label: "Proveedores", icon: Building2 },
  { id: "licitacion", label: "Licitaciones", icon: Scale },
];

export function DocumentsEntityBrowser() {
  const [filter, setFilter] = useState<EntityFilter>("all");
  const [pending, setPending] = useState<DocumentPendingItem[]>([]);
  const [hubStats, setHubStats] = useState<{ companies: number; expired: number; missing: number } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiClient.getDocumentsHubPending(),
      apiClient.getDocumentsHubDashboard(),
    ])
      .then(([p, h]) => {
        setPending(p);
        setHubStats({
          companies: h.total_companies,
          expired: h.documents_expired,
          missing: h.documents_missing,
        });
      })
      .finally(() => setLoading(false));
  }, []);

  const filtered = pending.filter((item) => {
    if (filter === "all") return true;
    if (filter === "internal_company") return Boolean(item.company_key);
    if (filter === "licitacion") return item.item_type.includes("licit") || item.item_type.includes("dgcp");
    return false;
  });

  if (loading) return <p className="text-sm text-muted-foreground">Cargando documentos…</p>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            onClick={() => setFilter(f.id)}
            className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm ${
              filter === f.id ? "border-primary bg-primary/10 text-primary" : "text-muted-foreground hover:bg-muted"
            }`}
          >
            <f.icon className="h-3.5 w-3.5" />
            {f.label}
          </button>
        ))}
      </div>

      {filter === "internal_company" && hubStats && (
        <div className="grid gap-3 sm:grid-cols-3">
          <StatCard label="Empresas del grupo" value={hubStats.companies} href={moduleSectionHref("empresas-grupo", "empresas")} />
          <StatCard label="Vencidos" value={hubStats.expired} href={moduleSectionHref("empresas-grupo", "pendientes")} warn />
          <StatCard label="Faltantes" value={hubStats.missing} href={moduleSectionHref("empresas-grupo", "pendientes")} />
        </div>
      )}

      {filter === "customer" && (
        <Card>
          <CardContent className="py-6 text-sm">
            Documentos de clientes se consultan desde{" "}
            <Link href={moduleSectionHref("clientes", "documentos")} className="text-primary hover:underline">
              Clientes → Documentos
            </Link>{" "}
            o historial Odoo.
          </CardContent>
        </Card>
      )}

      {filter === "supplier" && (
        <Card>
          <CardContent className="py-6 text-sm">
            Listas y documentos de proveedores en{" "}
            <Link href={moduleSectionHref("proveedores", "listas")} className="text-primary hover:underline">
              Proveedores → Listas de precios
            </Link>
            .
          </CardContent>
        </Card>
      )}

      {filter === "licitacion" && (
        <Card>
          <CardContent className="py-6 text-sm">
            <Link href={moduleSectionHref("licitaciones", "documentos")} className="text-primary hover:underline">
              Licitaciones → Documentos
            </Link>{" "}
            y expedientes DGCP.
          </CardContent>
        </Card>
      )}

      {(filter === "all" || filter === "internal_company") && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium">Pendientes y vencimientos</h3>
          {filtered.length === 0 ? (
            <p className="text-sm text-muted-foreground">No hay documentos pendientes en este filtro.</p>
          ) : (
            filtered.slice(0, 30).map((item) => (
              <Card key={item.id}>
                <CardContent className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm">
                  <div>
                    <p className="font-medium">{item.item_label}</p>
                    <p className="text-xs text-muted-foreground">
                      {item.company_label} · {item.responsible}
                      {item.due_at ? ` · vence ${item.due_at}` : ""}
                    </p>
                  </div>
                  <VigencyBadge
                    status={item.severity === "critical" ? "vencido" : item.status}
                    missing={item.status === "pending" || item.status === "missing"}
                  />
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  href,
  warn,
}: {
  label: string;
  value: number;
  href: string;
  warn?: boolean;
}) {
  return (
    <Link href={href}>
      <Card className={warn && value > 0 ? "border-amber-300/60" : ""}>
        <CardHeader className="pb-1">
          <CardTitle className="text-xs font-medium text-muted-foreground">{label}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-bold">{value}</p>
        </CardContent>
      </Card>
    </Link>
  );
}
