"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Building2, Plus, RefreshCw, Search } from "lucide-react";

import { SupplierCard, SupplierDashboardCards } from "@/components/suppliers/supplier-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ModuleEmptyState } from "@/components/module/module-dashboard";
import { apiClient } from "@/lib/api";
import type { Supplier, SupplierDashboardStats } from "@/lib/suppliers";

/** Directorio de suplidores externos — NO empresas del grupo interno. */
export function SuppliersDirectorySection() {
  const [items, setItems] = useState<Supplier[]>([]);
  const [stats, setStats] = useState<SupplierDashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [list, dash] = await Promise.all([
        apiClient.getSuppliers({
          search: search || undefined,
          limit: 100,
        }),
        apiClient.getSupplierDashboard(),
      ]);
      const filtered = list.items.filter(
        (s) => s.company_type !== "cliente" && !/justech|just office|mf plug|omni solutions/i.test(s.name),
      );
      setItems(filtered);
      setStats(dash);
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    const t = setTimeout(load, search ? 300 : 0);
    return () => clearTimeout(t);
  }, [load, search]);

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-dashed bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
        Directorio de <strong>proveedores externos</strong> (distribuidores, fabricantes, mayoristas).
        Las empresas del grupo están en{" "}
        <Link href="/apps/empresas-grupo" className="font-medium text-primary hover:underline">
          Empresas del Grupo
        </Link>
        .
      </div>

      <SupplierDashboardCards stats={stats} />

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-[220px] flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Buscar proveedor, marca, categoría…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Actualizar
        </Button>
        <Button size="sm" asChild>
          <Link href="/configuracion/integraciones/proveedores">
            <Plus className="mr-2 h-4 w-4" />
            Gestionar proveedores
          </Link>
        </Button>
      </div>

      {loading && items.length === 0 ? (
        <p className="text-sm text-muted-foreground">Cargando proveedores…</p>
      ) : items.length === 0 ? (
        <ModuleEmptyState
          title="Sin proveedores registrados"
          description="Agrega suplidores como Omega Tech, Ingram o Solution Box desde Configuración → Integraciones → Proveedores."
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.map((s) => (
            <SupplierCard key={s.id} supplier={s} />
          ))}
        </div>
      )}
    </div>
  );
}
