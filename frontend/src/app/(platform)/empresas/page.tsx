"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Grid3X3,
  LayoutList,
  Plus,
  Search,
  Sparkles,
  Upload,
} from "lucide-react";

import { SupplierCard, SupplierDashboardCards } from "@/components/suppliers/supplier-card";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { apiClient } from "@/lib/api";
import {
  SUPPLIER_STATUS_LABELS,
  SUPPLIER_TYPE_LABELS,
  type Supplier,
  type SupplierCategory,
  type SupplierDashboardStats,
  type SupplierSearchMatch,
  type SupplierType,
} from "@/lib/suppliers";
import { cn } from "@/lib/utils";

const TYPES: Array<{ value: "" | SupplierType; label: string }> = [
  { value: "", label: "Todos los tipos" },
  { value: "proveedor", label: "Proveedor" },
  { value: "fabricante", label: "Fabricante" },
  { value: "mayorista", label: "Mayorista" },
  { value: "distribuidor", label: "Distribuidor" },
  { value: "cliente", label: "Cliente" },
  { value: "aliado", label: "Aliado" },
  { value: "subcontratista", label: "Subcontratista" },
  { value: "transportista", label: "Transportista" },
  { value: "tecnico_externo", label: "Técnico externo" },
];

export default function EmpresasPage() {
  const [items, setItems] = useState<Supplier[]>([]);
  const [searchResults, setSearchResults] = useState<SupplierSearchMatch[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<SupplierDashboardStats | null>(null);
  const [categories, setCategories] = useState<SupplierCategory[]>([]);
  const [search, setSearch] = useState("");
  const [smartQuery, setSmartQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<"" | SupplierType>("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [viewMode, setViewMode] = useState<"cards" | "table">("cards");
  const [smartMode, setSmartMode] = useState(false);
  const [loading, setLoading] = useState(true);
  const [smartLoading, setSmartLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [importing, setImporting] = useState(false);
  const [form, setForm] = useState({
    name: "",
    legal_name: "",
    company_type: "proveedor" as SupplierType,
    tax_id: "",
    email: "",
    phone: "",
    whatsapp: "",
    primary_contact: "",
    category: "",
    brands: "",
    products_services: "",
  });

  const loadMeta = useCallback(async () => {
    const [dash, cats] = await Promise.all([
      apiClient.getSupplierDashboard(),
      apiClient.getSupplierCategories(),
    ]);
    setStats(dash);
    setCategories(cats.items);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.getSuppliers({
        search,
        company_type: typeFilter || undefined,
        category_id: categoryFilter || undefined,
        status: statusFilter || undefined,
        limit: 200,
      });
      setItems(res.items);
      setTotal(res.total);
      setSearchResults([]);
      setSmartMode(false);
    } finally {
      setLoading(false);
    }
  }, [search, typeFilter, categoryFilter, statusFilter]);

  useEffect(() => {
    loadMeta().catch(() => undefined);
  }, [loadMeta]);

  useEffect(() => {
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
  }, [load]);

  const runSmartSearch = async () => {
    if (!smartQuery.trim()) return;
    setSmartLoading(true);
    try {
      const res = await apiClient.searchSuppliers({
        query: smartQuery.trim(),
        company_type: typeFilter || undefined,
        category_id: categoryFilter || undefined,
        limit: 30,
      });
      setSearchResults(res.results);
      setSmartMode(true);
      setTotal(res.total);
    } finally {
      setSmartLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!form.name.trim()) return;
    await apiClient.createSupplier({
      name: form.name.trim(),
      legal_name: form.legal_name || undefined,
      company_type: form.company_type,
      tax_id: form.tax_id || undefined,
      email: form.email || undefined,
      phone: form.phone || undefined,
      whatsapp: form.whatsapp || undefined,
      primary_contact: form.primary_contact || undefined,
      category: form.category || undefined,
      brands: form.brands ? form.brands.split(",").map((b) => b.trim()).filter(Boolean) : [],
      products_services: form.products_services
        ? form.products_services.split(",").map((b) => b.trim()).filter(Boolean)
        : [],
      status: "activo",
    });
    setShowForm(false);
    setForm({
      name: "",
      legal_name: "",
      company_type: "proveedor",
      tax_id: "",
      email: "",
      phone: "",
      whatsapp: "",
      primary_contact: "",
      category: "",
      brands: "",
      products_services: "",
    });
    await loadMeta();
    load();
  };

  const handleImportCsv = async (file: File) => {
    setImporting(true);
    try {
      const text = await file.text();
      const lines = text.split(/\r?\n/).filter(Boolean);
      if (lines.length < 2) return;
      const headers = lines[0].split(",").map((h) => h.trim().toLowerCase());
      const rows = lines.slice(1).map((line) => {
        const cols = line.split(",");
        const row: Record<string, string> = {};
        headers.forEach((h, i) => {
          row[h] = (cols[i] || "").trim();
        });
        return row;
      });
      await apiClient.importSuppliers({ source: "csv", rows });
      await loadMeta();
      load();
    } finally {
      setImporting(false);
    }
  };

  const displayItems = useMemo(
    () => (smartMode ? searchResults.map((r) => ({ supplier: r.supplier, match: r })) : items.map((s) => ({ supplier: s }))),
    [smartMode, searchResults, items],
  );

  const topCategories = stats?.by_category ?? [];

  return (
    <AppShell
      title="Empresas y Proveedores"
      description="Directorio inteligente — busca, clasifica y contacta proveedores según lo que necesites comprar"
    >
      <div className="space-y-6">
        <SupplierDashboardCards stats={stats} />

        <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-transparent">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Sparkles className="h-5 w-5 text-primary" />
              Búsqueda inteligente
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap gap-2">
              <div className="relative min-w-[280px] flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={smartQuery}
                  onChange={(e) => setSmartQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && runSmartSearch()}
                  placeholder='Ej: "Necesito toners HP", "laptops Dell usadas", "cámaras Hikvision"...'
                  className="pl-9"
                />
              </div>
              <Button onClick={runSmartSearch} disabled={smartLoading}>
                {smartLoading ? "Buscando…" : "Buscar proveedor"}
              </Button>
              {smartMode && (
                <Button variant="outline" onClick={() => { setSmartMode(false); load(); }}>
                  Ver directorio completo
                </Button>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              {["toners HP", "laptops usadas", "licencias Microsoft", "cámaras seguridad", "muebles oficina"].map((hint) => (
                <button
                  key={hint}
                  type="button"
                  onClick={() => { setSmartQuery(hint); }}
                  className="rounded-full border px-3 py-1 text-xs text-muted-foreground hover:border-primary hover:text-primary"
                >
                  {hint}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {topCategories.length > 0 && (
          <div>
            <p className="mb-2 text-sm font-medium text-muted-foreground">Por categoría</p>
            <div className="flex flex-wrap gap-2">
              {topCategories.map((c) => (
                <Badge
                  key={c.name}
                  variant="secondary"
                  className="cursor-pointer"
                  onClick={() => {
                    const cat = categories.find((x) => x.name === c.name);
                    if (cat) setCategoryFilter(cat.id);
                  }}
                >
                  {c.name} ({c.count})
                </Badge>
              ))}
              {categories.slice(0, 12).filter((c) => !topCategories.some((t) => t.name === c.name)).map((c) => (
                <Badge
                  key={c.id}
                  variant="outline"
                  className="cursor-pointer"
                  onClick={() => setCategoryFilter(c.id)}
                >
                  {c.name}
                </Badge>
              ))}
            </div>
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2">
            <div className="relative min-w-[200px]">
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Filtrar por nombre, RNC…"
              />
            </div>
            <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value as "" | SupplierType)} className="brand-input py-2">
              {TYPES.map((t) => (
                <option key={t.value || "all"} value={t.value}>{t.label}</option>
              ))}
            </select>
            <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} className="brand-input py-2">
              <option value="">Todas las categorías</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="brand-input py-2">
              <option value="">Todos los estados</option>
              {Object.entries(SUPPLIER_STATUS_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-wrap gap-2">
            <div className="flex rounded-md border">
              <Button variant={viewMode === "cards" ? "default" : "ghost"} size="sm" onClick={() => setViewMode("cards")}>
                <Grid3X3 className="h-4 w-4" />
              </Button>
              <Button variant={viewMode === "table" ? "default" : "ghost"} size="sm" onClick={() => setViewMode("table")}>
                <LayoutList className="h-4 w-4" />
              </Button>
            </div>
            <label className="cursor-pointer">
              <input
                type="file"
                accept=".csv"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && handleImportCsv(e.target.files[0])}
              />
              <Button variant="outline" disabled={importing} asChild>
                <span><Upload className="mr-2 h-4 w-4" />{importing ? "Importando…" : "Importar CSV"}</span>
              </Button>
            </label>
            <Button onClick={() => setShowForm((v) => !v)}>
              <Plus className="mr-2 h-4 w-4" />
              Registrar proveedor
            </Button>
          </div>
        </div>

        {showForm && (
          <Card className="border-primary/20">
            <CardHeader>
              <CardTitle className="text-base">Nuevo proveedor</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 md:grid-cols-3">
              <Input placeholder="Nombre comercial *" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              <Input placeholder="Razón social" value={form.legal_name} onChange={(e) => setForm({ ...form, legal_name: e.target.value })} />
              <select value={form.company_type} onChange={(e) => setForm({ ...form, company_type: e.target.value as SupplierType })} className="brand-input py-2">
                {TYPES.filter((t) => t.value).map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
              <Input placeholder="RNC/cédula" value={form.tax_id} onChange={(e) => setForm({ ...form, tax_id: e.target.value })} />
              <Input placeholder="Correo" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
              <Input placeholder="Teléfono" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
              <Input placeholder="WhatsApp" value={form.whatsapp} onChange={(e) => setForm({ ...form, whatsapp: e.target.value })} />
              <Input placeholder="Contacto principal" value={form.primary_contact} onChange={(e) => setForm({ ...form, primary_contact: e.target.value })} />
              <Input placeholder="Categoría" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
              <Input placeholder="Marcas (coma)" value={form.brands} onChange={(e) => setForm({ ...form, brands: e.target.value })} />
              <Input placeholder="Productos/servicios (coma)" value={form.products_services} onChange={(e) => setForm({ ...form, products_services: e.target.value })} />
              <div className="md:col-span-3 flex gap-2">
                <Button onClick={handleCreate}>Guardar</Button>
                <Button variant="outline" onClick={() => setShowForm(false)}>Cancelar</Button>
              </div>
            </CardContent>
          </Card>
        )}

        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {smartMode ? `${total} resultado(s) inteligente(s)` : `${total} proveedor(es) registrado(s)`}
          </p>
        </div>

        {loading ? (
          <p className="text-sm text-muted-foreground">Cargando directorio…</p>
        ) : displayItems.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <p className="text-muted-foreground">
                {smartMode
                  ? "No hay proveedores que coincidan. Registra uno nuevo o importa desde CSV."
                  : "No hay proveedores registrados. Usa la búsqueda inteligente, importa CSV o registra manualmente."}
              </p>
              <Button className="mt-4" onClick={() => setShowForm(true)}>Registrar proveedor</Button>
            </CardContent>
          </Card>
        ) : viewMode === "cards" ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {displayItems.map(({ supplier, match }) => (
              <SupplierCard key={supplier.id} supplier={supplier} match={match} />
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="overflow-x-auto p-0">
              <table className="w-full min-w-[800px] text-sm">
                <thead>
                  <tr className="border-b bg-muted/40 text-left text-muted-foreground">
                    <th className="p-3">Nombre</th>
                    <th className="p-3">Tipo</th>
                    <th className="p-3">Contacto</th>
                    <th className="p-3">Categorías</th>
                    <th className="p-3">Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {displayItems.map(({ supplier, match }) => (
                    <tr key={supplier.id} className="border-b hover:bg-muted/20">
                      <td className="p-3">
                        <Link href={`/empresas/${supplier.id}`} className="font-medium text-primary hover:underline">
                          {supplier.name}
                        </Link>
                        {match && <p className="text-xs text-muted-foreground">{match.recommendation_reason}</p>}
                      </td>
                      <td className="p-3">{SUPPLIER_TYPE_LABELS[supplier.company_type]}</td>
                      <td className="p-3">{supplier.primary_contact || supplier.email || supplier.phone || "—"}</td>
                      <td className="p-3">
                        {supplier.categories.slice(0, 2).map((c) => c.name).join(", ") || supplier.category || "—"}
                      </td>
                      <td className="p-3">
                        <span className={cn(
                          "rounded-full px-2 py-0.5 text-xs",
                          supplier.status === "preferido" && "bg-amber-100 text-amber-800",
                          supplier.status === "activo" && "bg-success/10 text-success",
                          supplier.status === "bloqueado" && "bg-destructive/10 text-destructive",
                          supplier.status === "inactivo" && "bg-muted text-muted-foreground",
                        )}>
                          {SUPPLIER_STATUS_LABELS[supplier.status]}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        )}
      </div>
    </AppShell>
  );
}
