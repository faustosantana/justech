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
import { formatOdooAmount, type OdooCustomerDetail } from "@/lib/odoo";

export default function OdooCustomerDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { setContext } = useAssistantContext();
  const [data, setData] = useState<OdooCustomerDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const pid = parseInt(id, 10);
    setContext({ recordType: "customer", recordId: id });
    apiClient.getOdooCustomerDetail(pid).then(setData).finally(() => setLoading(false));
  }, [id, setContext]);

  if (loading) return <AppShell title="Cliente"><p className="text-muted-foreground">Cargando…</p></AppShell>;
  if (!data || data.message === "Odoo no conectado") {
    return <AppShell title="Cliente"><p>Odoo no conectado</p></AppShell>;
  }

  return (
    <AppShell title={data.name} description="Inteligencia de clientes — Odoo">
      <div className="mb-4 flex flex-wrap gap-2">
        <Link href="/odoo" className="text-sm text-primary hover:underline">← Odoo</Link>
        <AskJaiosButton question={`¿Qué facturas vencidas tiene ${data.name}?`} />
        <CreateTaskButton
          eventType="seguimiento_cliente"
          title={`Seguimiento cliente: ${data.name}`}
          description={`Tarea de seguimiento para ${data.name}`}
          customerName={data.name}
          odooCustomerId={data.id}
          source="odoo_customer"
          label="Crear tarea"
        />
      </div>
      <div className="grid gap-4 md:grid-cols-4 mb-6">
        <Card><CardHeader><CardTitle className="text-sm">Ventas históricas</CardTitle></CardHeader>
          <CardContent><p className="text-2xl font-bold">{formatOdooAmount(data.total_sales_historical)}</p></CardContent></Card>
        <Card><CardHeader><CardTitle className="text-sm">Deuda abierta</CardTitle></CardHeader>
          <CardContent><p className="text-2xl font-bold">{formatOdooAmount(data.total_due)}</p></CardContent></Card>
        <Card><CardHeader><CardTitle className="text-sm">Vencida</CardTitle></CardHeader>
          <CardContent><p className="text-2xl font-bold text-destructive">{formatOdooAmount(data.total_overdue)}</p></CardContent></Card>
        <Card><CardHeader><CardTitle className="text-sm">Contacto</CardTitle></CardHeader>
          <CardContent className="text-sm space-y-1">
            <p>{data.email || "—"}</p><p>{data.phone || "—"}</p><p>{data.vat || "—"}</p>
            <p className="text-muted-foreground">Vendedor: {data.salesperson || "—"}</p>
          </CardContent></Card>
      </div>
      <Section title={`Facturas abiertas (${data.open_invoices.length})`} items={data.open_invoices.map(i => ({ label: i.name, sub: `${formatOdooAmount(i.amount_residual)} pendiente`, href: `/odoo/invoices/${i.id}` }))} />
      <Section title={`Facturas vencidas (${data.overdue_invoices.length})`} items={data.overdue_invoices.map(i => ({ label: i.name, sub: `${formatOdooAmount(i.amount_residual)} · vence ${i.due_date}`, href: `/odoo/invoices/${i.id}` }))} />
      <Section title={`Cotizaciones (${data.quotations.length})`} items={data.quotations.map(q => ({ label: q.name, sub: formatOdooAmount(q.amount_total), href: null }))} />
      <Section title={`Oportunidades (${data.opportunities.length})`} items={data.opportunities.map(o => ({ label: o.name, sub: formatOdooAmount(o.expected_revenue), href: null }))} />
      <Section title={`Proyectos (${data.projects.length})`} items={data.projects.map(p => ({ label: p.name, sub: p.stage || "", href: null }))} />
      <Section
        title="Productos más comprados"
        items={data.products_purchased.map(p => ({
          label: p.product_name,
          sub: `${p.total_qty} uds · último ${formatOdooAmount(p.last_price)}`,
          href: p.product_id > 0 ? `/odoo/products/${p.product_id}` : null,
        }))}
      />
    </AppShell>
  );
}

function Section({ title, items }: { title: string; items: { label: string; sub: string; href: string | null }[] }) {
  return (
    <Card className="mb-4">
      <CardHeader><CardTitle className="text-base">{title}</CardTitle></CardHeader>
      <CardContent>
        {items.length === 0 ? <p className="text-sm text-muted-foreground">Sin registros</p> : (
          <ul className="space-y-2">{items.map((it, i) => (
            <li key={i} className="flex justify-between text-sm border-b border-border pb-2">
              {it.href ? <Link href={it.href} className="text-primary hover:underline">{it.label}</Link> : <span>{it.label}</span>}
              <span className="text-muted-foreground">{it.sub}</span>
            </li>
          ))}</ul>
        )}
      </CardContent>
    </Card>
  );
}
