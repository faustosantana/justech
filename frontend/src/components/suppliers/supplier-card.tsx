"use client";

import { Building2, Star, Tag } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  SUPPLIER_STATUS_LABELS,
  SUPPLIER_TYPE_LABELS,
  type Supplier,
  type SupplierSearchMatch,
} from "@/lib/suppliers";
import { cn } from "@/lib/utils";

interface SupplierCardProps {
  supplier: Supplier;
  match?: SupplierSearchMatch;
  compact?: boolean;
}

export function SupplierCard({ supplier, match, compact }: SupplierCardProps) {
  const isPreferred = supplier.status === "preferido";

  return (
    <Card className={cn("transition hover:border-primary/40", isPreferred && "border-amber-400/50 bg-amber-50/30 dark:bg-amber-950/10")}>
      <CardContent className={cn("p-4", compact && "p-3")}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <Link href={`/empresas/${supplier.id}`} className="truncate font-semibold text-primary hover:underline">
                {supplier.name}
              </Link>
              {isPreferred && (
                <Badge variant="secondary" className="gap-1 bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
                  <Star className="h-3 w-3 fill-current" />
                  Preferido
                </Badge>
              )}
              {match && (
                <Badge variant="outline" className="text-xs">
                  {match.confidence === "high" ? "Alta confianza" : match.confidence === "medium" ? "Media" : "Baja"}
                </Badge>
              )}
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {SUPPLIER_TYPE_LABELS[supplier.company_type]} · {SUPPLIER_STATUS_LABELS[supplier.status]}
            </p>
          </div>
          {supplier.internal_rating != null && (
            <div className="flex items-center gap-1 text-sm font-medium text-amber-600">
              <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
              {Number(supplier.internal_rating).toFixed(1)}
            </div>
          )}
        </div>

        <div className="mt-3 grid gap-1 text-sm text-muted-foreground">
          {(supplier.primary_contact || supplier.email) && (
            <p>{supplier.primary_contact || supplier.email}</p>
          )}
          {(supplier.whatsapp || supplier.phone) && (
            <p>{supplier.whatsapp || supplier.phone}</p>
          )}
        </div>

        {(supplier.categories.length > 0 || supplier.brands.length > 0) && (
          <div className="mt-3 flex flex-wrap gap-1">
            {supplier.categories.slice(0, 3).map((c) => (
              <Badge key={c.id} variant="secondary" className="text-xs">
                <Tag className="mr-1 h-3 w-3" />
                {c.name}
              </Badge>
            ))}
            {supplier.brands.slice(0, 4).map((b) => (
              <Badge key={b} variant="outline" className="text-xs">{b}</Badge>
            ))}
          </div>
        )}

        {match?.recommendation_reason && (
          <p className="mt-2 text-xs text-primary/80">{match.recommendation_reason}</p>
        )}

        <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
          {supplier.price_lists_count > 0 && (
            <span>{supplier.price_lists_count} lista(s) de precios</span>
          )}
          {supplier.products_indexed_count > 0 && (
            <span>{supplier.products_indexed_count} productos</span>
          )}
          {supplier.last_quote_at && (
            <span>Última cotización: {new Date(supplier.last_quote_at).toLocaleDateString()}</span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function SupplierDashboardCards({
  stats,
}: {
  stats: import("@/lib/suppliers").SupplierDashboardStats | null;
}) {
  if (!stats) return null;

  const cards = [
    { label: "Total proveedores", value: stats.total_suppliers, icon: Building2 },
    { label: "Activos", value: stats.active_suppliers, icon: Building2 },
    { label: "Preferidos", value: stats.preferred_suppliers, icon: Star },
    { label: "Categorías usadas", value: stats.by_category.length, icon: Tag },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map((c) => (
        <Card key={c.label}>
          <CardContent className="flex items-center gap-4 p-4">
            <div className="rounded-lg bg-primary/10 p-2 text-primary">
              <c.icon className="h-5 w-5" />
            </div>
            <div>
              <p className="text-2xl font-bold">{c.value}</p>
              <p className="text-xs text-muted-foreground">{c.label}</p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
