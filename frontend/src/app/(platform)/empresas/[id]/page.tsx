"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { CreateTaskButton } from "@/components/work/create-task-button";
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

export default function EmpresaDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [data, setData] = useState<BusinessCompany | null>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Partial<BusinessCompany>>({});

  useEffect(() => {
    apiClient.getCompany(id).then(setData).catch(() => router.replace("/empresas"));
  }, [id, router]);

  if (!data) {
    return (
      <AppShell title="Empresa">
        <p className="text-muted-foreground">Cargando…</p>
      </AppShell>
    );
  }

  const save = async () => {
    const updated = await apiClient.updateCompany(id, {
      ...form,
      brands: typeof form.brands === "string"
        ? String(form.brands).split(",").map((b) => b.trim()).filter(Boolean)
        : form.brands,
    });
    setData(updated);
    setEditing(false);
  };

  const deactivate = async () => {
    if (!confirm("¿Desactivar esta empresa?")) return;
    await apiClient.deactivateCompany(id);
    router.push("/empresas");
  };

  return (
    <AppShell title={data.name} description={COMPANY_TYPE_LABELS[data.company_type]}>
      <div className="mb-4 flex flex-wrap gap-2">
        <Link href="/empresas" className="text-sm text-primary hover:underline">← Empresas</Link>
        <CreateTaskButton
          eventType="seguimiento_cliente"
          title={`Seguimiento: ${data.name}`}
          description={`Tarea relacionada con ${data.name}`}
          customerName={data.name}
          source="empresa"
          label="Crear tarea"
        />
        {data.price_supplier_name && (
          <Button variant="outline" size="sm" asChild>
            <Link href={`/prices?supplier=${encodeURIComponent(data.price_supplier_name)}`}>
              Ver precios
            </Link>
          </Button>
        )}
        {data.odoo_partner_id && (
          <Button variant="outline" size="sm" asChild>
            <Link href={`/odoo/customers/${data.odoo_partner_id}`}>Ver en Odoo</Link>
          </Button>
        )}
        <Button variant="outline" size="sm" asChild>
          <Link href={`/search?q=${encodeURIComponent(data.name)}`}>Buscar en JAIOS</Link>
        </Button>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Detalle</CardTitle>
          <div className="flex gap-2">
            {!editing ? (
              <Button size="sm" variant="outline" onClick={() => { setForm(data); setEditing(true); }}>
                Editar
              </Button>
            ) : (
              <>
                <Button size="sm" onClick={save}>Guardar</Button>
                <Button size="sm" variant="outline" onClick={() => setEditing(false)}>Cancelar</Button>
              </>
            )}
            <Button size="sm" variant="destructive" onClick={deactivate}>Desactivar</Button>
          </div>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          {editing ? (
            <>
              <Field label="Nombre" value={form.name ?? ""} onChange={(v) => setForm({ ...form, name: v })} />
              <select
                value={form.company_type ?? data.company_type}
                onChange={(e) => setForm({ ...form, company_type: e.target.value as CompanyType })}
                className="brand-input py-2"
              >
                {Object.entries(COMPANY_TYPE_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
              <Field label="RNC" value={form.tax_id ?? ""} onChange={(v) => setForm({ ...form, tax_id: v })} />
              <Field label="Correo" value={form.email ?? ""} onChange={(v) => setForm({ ...form, email: v })} />
              <Field label="Teléfono" value={form.phone ?? ""} onChange={(v) => setForm({ ...form, phone: v })} />
              <Field label="Contacto" value={form.primary_contact ?? ""} onChange={(v) => setForm({ ...form, primary_contact: v })} />
              <Field label="Sitio web" value={form.website ?? ""} onChange={(v) => setForm({ ...form, website: v })} />
              <Field label="Categoría" value={form.category ?? ""} onChange={(v) => setForm({ ...form, category: v })} />
              <Field label="Proveedor precios" value={form.price_supplier_name ?? ""} onChange={(v) => setForm({ ...form, price_supplier_name: v })} />
              <Field label="Marcas (coma)" value={(form.brands ?? []).join(", ")} onChange={(v) => setForm({ ...form, brands: v.split(",") })} />
              <div className="md:col-span-2">
                <label className="text-xs text-muted-foreground">Notas</label>
                <textarea
                  value={form.notes ?? ""}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  className="mt-1 w-full brand-input p-2"
                  rows={3}
                />
              </div>
            </>
          ) : (
            <>
              <Info label="Estado" value={COMPANY_STATUS_LABELS[data.status]} />
              <Info label="RNC" value={data.tax_id} />
              <Info label="Correo" value={data.email} />
              <Info label="Teléfono" value={data.phone} />
              <Info label="Contacto principal" value={data.primary_contact} />
              <Info label="Sitio web" value={data.website} />
              <Info label="Categoría" value={data.category} />
              <Info label="Marcas" value={data.brands?.join(", ") || "—"} />
              <Info label="Condiciones comerciales" value={data.commercial_terms} />
              <Info label="Proveedor en precios" value={data.price_supplier_name} />
              <Info label="Odoo partner ID" value={data.odoo_partner_id?.toString()} />
              <div className="md:col-span-2">
                <Info label="Notas" value={data.notes} />
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </AppShell>
  );
}

function Info({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm font-medium">{value || "—"}</p>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label className="text-xs text-muted-foreground">{label}</label>
      <Input value={value} onChange={(e) => onChange(e.target.value)} className="mt-1" />
    </div>
  );
}
