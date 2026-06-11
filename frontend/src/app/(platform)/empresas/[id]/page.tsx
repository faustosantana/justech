"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  FileText,
  Mail,
  MessageCircle,
  Star,
  ListChecks,
  DollarSign,
} from "lucide-react";

import { CreateTaskButton } from "@/components/work/create-task-button";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { apiClient } from "@/lib/api";
import {
  SUPPLIER_STATUS_LABELS,
  SUPPLIER_TYPE_LABELS,
  mailtoUrl,
  whatsappUrl,
  type Supplier,
  type SupplierInteraction,
  type SupplierPriceListSummary,
  type SupplierType,
} from "@/lib/suppliers";

export default function EmpresaDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [data, setData] = useState<Supplier | null>(null);
  const [priceLists, setPriceLists] = useState<SupplierPriceListSummary[]>([]);
  const [interactions, setInteractions] = useState<SupplierInteraction[]>([]);
  const [editing, setEditing] = useState(false);
  const [quoteProducts, setQuoteProducts] = useState("");
  const [form, setForm] = useState<Partial<Supplier>>({});

  const reload = async () => {
    const [supplier, lists, inter] = await Promise.all([
      apiClient.getSupplier(id),
      apiClient.getSupplierPriceLists(id),
      apiClient.getSupplierInteractions(id),
    ]);
    setData(supplier);
    setPriceLists(lists);
    setInteractions(inter);
  };

  useEffect(() => {
    reload().catch(() => router.replace("/empresas"));
  }, [id, router]);

  if (!data) {
    return (
      <AppShell title="Proveedor">
        <p className="text-muted-foreground">Cargando…</p>
      </AppShell>
    );
  }

  const save = async () => {
    const updated = await apiClient.updateSupplier(id, {
      ...form,
      brands: typeof form.brands === "string"
        ? String(form.brands).split(",").map((b) => b.trim()).filter(Boolean)
        : form.brands,
      products_services: typeof form.products_services === "string"
        ? String(form.products_services).split(",").map((b) => b.trim()).filter(Boolean)
        : form.products_services,
    });
    setData(updated);
    setEditing(false);
  };

  const deactivate = async () => {
    if (!confirm("¿Desactivar este proveedor?")) return;
    await apiClient.deleteSupplier(id);
    router.push("/empresas");
  };

  const togglePreferred = async () => {
    const updated = await apiClient.markSupplierPreferred(id, data.status !== "preferido");
    setData(updated);
  };

  const requestQuote = async (channel: "email" | "whatsapp" | "both") => {
    const products = quoteProducts
      ? quoteProducts.split(",").map((p) => p.trim()).filter(Boolean)
      : data.products_services?.slice(0, 5) ?? ["productos solicitados"];
    const quote = await apiClient.requestSupplierQuote(id, { products, channel });
    if (channel === "whatsapp" || channel === "both") {
      const url = whatsappUrl(data.whatsapp || data.phone, quote.whatsapp_message || undefined);
      if (url) window.open(url, "_blank");
    }
    if (channel === "email" || channel === "both") {
      const url = mailtoUrl(data.email, quote.subject, quote.email_body || undefined);
      if (url) window.location.href = url;
    }
    await reload();
  };

  return (
    <AppShell
      title={data.name}
      description={`${SUPPLIER_TYPE_LABELS[data.company_type]} · ${SUPPLIER_STATUS_LABELS[data.status]}`}
    >
      <div className="mb-4 flex flex-wrap gap-2">
        <Link href="/empresas" className="text-sm text-primary hover:underline">← Directorio</Link>
      </div>

      <div className="mb-6 flex flex-wrap gap-2">
        {(data.whatsapp || data.phone) && (
          <Button variant="outline" size="sm" asChild>
            <a href={whatsappUrl(data.whatsapp || data.phone) || "#"} target="_blank" rel="noreferrer">
              <MessageCircle className="mr-2 h-4 w-4" />WhatsApp
            </a>
          </Button>
        )}
        {data.email && (
          <Button variant="outline" size="sm" asChild>
            <a href={mailtoUrl(data.email) || "#"}>
              <Mail className="mr-2 h-4 w-4" />Correo
            </a>
          </Button>
        )}
        <Button variant="outline" size="sm" onClick={() => requestQuote("both")}>
          <DollarSign className="mr-2 h-4 w-4" />Solicitar cotización
        </Button>
        {data.price_supplier_name && (
          <Button variant="outline" size="sm" asChild>
            <Link href={`/prices?supplier=${encodeURIComponent(data.price_supplier_name)}`}>
              <ListChecks className="mr-2 h-4 w-4" />Ver precios
            </Link>
          </Button>
        )}
        <Button variant="outline" size="sm" onClick={togglePreferred}>
          <Star className="mr-2 h-4 w-4" />
          {data.status === "preferido" ? "Quitar preferido" : "Marcar preferido"}
        </Button>
        <CreateTaskButton
          eventType="seguimiento_cliente"
          title={`Seguimiento proveedor: ${data.name}`}
          description={`Tarea de seguimiento con ${data.name}`}
          customerName={data.name}
          source="empresa"
          label="Crear tarea"
        />
        {data.odoo_partner_id && (
          <Button variant="outline" size="sm" asChild>
            <Link href={`/odoo/customers/${data.odoo_partner_id}`}>Ver en Odoo</Link>
          </Button>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Ficha del proveedor</CardTitle>
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
                  <Field label="Nombre comercial" value={form.name ?? ""} onChange={(v) => setForm({ ...form, name: v })} />
                  <Field label="Razón social" value={form.legal_name ?? ""} onChange={(v) => setForm({ ...form, legal_name: v })} />
                  <select
                    value={form.company_type ?? data.company_type}
                    onChange={(e) => setForm({ ...form, company_type: e.target.value as SupplierType })}
                    className="brand-input py-2"
                  >
                    {Object.entries(SUPPLIER_TYPE_LABELS).map(([k, v]) => (
                      <option key={k} value={k}>{v}</option>
                    ))}
                  </select>
                  <Field label="RNC" value={form.tax_id ?? ""} onChange={(v) => setForm({ ...form, tax_id: v })} />
                  <Field label="Correo" value={form.email ?? ""} onChange={(v) => setForm({ ...form, email: v })} />
                  <Field label="Teléfono" value={form.phone ?? ""} onChange={(v) => setForm({ ...form, phone: v })} />
                  <Field label="WhatsApp" value={form.whatsapp ?? ""} onChange={(v) => setForm({ ...form, whatsapp: v })} />
                  <Field label="Contacto" value={form.primary_contact ?? ""} onChange={(v) => setForm({ ...form, primary_contact: v })} />
                  <Field label="Sitio web" value={form.website ?? ""} onChange={(v) => setForm({ ...form, website: v })} />
                  <Field label="Dirección" value={form.address ?? ""} onChange={(v) => setForm({ ...form, address: v })} />
                  <Field label="Ciudad" value={form.city ?? ""} onChange={(v) => setForm({ ...form, city: v })} />
                  <Field label="Condiciones de pago" value={form.payment_terms ?? ""} onChange={(v) => setForm({ ...form, payment_terms: v })} />
                  <Field label="Tiempo de entrega" value={form.delivery_time ?? ""} onChange={(v) => setForm({ ...form, delivery_time: v })} />
                  <Field label="Proveedor precios" value={form.price_supplier_name ?? ""} onChange={(v) => setForm({ ...form, price_supplier_name: v })} />
                  <Field label="Marcas (coma)" value={(form.brands ?? []).join(", ")} onChange={(v) => setForm({ ...form, brands: v.split(",") })} />
                  <Field label="Productos (coma)" value={(form.products_services ?? []).join(", ")} onChange={(v) => setForm({ ...form, products_services: v.split(",") })} />
                  <div className="md:col-span-2">
                    <label className="text-xs text-muted-foreground">Notas internas</label>
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
                  <Info label="Estado" value={SUPPLIER_STATUS_LABELS[data.status]} />
                  <Info label="Razón social" value={data.legal_name} />
                  <Info label="RNC" value={data.tax_id} />
                  <Info label="Correo" value={data.email} />
                  <Info label="Teléfono" value={data.phone} />
                  <Info label="WhatsApp" value={data.whatsapp} />
                  <Info label="Contacto principal" value={data.primary_contact} />
                  <Info label="Sitio web" value={data.website} />
                  <Info label="Dirección" value={data.address} />
                  <Info label="Ciudad / Provincia" value={[data.city, data.province].filter(Boolean).join(", ") || undefined} />
                  <Info label="País" value={data.country} />
                  <Info label="Condiciones de pago" value={data.payment_terms || data.commercial_terms} />
                  <Info label="Tiempo de entrega" value={data.delivery_time} />
                  <Info label="Moneda" value={data.currency} />
                  <Info label="Rating interno" value={data.internal_rating?.toString()} />
                  <Info label="Marcas" value={data.brands?.join(", ") || "—"} />
                  <Info label="Productos/servicios" value={data.products_services?.join(", ") || "—"} />
                  <Info label="Proveedor en precios" value={data.price_supplier_name} />
                  <div className="md:col-span-2 flex flex-wrap gap-1">
                    {data.categories.map((c) => (
                      <Badge key={c.id} variant="secondary">{c.name}</Badge>
                    ))}
                    {data.tags.map((t) => (
                      <Badge key={t} variant="outline">{t}</Badge>
                    ))}
                  </div>
                  <div className="md:col-span-2">
                    <Info label="Notas internas" value={data.notes} />
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Solicitar cotización</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <Input
                className="max-w-md"
                placeholder="Productos (separados por coma)"
                value={quoteProducts}
                onChange={(e) => setQuoteProducts(e.target.value)}
              />
              <Button size="sm" variant="outline" onClick={() => requestQuote("email")}>Generar correo</Button>
              <Button size="sm" variant="outline" onClick={() => requestQuote("whatsapp")}>Generar WhatsApp</Button>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Listas de precios</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {priceLists.length === 0 ? (
                <p className="text-sm text-muted-foreground">Sin listas vinculadas. Se vinculan al indexar archivos en 03_PROVEEDORES.</p>
              ) : (
                priceLists.map((pl) => (
                  <div key={pl.id} className="rounded-md border p-3 text-sm">
                    <p className="font-medium">{pl.filename || "Lista de precios"}</p>
                    <p className="text-xs text-muted-foreground">{pl.product_count} productos · {new Date(pl.linked_at).toLocaleDateString()}</p>
                    {pl.detected_brands.length > 0 && (
                      <p className="mt-1 text-xs">Marcas: {pl.detected_brands.slice(0, 5).join(", ")}</p>
                    )}
                  </div>
                ))
              )}
              <p className="text-xs text-muted-foreground">
                Total indexado: {data.products_indexed_count} productos en {data.price_lists_count} lista(s)
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <FileText className="h-4 w-4" />
                Historial de actividad
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {interactions.length === 0 ? (
                <p className="text-sm text-muted-foreground">Sin interacciones registradas.</p>
              ) : (
                interactions.slice(0, 8).map((i) => (
                  <div key={i.id} className="border-b pb-2 text-sm last:border-0">
                    <p className="font-medium capitalize">{i.interaction_type.replace("_", " ")} · {i.channel}</p>
                    {i.subject && <p className="text-xs text-muted-foreground">{i.subject}</p>}
                    <p className="text-xs text-muted-foreground">{new Date(i.created_at).toLocaleString()}</p>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </div>
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
