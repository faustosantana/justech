"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import { useAssistantContext } from "@/lib/assistant-context";
import { formatOdooAmount, type OdooVendorDetail } from "@/lib/odoo";

export default function OdooVendorDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { setContext } = useAssistantContext();
  const [data, setData] = useState<OdooVendorDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setContext({ recordType: "vendor", recordId: id });
    apiClient.getOdooVendorDetail(parseInt(id, 10)).then(setData).finally(() => setLoading(false));
  }, [id, setContext]);

  if (loading) return <AppShell title="Proveedor"><p className="text-muted-foreground">Cargando…</p></AppShell>;
  if (!data?.connected) return <AppShell title="Proveedor"><p>Odoo no conectado</p></AppShell>;

  return (
    <AppShell title={data.name} description="Inteligencia de proveedores — Odoo">
      <Link href="/odoo" className="text-sm text-primary hover:underline mb-4 inline-block">← Odoo</Link>
      <div className="grid gap-4 md:grid-cols-2 mb-6">
        <Card>
          <CardHeader><CardTitle className="text-base">Datos</CardTitle></CardHeader>
          <CardContent className="text-sm space-y-1">
            <p>{data.email || "—"} · {data.phone || "—"}</p>
            <p>RNC: {data.vat || "—"} · {data.city || "—"}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Compras totales</CardTitle></CardHeader>
          <CardContent className="text-2xl font-bold">{formatOdooAmount(data.total_purchase_value)}</CardContent>
        </Card>
      </div>
      <Card className="mb-4">
        <CardHeader><CardTitle className="text-base">Productos suplidos ({data.products_supplied.length})</CardTitle></CardHeader>
        <CardContent>
          {data.products_supplied.length === 0 ? <p className="text-sm text-muted-foreground">Sin productos</p> : (
            <ul className="space-y-2 text-sm">{data.products_supplied.map((p) => (
              <li key={p.product_id} className="flex justify-between border-b border-border pb-2">
                <span>{p.product_name}</span>
                <span className="text-muted-foreground">
                  Último costo {formatOdooAmount(p.last_cost)} · {p.total_qty} uds · {p.purchase_count} compras
                </span>
              </li>
            ))}</ul>
          )}
        </CardContent>
      </Card>
      <Card className="mb-4">
        <CardHeader><CardTitle className="text-base">Órdenes de compra</CardTitle></CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm">{data.purchase_orders.map((po, i) => (
            <li key={i} className="flex justify-between"><span>{po.name}</span><span>{po.date} · {formatOdooAmount(po.amount_total)}</span></li>
          ))}</ul>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle className="text-base">Compras históricas</CardTitle></CardHeader>
        <CardContent>
          <ul className="space-y-1 text-sm">{data.purchase_history.map((p) => (
            <li key={p.id}>{p.product_name} — {p.quantity} × {formatOdooAmount(p.unit_price)} = {formatOdooAmount(p.subtotal)}</li>
          ))}</ul>
        </CardContent>
      </Card>
    </AppShell>
  );
}
