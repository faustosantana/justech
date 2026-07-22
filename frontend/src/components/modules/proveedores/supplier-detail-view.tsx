"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
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
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { apiClient } from "@/lib/api";
import { moduleSectionHref } from "@/lib/modules/types";
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

export function SupplierDetailView({
  supplierId,
  backHref = "/apps/proveedores/directorio",
  backLabel = "← Directorio",
}: {
  supplierId: string;
  backHref?: string;
  backLabel?: string;
}) {
  const router = useRouter();
  const [data, setData] = useState<Supplier | null>(null);
  const [priceLists, setPriceLists] = useState<SupplierPriceListSummary[]>([]);
  const [interactions, setInteractions] = useState<SupplierInteraction[]>([]);
  const [editing, setEditing] = useState(false);
  const [quoteProducts, setQuoteProducts] = useState("");
  const [form, setForm] = useState<Partial<Supplier>>({});

  const reload = async () => {
    const [supplier, lists, inter] = await Promise.all([
      apiClient.getSupplier(supplierId),
      apiClient.getSupplierPriceLists(supplierId),
      apiClient.getSupplierInteractions(supplierId),
    ]);
    setData(supplier);
    setPriceLists(lists);
    setInteractions(inter);
  };

  useEffect(() => {
    reload().catch(() => router.replace(backHref));
  }, [supplierId, router, backHref]);

  if (!data) {
    return <p className="p-4 text-sm text-muted-foreground">Cargando proveedor…</p>;
  }

  const save = async () => {
    const updated = await apiClient.updateSupplier(supplierId, {
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
    await apiClient.deleteSupplier(supplierId);
    router.push(backHref);
  };

  const togglePreferred = async () => {
    const updated = await apiClient.markSupplierPreferred(supplierId, data.status !== "preferido");
    setData(updated);
  };

  const requestQuote = async (channel: "email" | "whatsapp" | "both") => {
    const products = quoteProducts
      ? quoteProducts.split(",").map((p) => p.trim()).filter(Boolean)
      : data.products_services?.slice(0, 5) ?? ["productos solicitados"];
    const quote = await apiClient.requestSupplierQuote(supplierId, { products, channel });
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
    <div className="space-y-4 p-1">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Link href={backHref} className="text-sm text-primary hover:underline">
          {backLabel}
        </Link>
        <p className="text-xs text-muted-foreground">
          {SUPPLIER_TYPE_LABELS[data.company_type]} · {SUPPLIER_STATUS_LABELS[data.status]}
        </p>
      </div>

      <div>
        <h1 className="text-xl font-semibold">{data.name}</h1>
        {data.legal_name && data.legal_name !== data.name && (
          <p className="text-sm text-muted-foreground">{data.legal_name}</p>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
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
            <Link href={`${moduleSectionHref("precios", "buscador")}?supplier=${encodeURIComponent(data.price_supplier_name)}`}>
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
                  <Field label="Condiciones de pago" value={form.payment_terms ?? ""} onChange={(v) => setForm({ ...form, payment_terms: v })} />
                  <Field label="Tiempo de entrega" value={form.delivery_time ?? ""} onChange={(v) => setForm({ ...form, delivery_time: v })} />
                </>
              ) : (
                <>
                  <Info label="RNC" value={data.tax_id} />
                  <Info label="Correo" value={data.email} />
                  <Info label="Teléfono" value={data.phone} />
                  <Info label="WhatsApp" value={data.whatsapp} />
                  <Info label="Contacto principal" value={data.primary_contact} />
                  <Info label="Dirección" value={data.address} />
                  <Info label="Condiciones comerciales" value={data.payment_terms || data.commercial_terms} />
                  <Info label="Tiempo de entrega" value={data.delivery_time} />
                  <Info label="Marcas" value={data.brands?.join(", ") || "—"} />
                  <Info label="Productos/servicios" value={data.products_services?.join(", ") || "—"} />
                  <div className="md:col-span-2 flex flex-wrap gap-1">
                    {data.categories.map((c) => (
                      <Badge key={c.id} variant="secondary">{c.name}</Badge>
                    ))}
                  </div>
                </>
              )}
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
                <p className="text-sm text-muted-foreground">Sin listas vinculadas.</p>
              ) : (
                priceLists.map((pl) => (
                  <div key={pl.id} className="rounded-md border p-3 text-sm">
                    <p className="font-medium">{pl.filename || "Lista"}</p>
                    <p className="text-xs text-muted-foreground">{pl.product_count} productos</p>
                  </div>
                ))
              )}
              <Link href={moduleSectionHref("precios", "listas")} className="text-xs text-primary hover:underline">
                Ver inteligencia de precios →
              </Link>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <FileText className="h-4 w-4" />
                Historial
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {interactions.length === 0 ? (
                <p className="text-sm text-muted-foreground">Sin interacciones.</p>
              ) : (
                interactions.slice(0, 6).map((i) => (
                  <div key={i.id} className="border-b pb-2 text-sm last:border-0">
                    <p className="font-medium">{i.interaction_type} · {i.channel}</p>
                    <p className="text-xs text-muted-foreground">{new Date(i.created_at).toLocaleString()}</p>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
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

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <label className="text-xs text-muted-foreground">{label}</label>
      <Input value={value} onChange={(e) => onChange(e.target.value)} className="mt-1" />
    </div>
  );
}
