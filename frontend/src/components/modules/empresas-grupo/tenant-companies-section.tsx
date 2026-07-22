"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AlertTriangle, Building2, CheckCircle2, Clock } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api";
import { cn } from "@/lib/utils";

type CompanyCard = Awaited<ReturnType<typeof apiClient.getDocumentsHubDashboard>>["company_cards"][number];

function statusBadge(score: number, expired?: number, pending?: number) {
  if (pending && pending > 0) {
    return (
      <Badge variant="destructive" className="gap-1">
        <AlertTriangle className="h-3 w-3" />
        Pendientes
      </Badge>
    );
  }
  if (expired && expired > 0) {
    return (
      <Badge variant="destructive" className="gap-1">
        <AlertTriangle className="h-3 w-3" />
        Vencidos
      </Badge>
    );
  }
  if (score >= 90) {
    return (
      <Badge className="gap-1 bg-emerald-600 hover:bg-emerald-600">
        <CheckCircle2 className="h-3 w-3" />
        Vigente
      </Badge>
    );
  }
  if (score >= 70) {
    return (
      <Badge variant="secondary" className="gap-1 bg-amber-100 text-amber-900">
        <Clock className="h-3 w-3" />
        Por completar
      </Badge>
    );
  }
  return (
    <Badge variant="destructive" className="gap-1">
      <AlertTriangle className="h-3 w-3" />
      Incompleto
    </Badge>
  );
}

/** Empresas internas del grupo — Justech, Just Office, MF Plug, Omni Solutions. */
export function TenantCompaniesSection() {
  const [companies, setCompanies] = useState<CompanyCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    apiClient
      .getDocumentsHubDashboard()
      .then((d) => setCompanies(d.company_cards || []))
      .finally(() => setLoading(false));
  }, []);

  const filtered = companies.filter((c) => {
    const q = search.toLowerCase();
    return !q || c.razon_social.toLowerCase().includes(q) || (c.rnc || "").includes(q);
  });

  if (loading) return <p className="text-sm text-muted-foreground">Cargando empresas del grupo…</p>;

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-dashed bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
        <Building2 className="mb-1 inline h-4 w-4 mr-1" />
        Expedientes legales y fiscales de las <strong>empresas internas del grupo</strong>.
        Clientes y proveedores externos tienen módulos propios.
      </div>

      <Input
        placeholder="Buscar razón social, RNC…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="max-w-md"
      />

      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {filtered.map((c) => (
          <Link
            key={c.id}
            href={c.href || `/apps/empresas-grupo/perfil/${c.id}`}
            className={cn(
              "rounded-xl border bg-card p-4 transition hover:border-primary/30",
              (c.completeness_score ?? 0) < 70 && "border-red-200 dark:border-red-900/50",
            )}
          >
            <div className="flex items-start justify-between gap-2">
              <p className="font-medium leading-snug">{c.razon_social}</p>
              {statusBadge(c.completeness_score ?? 0)}
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              RNC {c.rnc || "—"} · Perfil {c.completeness_score ?? 0}% completo
            </p>
            {c.documents_missing != null && c.documents_missing > 0 && (
              <p className="mt-1 text-xs text-red-600">{c.documents_missing} documento(s) pendiente(s)</p>
            )}
          </Link>
        ))}
      </div>
    </div>
  );
}
