"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { Database, RefreshCw, Search, Settings, Shield } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import {
  formatOdooAmount,
  type OdooCompany,
  type OdooCompanyContext,
  type OdooCustomer,
  type OdooHealth,
  type OdooInvoice,
  type OdooOpportunity,
  type OdooProduct,
  type OdooProject,
  type OdooQuotation,
  type OdooSaleHistoryItem,
  type OdooSummary,
  type OdooVendor,
} from "@/lib/odoo";
import { useAssistantContext } from "@/lib/assistant-context";
import { cn } from "@/lib/utils";

const TABS = [
  { id: "resumen", label: "Resumen" },
  { id: "clientes", label: "Clientes" },
  { id: "productos", label: "Productos" },
  { id: "ventas", label: "Histórico de ventas" },
  { id: "facturas", label: "Facturas" },
  { id: "cotizaciones", label: "Cotizaciones" },
  { id: "oportunidades", label: "Oportunidades" },
  { id: "proyectos", label: "Proyectos" },
  { id: "proveedores", label: "Proveedores" },
  { id: "consultas", label: "Consultas inteligentes" },
] as const;

type TabId = (typeof TABS)[number]["id"];

const EMPTY_SUMMARY: OdooSummary = {
  customers: 0,
  products: 0,
  open_invoices: 0,
  overdue_invoices: 0,
  quotations: 0,
  opportunities: 0,
  projects: 0,
  connected: false,
};

export default function OdooPage() {
  const router = useRouter();
  const [tab, setTab] = useState<TabId>("resumen");
  const [health, setHealth] = useState<OdooHealth | null>(null);
  const [companies, setCompanies] = useState<OdooCompany[]>([]);
  const [companyContext, setCompanyContext] = useState<OdooCompanyContext | null>(null);
  const [companySaving, setCompanySaving] = useState(false);
  const [summary, setSummary] = useState<OdooSummary>(EMPTY_SUMMARY);
  const [customers, setCustomers] = useState<OdooCustomer[]>([]);
  const [products, setProducts] = useState<OdooProduct[]>([]);
  const [sales, setSales] = useState<OdooSaleHistoryItem[]>([]);
  const [openInvoices, setOpenInvoices] = useState<OdooInvoice[]>([]);
  const [overdueInvoices, setOverdueInvoices] = useState<OdooInvoice[]>([]);
  const [quotations, setQuotations] = useState<OdooQuotation[]>([]);
  const [opportunities, setOpportunities] = useState<OdooOpportunity[]>([]);
  const [projects, setProjects] = useState<OdooProject[]>([]);
  const [vendors, setVendors] = useState<OdooVendor[]>([]);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [queryAnswer, setQueryAnswer] = useState<string | null>(null);
  const [queryLoading, setQueryLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);
  const { setContext: setAssistantContext } = useAssistantContext();

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const connected = health?.connected ?? false;

  const loadCore = useCallback(async () => {
    if (!getAccessToken()) {
      router.replace("/login");
      return;
    }
    setError(null);
    const results = await Promise.allSettled([
      apiClient.getOdooHealth(),
      apiClient.getOdooSummary(),
      apiClient.getOdooCompanies(),
      apiClient.getOdooCompanyContext(),
    ]);
    if (!mountedRef.current) return;

    if (results[0].status === "fulfilled") setHealth(results[0].value);
    if (results[1].status === "fulfilled") setSummary(results[1].value);
    if (results[2].status === "fulfilled") setCompanies(results[2].value.items);
    if (results[3].status === "fulfilled") {
      setCompanyContext(results[3].value);
      if (results[3].value.odoo_company_id) {
        setAssistantContext({ companyContextId: results[3].value.odoo_company_id });
      }
    }

    const allFailed = results.every((r) => r.status === "rejected");
    if (allFailed) {
      setError("No se pudo contactar el backend Odoo.");
    }
  }, [router, setAssistantContext]);

  const loadTabData = useCallback(async () => {
    if (!getAccessToken()) return;
    setLoading(true);
    try {
      switch (tab) {
        case "clientes": {
          const res = await apiClient.getOdooCustomers(search, 50);
          if (mountedRef.current) setCustomers(res.items);
          break;
        }
        case "productos": {
          const res = await apiClient.getOdooProducts(search, 50);
          if (mountedRef.current) setProducts(res.items);
          break;
        }
        case "ventas": {
          const res = await apiClient.getOdooSalesHistory({ limit: 50 });
          if (mountedRef.current) setSales(res.items);
          break;
        }
        case "facturas": {
          const [open, overdue] = await Promise.all([
            apiClient.getOdooOpenInvoices({ limit: 50 }),
            apiClient.getOdooOverdueInvoices({ limit: 50 }),
          ]);
          if (mountedRef.current) {
            setOpenInvoices(open.items);
            setOverdueInvoices(overdue.items);
          }
          break;
        }
        case "cotizaciones": {
          const res = await apiClient.getOdooQuotations({ limit: 50 });
          if (mountedRef.current) setQuotations(res.items);
          break;
        }
        case "oportunidades": {
          const res = await apiClient.getOdooOpportunities({ limit: 50 });
          if (mountedRef.current) setOpportunities(res.items);
          break;
        }
        case "proyectos": {
          const res = await apiClient.getOdooProjects({ limit: 50 });
          if (mountedRef.current) setProjects(res.items);
          break;
        }
        case "proveedores": {
          const res = await apiClient.getOdooVendors(search, 50);
          if (mountedRef.current) setVendors(res.items);
          break;
        }
        default:
          break;
      }
    } catch {
      if (mountedRef.current) setError("Error cargando datos de Odoo.");
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [tab, search]);

  useEffect(() => {
    loadCore().finally(() => {
      if (mountedRef.current) setLoading(false);
    });
  }, [loadCore]);

  useEffect(() => {
    if (tab !== "resumen" && tab !== "consultas") {
      loadTabData();
    }
  }, [tab, loadTabData]);

  const handleCompanyChange = async (companyId: string) => {
    const id = parseInt(companyId, 10);
    if (!id || companySaving) return;
    setCompanySaving(true);
    try {
      const ctx = await apiClient.setOdooCompanyContext(id);
      if (!mountedRef.current) return;
      setCompanyContext(ctx);
      setCompanies((prev) =>
        prev.map((c) => ({ ...c, selected_by_current_user: c.id === id })),
      );
      await loadCore();
      if (tab !== "resumen" && tab !== "consultas") {
        await loadTabData();
      }
    } catch {
      if (mountedRef.current) setError("No se pudo cambiar la empresa Odoo activa.");
    } finally {
      if (mountedRef.current) setCompanySaving(false);
    }
  };

  const handleRefresh = async () => {
    setLoading(true);
    await loadCore();
    if (tab !== "resumen" && tab !== "consultas") {
      await loadTabData();
    } else {
      setLoading(false);
    }
  };

  const handleQuery = async () => {
    if (!query.trim()) return;
    setQueryLoading(true);
    setQueryAnswer(null);
    try {
      const res = await apiClient.queryOdoo(query.trim());
      if (mountedRef.current) setQueryAnswer(res.answer);
    } catch {
      if (mountedRef.current) setQueryAnswer("No se pudo procesar la consulta.");
    } finally {
      if (mountedRef.current) setQueryLoading(false);
    }
  };

  const notConnectedBanner = !connected && (
    <Card className="border-amber-500/30 bg-warning/10">
      <CardContent className="flex items-center gap-3 py-4">
        <Database className="h-5 w-5 text-warning" />
        <div>
          <p className="font-medium text-amber-700">Odoo no conectado</p>
          <p className="text-sm text-muted-foreground">
            Configura ODOO_URL, ODOO_DB, ODOO_USERNAME y ODOO_API_KEY en el entorno del backend.
          </p>
        </div>
      </CardContent>
    </Card>
  );

  return (
    <AppShell
      title="Centro de Inteligencia Odoo"
      description="Consulta segura en modo solo lectura"
    >
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {connected && companies.length > 0 ? (
            <div className="flex items-center gap-2">
              <label htmlFor="odoo-company" className="text-sm font-medium text-muted-foreground">
                Empresa Odoo activa
              </label>
              <select
                id="odoo-company"
                value={
                  companyContext?.odoo_company_id?.toString() ??
                  companies.find((c) => c.selected_by_current_user)?.id?.toString() ??
                  ""
                }
                onChange={(e) => handleCompanyChange(e.target.value)}
                disabled={companySaving}
                className="rounded-lg border border-input bg-background px-3 py-2 text-sm min-w-[220px]"
              >
                <option value="" disabled>
                  Seleccionar empresa…
                </option>
                {companies
                  .filter((c) => c.is_active)
                  .map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
              </select>
            </div>
          ) : (
            <div />
          )}
          <div className="flex flex-wrap items-center gap-2">
            {health?.read_only && (
              <span className="flex items-center gap-1 rounded-full bg-success/10 px-3 py-1 text-xs font-medium text-success">
                <Shield className="h-3.5 w-3.5" />
                Solo lectura
              </span>
            )}
            {companyContext?.odoo_company_name && (
              <span className="text-xs text-muted-foreground">
                Filtrando: {companyContext.odoo_company_name}
              </span>
            )}
            <Button variant="outline" size="sm" asChild>
              <Link href="/odoo/settings">
                <Settings className="mr-2 h-4 w-4" />
                Mi usuario Odoo
              </Link>
            </Button>
            <Button variant="outline" size="sm" onClick={handleRefresh} disabled={loading}>
              <RefreshCw className={cn("mr-2 h-4 w-4", loading && "animate-spin")} />
              Actualizar
            </Button>
          </div>
        </div>
        {error && (
          <p className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-2 text-sm text-destructive">
            {error}
          </p>
        )}

        {notConnectedBanner}

        <div className="flex flex-wrap gap-1 border-b border-border pb-1">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={cn(
                "rounded-t-lg px-4 py-2 text-sm font-medium transition-colors",
                tab === t.id
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === "resumen" && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { label: "Clientes", value: summary.customers },
              { label: "Productos", value: summary.products },
              { label: "Facturas abiertas", value: summary.open_invoices },
              { label: "Facturas vencidas", value: summary.overdue_invoices },
              { label: "Cotizaciones", value: summary.quotations },
              { label: "Oportunidades", value: summary.opportunities },
              { label: "Proyectos", value: summary.projects },
            ].map((kpi) => (
              <Card key={kpi.label}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    {kpi.label}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-bold tabular-nums">
                    {connected ? kpi.value : "—"}
                  </p>
                </CardContent>
              </Card>
            ))}
            {health && (
              <Card className="sm:col-span-2 lg:col-span-4">
                <CardContent className="py-4 text-sm text-muted-foreground">
                  Estado: {health.message}
                  {health.version && ` · Odoo ${health.version}`}
                  {health.database && ` · DB ${health.database}`}
                  {summary.company_name && ` · Empresa: ${summary.company_name}`}
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {tab === "clientes" && (
          <DataSection
            loading={loading}
            connected={connected}
            search={search}
            onSearchChange={setSearch}
            onSearch={loadTabData}
            empty="Sin clientes"
          >
            <CustomerTable customers={customers} />
          </DataSection>
        )}

        {tab === "productos" && (
          <DataSection
            loading={loading}
            connected={connected}
            search={search}
            onSearchChange={setSearch}
            onSearch={loadTabData}
            empty="Sin productos"
          >
            <ProductTable products={products} />
          </DataSection>
        )}

        {tab === "ventas" && (
          <DataSection loading={loading} connected={connected} empty="Sin historial de ventas">
            <SimpleTable
              headers={["Pedido", "Cliente", "Producto", "Cant.", "Precio", "Margen %"]}
              rows={sales.map((s) => [
                s.order_name,
                s.partner_name,
                s.product_name,
                String(s.quantity),
                formatOdooAmount(s.unit_price),
                s.margin_pct != null ? `${s.margin_pct.toFixed(1)}%` : "—",
              ])}
            />
          </DataSection>
        )}

        {tab === "facturas" && (
          <div className="space-y-6">
            <div>
              <h3 className="mb-3 text-sm font-semibold">Abiertas ({openInvoices.length})</h3>
              <DataSection loading={loading} connected={connected} empty="Sin facturas abiertas">
                <InvoiceTable items={openInvoices} linkable />
              </DataSection>
            </div>
            <div>
              <h3 className="mb-3 text-sm font-semibold text-destructive">
                Vencidas ({overdueInvoices.length})
              </h3>
              <DataSection loading={loading} connected={connected} empty="Sin facturas vencidas">
                <InvoiceTable items={overdueInvoices} linkable />
              </DataSection>
            </div>
          </div>
        )}

        {tab === "cotizaciones" && (
          <DataSection loading={loading} connected={connected} empty="Sin cotizaciones pendientes">
            <SimpleTable
              headers={["Referencia", "Cliente", "Fecha", "Total", "Estado"]}
              rows={quotations.map((q) => [
                q.name,
                q.partner_name,
                q.date_order ?? "—",
                formatOdooAmount(q.amount_total),
                q.state,
              ])}
            />
          </DataSection>
        )}

        {tab === "oportunidades" && (
          <DataSection loading={loading} connected={connected} empty="Sin oportunidades CRM">
            <SimpleTable
              headers={["Nombre", "Cliente", "Ingreso esperado", "Prob.", "Etapa"]}
              rows={opportunities.map((o) => [
                o.name,
                o.partner_name ?? "—",
                formatOdooAmount(o.expected_revenue),
                `${o.probability}%`,
                o.stage ?? "—",
              ])}
            />
          </DataSection>
        )}

        {tab === "proyectos" && (
          <DataSection loading={loading} connected={connected} empty="Sin proyectos">
            <SimpleTable
              headers={["Nombre", "Cliente", "Etapa"]}
              rows={projects.map((p) => [p.name, p.partner_name ?? "—", p.stage ?? "—"])}
            />
          </DataSection>
        )}

        {tab === "proveedores" && (
          <DataSection
            loading={loading}
            connected={connected}
            search={search}
            onSearchChange={setSearch}
            onSearch={loadTabData}
            empty="Sin proveedores"
          >
            <VendorTable vendors={vendors} />
          </DataSection>
        )}

        {tab === "consultas" && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Consultas inteligentes</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Pregunta en lenguaje natural. Ejemplo: &quot;¿En cuánto se le vendió este artículo a
                Banco Ademi?&quot;
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleQuery()}
                  placeholder="Escribe tu pregunta…"
                  className="flex-1 rounded-lg border border-input bg-background px-3 py-2 text-sm"
                />
                <Button onClick={handleQuery} disabled={queryLoading || !query.trim()}>
                  <Search className="mr-2 h-4 w-4" />
                  Consultar
                </Button>
              </div>
              {queryLoading && <p className="text-sm text-muted-foreground">Analizando…</p>}
              {queryAnswer && (
                <div className="rounded-lg border border-border bg-muted/30 p-4 text-sm">
                  {queryAnswer}
                </div>
              )}
              {!connected && (
                <p className="text-sm text-warning">
                  Odoo no conectado — las consultas no pueden acceder a datos reales.
                </p>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </AppShell>
  );
}

function DataSection({
  children,
  loading,
  connected,
  search,
  onSearchChange,
  onSearch,
}: {
  children: ReactNode;
  loading: boolean;
  connected: boolean;
  search?: string;
  onSearchChange?: (v: string) => void;
  onSearch?: () => void;
  empty?: string;
}) {
  return (
    <div className="space-y-4">
      {onSearchChange && (
        <div className="flex gap-2">
          <input
            type="text"
            value={search ?? ""}
            onChange={(e) => onSearchChange(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onSearch?.()}
            placeholder="Buscar…"
            className="max-w-sm flex-1 rounded-lg border border-input bg-background px-3 py-2 text-sm"
          />
          <Button variant="outline" size="sm" onClick={onSearch}>
            <Search className="h-4 w-4" />
          </Button>
        </div>
      )}
      {loading ? (
        <p className="text-sm text-muted-foreground">Cargando…</p>
      ) : !connected ? (
        <p className="text-sm text-muted-foreground">Odoo no conectado</p>
      ) : (
        children
      )}
    </div>
  );
}

function SimpleTable({
  headers,
  rows,
  linkColumn,
  linkPrefix,
}: {
  headers: string[];
  rows: string[][];
  linkColumn?: number;
  linkPrefix?: string;
}) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">Sin resultados</p>;
  }
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/50">
            {headers.map((h) => (
              <th key={h} className="px-4 py-2 text-left font-medium text-muted-foreground">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-border last:border-0">
              {row.map((cell, j) => (
                <td key={j} className="px-4 py-2">
                  {linkColumn === j && linkPrefix && cell.startsWith("link:") ? (
                    <Link
                      href={`${linkPrefix}${cell.split(":")[1]}`}
                      className="text-primary hover:underline"
                    >
                      {cell.split(":").slice(2).join(":")}
                    </Link>
                  ) : (
                    cell
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CustomerTable({ customers }: { customers: OdooCustomer[] }) {
  if (customers.length === 0) return <p className="text-sm text-muted-foreground">Sin resultados</p>;
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/50">
            {["Nombre", "Email", "Teléfono", "RNC", "Ciudad"].map((h) => (
              <th key={h} className="px-4 py-2 text-left font-medium text-muted-foreground">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {customers.map((c) => (
            <tr key={c.id} className="border-b border-border last:border-0">
              <td className="px-4 py-2">
                <Link href={`/odoo/customers/${c.id}`} className="text-primary hover:underline">{c.name}</Link>
              </td>
              <td className="px-4 py-2">{c.email ?? "—"}</td>
              <td className="px-4 py-2">{c.phone ?? "—"}</td>
              <td className="px-4 py-2">{c.vat ?? "—"}</td>
              <td className="px-4 py-2">{c.city ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ProductTable({ products }: { products: OdooProduct[] }) {
  if (products.length === 0) return <p className="text-sm text-muted-foreground">Sin resultados</p>;
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/50">
            {["Código", "Nombre", "Precio lista", "Costo", "Stock"].map((h) => (
              <th key={h} className="px-4 py-2 text-left font-medium text-muted-foreground">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {products.map((p) => (
            <tr key={p.id} className="border-b border-border last:border-0">
              <td className="px-4 py-2">{p.default_code ?? "—"}</td>
              <td className="px-4 py-2">
                <Link href={`/odoo/products/${p.id}`} className="text-primary hover:underline">{p.name}</Link>
              </td>
              <td className="px-4 py-2">{formatOdooAmount(p.list_price)}</td>
              <td className="px-4 py-2">{formatOdooAmount(p.standard_price)}</td>
              <td className="px-4 py-2">{p.qty_available}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function VendorTable({ vendors }: { vendors: OdooVendor[] }) {
  if (vendors.length === 0) return <p className="text-sm text-muted-foreground">Sin resultados</p>;
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/50">
            {["Nombre", "Email", "Teléfono", "RNC", "Ciudad"].map((h) => (
              <th key={h} className="px-4 py-2 text-left font-medium text-muted-foreground">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {vendors.map((v) => (
            <tr key={v.id} className="border-b border-border last:border-0">
              <td className="px-4 py-2">
                <Link href={`/odoo/vendors/${v.id}`} className="text-primary hover:underline">{v.name}</Link>
              </td>
              <td className="px-4 py-2">{v.email ?? "—"}</td>
              <td className="px-4 py-2">{v.phone ?? "—"}</td>
              <td className="px-4 py-2">{v.vat ?? "—"}</td>
              <td className="px-4 py-2">{v.city ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function InvoiceTable({ items, linkable }: { items: OdooInvoice[]; linkable?: boolean }) {
  return (
    <SimpleTable
      headers={["Factura", "Cliente", "Vence", "Total", "Pendiente"]}
      rows={items.map((i) => [
        linkable ? `link:${i.id}:${i.name}` : i.name,
        i.partner_name,
        i.due_date ?? "—",
        formatOdooAmount(i.amount_total),
        formatOdooAmount(i.amount_residual),
      ])}
      linkColumn={linkable ? 0 : undefined}
      linkPrefix="/odoo/invoices/"
    />
  );
}
