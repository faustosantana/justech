"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Database, RefreshCw, Settings, Shield } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import {
  formatOdooAmount,
  type OdooCustomer,
  type OdooHealth,
  type OdooInvoice,
  type OdooOpportunity,
  type OdooProduct,
  type OdooQuotation,
  type OdooSaleHistoryItem,
  type OdooSummary,
  type OdooVendor,
} from "@/lib/odoo";
import { cn } from "@/lib/utils";

type TabId =
  | "resumen"
  | "clientes"
  | "productos"
  | "ventas"
  | "facturas"
  | "cotizaciones"
  | "oportunidades"
  | "proveedores";

export function OdooSectionView({ tab }: { tab: string }) {
  const tabId = tab as TabId;
  const [health, setHealth] = useState<OdooHealth | null>(null);
  const [summary, setSummary] = useState<OdooSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [customers, setCustomers] = useState<OdooCustomer[]>([]);
  const [products, setProducts] = useState<OdooProduct[]>([]);
  const [sales, setSales] = useState<OdooSaleHistoryItem[]>([]);
  const [quotations, setQuotations] = useState<OdooQuotation[]>([]);
  const [opportunities, setOpportunities] = useState<OdooOpportunity[]>([]);
  const [invoices, setInvoices] = useState<OdooInvoice[]>([]);
  const [vendors, setVendors] = useState<OdooVendor[]>([]);

  const connected = summary?.connected ?? false;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [h, s] = await Promise.all([apiClient.getOdooHealth(), apiClient.getOdooSummary()]);
      setHealth(h);
      setSummary(s);

      switch (tabId) {
        case "clientes": {
          const r = await apiClient.getOdooCustomers("", 50);
          setCustomers(r.items);
          break;
        }
        case "productos": {
          const r = await apiClient.getOdooProducts("", 50);
          setProducts(r.items);
          break;
        }
        case "ventas": {
          const r = await apiClient.getOdooSalesHistory({ limit: 50 });
          setSales(r.items);
          break;
        }
        case "cotizaciones": {
          const r = await apiClient.getOdooQuotations({ limit: 50 });
          setQuotations(r.items);
          break;
        }
        case "oportunidades": {
          const r = await apiClient.getOdooOpportunities({ limit: 50 });
          setOpportunities(r.items);
          break;
        }
        case "facturas": {
          const r = await apiClient.getOdooOpenInvoices({ limit: 50 });
          setInvoices(r.items);
          break;
        }
        case "proveedores": {
          const r = await apiClient.getOdooVendors("", 50);
          setVendors(r.items);
          break;
        }
        default:
          break;
      }
    } catch {
      setError("Error cargando datos de Odoo.");
    } finally {
      setLoading(false);
    }
  }, [tabId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!connected && !loading) {
    return (
      <Card className="border-amber-500/30 bg-amber-500/5">
        <CardContent className="flex items-center gap-3 py-4">
          <Database className="h-5 w-5 text-amber-700" />
          <div>
            <p className="font-medium">Odoo no conectado</p>
            <Link href="/configuracion/integraciones/odoo" className="text-sm text-primary underline">
              Configurar integración Odoo
            </Link>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {health?.read_only && (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-emerald-700">
              <Shield className="h-3 w-3" /> Solo lectura
            </span>
          )}
          {summary && tabId === "resumen" && (
            <span>
              {summary.customers} clientes · {summary.quotations} cotizaciones · {summary.open_invoices} facturas abiertas
            </span>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link href="/odoo/settings">
              <Settings className="mr-2 h-4 w-4" />
              Usuario Odoo
            </Link>
          </Button>
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
            <RefreshCw className={cn("mr-2 h-4 w-4", loading && "animate-spin")} />
            Actualizar
          </Button>
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {loading && <p className="text-sm text-muted-foreground">Cargando…</p>}

      {!loading && tabId === "resumen" && summary && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Clientes", summary.customers],
            ["Cotizaciones", summary.quotations],
            ["Facturas abiertas", summary.open_invoices],
            ["Vencidas", summary.overdue_invoices],
          ].map(([label, val]) => (
            <Card key={String(label)}>
              <CardContent className="py-4">
                <p className="text-2xl font-semibold tabular-nums">{val}</p>
                <p className="text-xs text-muted-foreground">{label}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {!loading && tabId === "clientes" && <SimpleTable headers={["Nombre", "Email", "Teléfono"]} rows={customers.map((c) => [c.name, c.email ?? "—", c.phone ?? "—"])} />}
      {!loading && tabId === "productos" && <SimpleTable headers={["Producto", "SKU", "Precio"]} rows={products.map((p) => [p.name, p.default_code ?? "—", formatOdooAmount(p.list_price)])} />}
      {!loading && tabId === "ventas" && <SimpleTable headers={["Pedido", "Cliente", "Producto", "Subtotal"]} rows={sales.map((s) => [s.order_name, s.partner_name, s.product_name, formatOdooAmount(s.subtotal)])} />}
      {!loading && tabId === "cotizaciones" && <SimpleTable headers={["Cotización", "Cliente", "Total", "Estado"]} rows={quotations.map((q) => [q.name, q.partner_name, formatOdooAmount(q.amount_total), q.state ?? "—"])} />}
      {!loading && tabId === "oportunidades" && <SimpleTable headers={["Oportunidad", "Cliente", "Monto", "Etapa"]} rows={opportunities.map((o) => [o.name, o.partner_name ?? "—", formatOdooAmount(o.expected_revenue), o.stage ?? "—"])} />}
      {!loading && tabId === "facturas" && <SimpleTable headers={["Factura", "Cliente", "Total", "Pendiente"]} rows={invoices.map((i) => [i.name, i.partner_name, formatOdooAmount(i.amount_total), formatOdooAmount(i.amount_residual)])} />}
      {!loading && tabId === "proveedores" && <SimpleTable headers={["Proveedor", "Email", "Teléfono"]} rows={vendors.map((v) => [v.name, v.email ?? "—", v.phone ?? "—"])} />}
    </div>
  );
}

function SimpleTable({ headers, rows }: { headers: string[]; rows: string[][] }) {
  if (!rows.length) return <p className="text-sm text-muted-foreground">Sin registros.</p>;
  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            {headers.map((h) => (
              <th key={h} className="px-4 py-2 text-left font-medium text-muted-foreground">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b last:border-0">
              {row.map((cell, j) => (
                <td key={j} className="px-4 py-2">{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
