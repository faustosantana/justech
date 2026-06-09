"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { AskJaiosButton } from "@/components/odoo/ask-jaios-button";
import { AppShell } from "@/components/layout/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import { useAssistantContext } from "@/lib/assistant-context";
import { formatOdooAmount, type OdooProductDetail } from "@/lib/odoo";

export default function OdooProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { setContext } = useAssistantContext();
  const [data, setData] = useState<OdooProductDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setContext({ recordType: "product", recordId: id });
    apiClient.getOdooProductDetail(parseInt(id, 10)).then(setData).finally(() => setLoading(false));
  }, [id, setContext]);

  if (loading) return <AppShell title="Producto"><p className="text-muted-foreground">Cargando…</p></AppShell>;
  if (!data?.connected) return <AppShell title="Producto"><p>Odoo no conectado</p></AppShell>;

  return (
    <AppShell title={data.name} description={data.default_code || data.category || "Producto Odoo"}>
      <div className="mb-4 flex gap-2">
        <Link href="/odoo" className="text-sm text-primary hover:underline">← Odoo</Link>
        <AskJaiosButton question={`¿Cuál fue el último precio vendido de ${data.name}?`} />
      </div>
      <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-6 mb-6">
        <Card><CardHeader><CardTitle className="text-sm">Precio lista</CardTitle></CardHeader><CardContent className="text-lg font-bold">{formatOdooAmount(data.list_price)}</CardContent></Card>
        <Card><CardHeader><CardTitle className="text-sm">Costo</CardTitle></CardHeader><CardContent className="text-lg font-bold">{formatOdooAmount(data.standard_price)}</CardContent></Card>
        <Card><CardHeader><CardTitle className="text-sm">Último vendido</CardTitle></CardHeader><CardContent className="text-lg font-bold">{formatOdooAmount(data.last_price)}</CardContent></Card>
        <Card><CardHeader><CardTitle className="text-sm">Promedio</CardTitle></CardHeader><CardContent className="text-lg font-bold">{formatOdooAmount(data.average_price)}</CardContent></Card>
        <Card><CardHeader><CardTitle className="text-sm">Mín / Máx</CardTitle></CardHeader><CardContent className="text-sm">{formatOdooAmount(data.min_price)} / {formatOdooAmount(data.max_price)}</CardContent></Card>
        <Card><CardHeader><CardTitle className="text-sm">Margen est.</CardTitle></CardHeader><CardContent className="text-lg font-bold">{data.estimated_margin_pct != null ? `${data.estimated_margin_pct.toFixed(1)}%` : "—"}</CardContent></Card>
      </div>
      <Card className="mb-4">
        <CardHeader><CardTitle className="text-base">Clientes compradores ({data.buyers.length})</CardTitle></CardHeader>
        <CardContent>
          {data.buyers.length === 0 ? <p className="text-sm text-muted-foreground">Sin ventas</p> : (
            <ul className="space-y-2">{data.buyers.map((b) => (
              <li key={b.partner_id} className="flex justify-between text-sm">
                <Link href={`/odoo/customers/${b.partner_id}`} className="text-primary hover:underline">{b.partner_name}</Link>
                <span className="text-muted-foreground">Último {formatOdooAmount(b.last_price)} · prom {formatOdooAmount(b.average_price)} · {b.sales_count} ventas</span>
              </li>
            ))}</ul>
          )}
        </CardContent>
      </Card>
      <Card className="mb-4">
        <CardHeader><CardTitle className="text-base">Histórico de ventas</CardTitle></CardHeader>
        <CardContent>
          <ul className="space-y-1 text-sm">{data.sales_history.slice(0, 25).map((s) => (
            <li key={s.id}>
              {s.partner_id ? <Link href={`/odoo/customers/${s.partner_id}`} className="text-primary hover:underline">{s.partner_name}</Link> : s.partner_name}
              {" — "}{formatOdooAmount(s.unit_price)} × {s.quantity}
            </li>
          ))}</ul>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle className="text-base">Histórico de compras (proveedores)</CardTitle></CardHeader>
        <CardContent>
          {data.purchase_history.length === 0 ? <p className="text-sm text-muted-foreground">Sin compras registradas</p> : (
            <ul className="space-y-1 text-sm">{data.purchase_history.slice(0, 25).map((p) => (
              <li key={p.id}>{p.vendor_name} — {p.order_name} — {formatOdooAmount(p.unit_price)} × {p.quantity}</li>
            ))}</ul>
          )}
        </CardContent>
      </Card>
    </AppShell>
  );
}
