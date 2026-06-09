"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { AskJaiosButton } from "@/components/odoo/ask-jaios-button";
import { CreateTaskButton } from "@/components/work/create-task-button";
import { AppShell } from "@/components/layout/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import { useAssistantContext } from "@/lib/assistant-context";
import { formatOdooAmount, type OdooInvoiceDetail } from "@/lib/odoo";

export default function OdooInvoiceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { setContext } = useAssistantContext();
  const [data, setData] = useState<OdooInvoiceDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setContext({ recordType: "invoice", recordId: id });
    apiClient.getOdooInvoiceDetail(parseInt(id, 10)).then(setData).finally(() => setLoading(false));
  }, [id, setContext]);

  if (loading) return <AppShell title="Factura"><p className="text-muted-foreground">Cargando…</p></AppShell>;
  if (!data?.connected) return <AppShell title="Factura"><p>Odoo no conectado</p></AppShell>;

  return (
    <AppShell title={data.name} description={`${data.partner_name} · ${data.payment_state || data.state}`}>
      <div className="mb-4 flex flex-wrap gap-2 items-center">
        <Link href="/odoo" className="text-sm text-primary hover:underline">← Odoo</Link>
        <Link href={`/odoo/customers/${data.partner_id}`} className="text-sm text-primary hover:underline">{data.partner_name}</Link>
        <AskJaiosButton question={`¿Qué se le vendió en la factura ${data.name}?`} />
        <CreateTaskButton
          eventType="factura_cliente"
          title={`Seguimiento factura ${data.name}`}
          description={`Seguimiento de factura ${data.name} — ${data.partner_name}`}
          customerName={data.partner_name}
          odooInvoiceId={data.id}
          odooCustomerId={data.partner_id}
          source="odoo_invoice"
          label="Crear tarea de seguimiento"
        />
        {Number(data.amount_residual) > 0 && (
          <CreateTaskButton
            eventType="cuenta_por_cobrar"
            title={`Cobro factura ${data.name}`}
            description={`Cobro pendiente ${data.amount_residual} — ${data.partner_name}`}
            customerName={data.partner_name}
            odooInvoiceId={data.id}
            source="odoo_invoice"
            label="Crear tarea de cobro"
          />
        )}
        {data.odoo_url && <a href={data.odoo_url} target="_blank" rel="noopener noreferrer" className="text-sm text-muted-foreground hover:underline">Ver en Odoo ↗</a>}
      </div>
      <div className="grid gap-4 md:grid-cols-5 mb-6">
        <Card><CardHeader><CardTitle className="text-sm">Total</CardTitle></CardHeader><CardContent className="text-xl font-bold">{formatOdooAmount(data.amount_total)}</CardContent></Card>
        <Card><CardHeader><CardTitle className="text-sm">Balance pendiente</CardTitle></CardHeader><CardContent className="text-xl font-bold text-amber-700">{formatOdooAmount(data.amount_residual)}</CardContent></Card>
        <Card><CardHeader><CardTitle className="text-sm">Fecha</CardTitle></CardHeader><CardContent>{data.invoice_date || "—"}</CardContent></Card>
        <Card><CardHeader><CardTitle className="text-sm">Vence</CardTitle></CardHeader><CardContent>{data.due_date || "—"}</CardContent></Card>
        <Card><CardHeader><CardTitle className="text-sm">Margen est.</CardTitle></CardHeader><CardContent>{data.margin_pct != null ? `${data.margin_pct.toFixed(1)}%` : "—"}</CardContent></Card>
      </div>
      <Card>
        <CardHeader><CardTitle className="text-base">Líneas ({data.lines.length})</CardTitle></CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b text-left text-muted-foreground">
              <th className="py-2">Producto</th><th>Cant.</th><th>Precio</th><th>Dto.</th><th>Subtotal</th><th>Impuestos</th><th>Margen</th>
            </tr></thead>
            <tbody>{data.lines.map((ln) => (
              <tr key={ln.id} className="border-b border-border">
                <td className="py-2">
                  {ln.product_id ? (
                    <Link href={`/odoo/products/${ln.product_id}`} className="text-primary hover:underline">{ln.product_name}</Link>
                  ) : ln.product_name}
                </td>
                <td>{ln.quantity}</td>
                <td>{formatOdooAmount(ln.unit_price)}</td>
                <td>{ln.discount}%</td>
                <td>{formatOdooAmount(ln.subtotal)}</td>
                <td className="text-muted-foreground">{ln.tax_names || "—"}</td>
                <td>{ln.margin_pct != null ? `${ln.margin_pct.toFixed(1)}%` : "—"}</td>
              </tr>
            ))}</tbody>
          </table>
        </CardContent>
      </Card>
    </AppShell>
  );
}
