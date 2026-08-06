"use client";

import { Component, type ReactNode } from "react";
import { AlertCircle, Loader2, RefreshCw, ShoppingCart } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useDgcpExpedienteContext } from "@/components/dgcp/dgcp-expediente-context";
import { isDgcpAutoExpedienteContextEnabled } from "@/lib/dgcp-expediente-context";
import type { DGCPCommercialSimilarItem } from "@/lib/dgcp-expediente-context";
import { formatCurrency, formatDate } from "@/lib/dgcp";
import { cn } from "@/lib/utils";

const EMPTY_MESSAGE = "No encontramos historial comercial relacionado.";
const ERROR_MESSAGE = "No se pudo cargar Comercial Odoo.";

function docLabel(type: string | null | undefined): string {
  if (type === "quotation") return "Cotización";
  if (type === "sale_order") return "Pedido";
  if (type === "invoice") return "Factura";
  return type?.trim() || "Documento";
}

function safeItemKey(item: DGCPCommercialSimilarItem, prefix: string, index: number): string {
  return `${prefix}-${item.id || item.document_number || `${prefix}-row-${index}`}`;
}

function CommercialRow({ item }: { item: DGCPCommercialSimilarItem }) {
  const unitPrice = item.unit_price;
  const hasPrice =
    unitPrice != null && unitPrice !== "" && Number.isFinite(Number(unitPrice));
  const marginPct =
    item.margin_pct != null && String(item.margin_pct).trim() !== ""
      ? String(item.margin_pct)
      : null;

  return (
    <div className="rounded border px-3 py-2 text-xs space-y-0.5">
      <p className="font-medium">{item.product_name?.trim() || "—"}</p>
      <p className="text-muted-foreground">
        {docLabel(item.document_type)}
        {item.document_number ? ` ${item.document_number}` : ""}
        {item.customer_name ? ` · ${item.customer_name}` : ""}
      </p>
      <p className="text-muted-foreground">
        {hasPrice ? formatCurrency(unitPrice, item.currency ?? "DOP") : "—"}
        {item.date ? ` · ${formatDate(item.date)}` : ""}
        {item.salesperson ? ` · ${item.salesperson}` : ""}
      </p>
      {(item.margin || marginPct) && (
        <p className="text-[10px] text-muted-foreground">
          Margen: {item.margin?.trim() || "—"}
          {marginPct ? ` (${marginPct}%)` : ""}
        </p>
      )}
    </div>
  );
}

function Metric({
  label,
  value,
  currency,
  formatAs = "currency",
}: {
  label: string;
  value: string | number | null | undefined;
  currency?: string | null;
  formatAs?: "currency" | "count" | "text";
}) {
  let display = "—";
  if (value != null && value !== "") {
    if (formatAs === "count") {
      display = String(value);
    } else if (formatAs === "text") {
      display = String(value);
    } else if (!Number.isNaN(Number(value))) {
      display = formatCurrency(value, currency ?? "DOP");
    } else {
      display = String(value);
    }
  }
  return (
    <div className="rounded-lg border p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold tabular-nums">{display}</p>
    </div>
  );
}

function CommercialOdooErrorCard({
  message,
  detail,
  onRetry,
  retrying,
}: {
  message: string;
  detail?: string | null;
  onRetry?: () => void;
  retrying?: boolean;
}) {
  return (
    <Card className="border-destructive/30">
      <CardContent className="py-4 space-y-3">
        <div className="flex items-start gap-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">{message}</p>
            {detail && <p className="text-xs text-muted-foreground mt-1">{detail}</p>}
          </div>
        </div>
        {onRetry && (
          <Button variant="outline" size="sm" disabled={retrying} onClick={onRetry}>
            <RefreshCw className={cn("h-3.5 w-3.5 mr-1", retrying && "animate-spin")} />
            Reintentar
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

class CommercialOdooErrorBoundary extends Component<
  { children: ReactNode; onRetry?: () => void },
  { hasError: boolean }
> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error) {
    console.error("[DgcpCommercialOdooPanel]", error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <CommercialOdooErrorCard
          message={ERROR_MESSAGE}
          onRetry={() => {
            this.setState({ hasError: false });
            this.props.onRetry?.();
          }}
        />
      );
    }
    return this.props.children;
  }
}

function DgcpCommercialOdooPanelInner() {
  const ctx = useDgcpExpedienteContext();
  const autoEnabled = isDgcpAutoExpedienteContextEnabled();

  if (!autoEnabled || !ctx?.enabled) {
    return (
      <Card>
        <CardContent className="py-4 text-sm text-muted-foreground">
          Contexto comercial automático deshabilitado. Active{" "}
          <code className="text-xs">NEXT_PUBLIC_DGCP_AUTO_EXPEDIENTE_CONTEXT</code>.
        </CardContent>
      </Card>
    );
  }

  if (ctx.loading && !ctx.commercial) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin shrink-0" />
          Buscando coincidencias Odoo…
        </CardContent>
      </Card>
    );
  }

  if (ctx.commercialStatus === "error" || ctx.commercialStatus === "skipped") {
    return (
      <Card>
        <CardHeader className="py-3">
          <CardTitle className="text-base flex items-center gap-2">
            <ShoppingCart className="h-4 w-4" />
            Comercial Odoo
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <p>{ctx.commercialStatus === "skipped"
            ? "Integración no disponible para la empresa activa en este momento."
            : (ctx.commercialMessage || ERROR_MESSAGE)}</p>
          {ctx.commercialStatus === "error" && (
            <Button variant="outline" size="sm" disabled={ctx.loading} onClick={() => void ctx.refresh(true)}>
              {ctx.loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              <span className="ml-2">Reintentar</span>
            </Button>
          )}
        </CardContent>
      </Card>
    );
  }

  const commercial = ctx.commercial;
  if (!commercial) {
    return (
      <Card>
        <CardContent className="py-4 text-sm text-muted-foreground">
          {ctx.historicalStatus === "skipped"
            ? "Sin datos comerciales todavía."
            : ctx.loading
              ? "Buscando coincidencias Odoo…"
              : EMPTY_MESSAGE}
        </CardContent>
      </Card>
    );
  }

  const quotes = commercial.quotes ?? [];
  const sales = commercial.sales ?? [];
  const hasRows = quotes.length > 0 || sales.length > 0;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between py-3">
          <CardTitle className="text-base flex items-center gap-2">
            <ShoppingCart className="h-4 w-4" />
            Ventas y cotizaciones similares (Odoo)
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            disabled={ctx.loading}
            onClick={() => void ctx.refresh(true)}
          >
            <RefreshCw className={cn("h-3.5 w-3.5", ctx.loading && "animate-spin")} />
          </Button>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div className="grid gap-3 sm:grid-cols-3">
            <Metric
              label="Último precio vendido"
              value={commercial.last_sold_price}
              currency={commercial.currency}
            />
            <Metric
              label="Precio promedio"
              value={commercial.avg_sold_price}
              currency={commercial.currency}
            />
            <Metric label="Coincidencias" value={commercial.total ?? 0} formatAs="count" />
          </div>

          {!hasRows && (
            <p className="text-muted-foreground text-xs">
              {commercial.message?.trim() || EMPTY_MESSAGE}
            </p>
          )}

          {quotes.length > 0 && (
            <section className="space-y-2">
              <p className="text-xs font-semibold uppercase text-muted-foreground">
                Cotizaciones similares
              </p>
              {quotes.map((item, index) => (
                <CommercialRow key={safeItemKey(item, "q", index)} item={item} />
              ))}
            </section>
          )}

          {sales.length > 0 && (
            <section className="space-y-2">
              <p className="text-xs font-semibold uppercase text-muted-foreground">
                Ventas similares
              </p>
              {sales.map((item, index) => (
                <CommercialRow key={safeItemKey(item, "s", index)} item={item} />
              ))}
            </section>
          )}

          {ctx.lastUpdated && (
            <p className="text-[10px] text-muted-foreground">
              Última actualización: {formatDate(ctx.lastUpdated)}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export function DgcpCommercialOdooPanel() {
  const ctx = useDgcpExpedienteContext();
  return (
    <CommercialOdooErrorBoundary onRetry={() => void ctx?.refresh(true)}>
      <DgcpCommercialOdooPanelInner />
    </CommercialOdooErrorBoundary>
  );
}
