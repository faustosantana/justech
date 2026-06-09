"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Plus, Search } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api";
import {
  COMPANY_STATUS_LABELS,
  COMPANY_TYPE_LABELS,
  type BusinessCompany,
  type CompanyType,
} from "@/lib/companies";
import { cn } from "@/lib/utils";

const TYPES: Array<{ value: "" | CompanyType; label: string }> = [
  { value: "", label: "Todos los tipos" },
  { value: "proveedor", label: "Proveedor" },
  { value: "fabricante", label: "Fabricante" },
  { value: "cliente", label: "Cliente" },
  { value: "aliado", label: "Aliado" },
  { value: "competidor", label: "Competidor" },
];

export default function EmpresasPage() {
  const [items, setItems] = useState<BusinessCompany[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<"" | CompanyType>("");
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: "",
    company_type: "proveedor" as CompanyType,
    tax_id: "",
    email: "",
    phone: "",
    primary_contact: "",
    category: "",
    brands: "",
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.getCompanies({
        search,
        company_type: typeFilter || undefined,
        status: "activo",
        limit: 200,
      });
      setItems(res.items);
      setTotal(res.total);
    } finally {
      setLoading(false);
    }
  }, [search, typeFilter]);

  useEffect(() => {
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
  }, [load]);

  const handleCreate = async () => {
    if (!form.name.trim()) return;
    await apiClient.createCompany({
      name: form.name.trim(),
      company_type: form.company_type,
      tax_id: form.tax_id || undefined,
      email: form.email || undefined,
      phone: form.phone || undefined,
      primary_contact: form.primary_contact || undefined,
      category: form.category || undefined,
      brands: form.brands
        ? form.brands.split(",").map((b) => b.trim()).filter(Boolean)
        : [],
      status: "activo",
    });
    setShowForm(false);
    setForm({
      name: "",
      company_type: "proveedor",
      tax_id: "",
      email: "",
      phone: "",
      primary_contact: "",
      category: "",
      brands: "",
    });
    load();
  };

  return (
    <AppShell
      title="Empresas y Proveedores"
      description="Directorio comercial — proveedores, fabricantes, clientes y aliados"
    >
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          <div className="relative min-w-[220px] flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar por nombre, RNC, contacto…"
              className="pl-9"
            />
          </div>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value as "" | CompanyType)}
            className="brand-input py-2"
          >
            {TYPES.map((t) => (
              <option key={t.value || "all"} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>
        <Button onClick={() => setShowForm((v) => !v)}>
          <Plus className="mr-2 h-4 w-4" />
          Registrar empresa
        </Button>
      </div>

      {showForm && (
        <Card className="mb-6 border-primary/20">
          <CardHeader>
            <CardTitle className="text-base">Nueva empresa</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2">
            <Input placeholder="Nombre *" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <select
              value={form.company_type}
              onChange={(e) => setForm({ ...form, company_type: e.target.value as CompanyType })}
              className="brand-input py-2"
            >
              {TYPES.filter((t) => t.value).map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
            <Input placeholder="RNC" value={form.tax_id} onChange={(e) => setForm({ ...form, tax_id: e.target.value })} />
            <Input placeholder="Correo" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            <Input placeholder="Teléfono" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            <Input placeholder="Contacto principal" value={form.primary_contact} onChange={(e) => setForm({ ...form, primary_contact: e.target.value })} />
            <Input placeholder="Categoría" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
            <Input placeholder="Marcas (separadas por coma)" value={form.brands} onChange={(e) => setForm({ ...form, brands: e.target.value })} />
            <div className="md:col-span-2 flex gap-2">
              <Button onClick={handleCreate}>Guardar</Button>
              <Button variant="outline" onClick={() => setShowForm(false)}>Cancelar</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>{total} empresa(s) registrada(s)</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Cargando…</p>
          ) : items.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              No hay empresas registradas. Usa «Registrar empresa» para agregar proveedores, fabricantes o clientes.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="py-2 pr-4">Nombre</th>
                    <th className="py-2 pr-4">Tipo</th>
                    <th className="py-2 pr-4">RNC</th>
                    <th className="py-2 pr-4">Contacto</th>
                    <th className="py-2">Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((c) => (
                    <tr key={c.id} className="border-b border-border/60 hover:bg-muted/30">
                      <td className="py-3 pr-4">
                        <Link href={`/empresas/${c.id}`} className="font-medium text-primary hover:underline">
                          {c.name}
                        </Link>
                      </td>
                      <td className="py-3 pr-4">{COMPANY_TYPE_LABELS[c.company_type]}</td>
                      <td className="py-3 pr-4">{c.tax_id || "—"}</td>
                      <td className="py-3 pr-4">{c.primary_contact || c.email || "—"}</td>
                      <td className="py-3">
                        <span className={cn(
                          "rounded-full px-2 py-0.5 text-xs",
                          c.status === "activo" ? "bg-success/10 text-success" : "bg-muted text-muted-foreground",
                        )}>
                          {COMPANY_STATUS_LABELS[c.status]}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </AppShell>
  );
}
