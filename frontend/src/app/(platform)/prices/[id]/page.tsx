"use client";

import Link from "next/link";
import { ArrowLeft, Copy, ExternalLink, FileSpreadsheet, ShoppingCart, AlertTriangle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { t } from "@/i18n";
import { ApiError, apiClient } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import type { PriceOdooMatch, PriceProductDetail, PriceQuoteDraft } from "@/lib/prices";

const m = t();

function formatDate(value: string | null, estimated: boolean) {
  if (!value) return "—";
  const d = new Date(value);
  const label = d.toLocaleDateString("es-DO");
  return estimated ? `${label} (estimada por modificación del archivo)` : label;
}

export default function PriceDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params.id;

  const [product, setProduct] = useState<PriceProductDetail | null>(null);
  const [odooMatch, setOdooMatch] = useState<PriceOdooMatch | null>(null);
  const [draft, setDraft] = useState<PriceQuoteDraft | null>(null);
  const [clientName, setClientName] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!getAccessToken()) {
      router.replace("/login?session=expired");
      return;
    }
    setLoading(true);
    Promise.all([
      apiClient.getPriceProduct(id),
      apiClient.getPriceOdooMatch(id).catch(() => null),
    ])
      .then(([prod, odoo]) => {
        setProduct(prod);
        setOdooMatch(odoo);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : m.common.loading))
      .finally(() => setLoading(false));
  }, [id, router]);

  const prepareQuote = useCallback(async () => {
    if (!product) return;
    try {
      const res = await apiClient.createPriceQuoteDraft({
        product_id: product.id,
        client_name: clientName || undefined,
        quantity: Number(quantity) || 1,
      });
      setDraft(res);
      setActionMsg(
        res.task_id
          ? `Borrador creado. Tarea asignada a ventas. Ver en /prices/drafts o /tasks/${res.task_id}`
          : "Borrador de cotización creado en JAIOS.",
      );
    } catch (err) {
      setActionMsg(err instanceof ApiError ? err.message : "No se pudo crear el borrador.");
    }
  }, [product, clientName, quantity]);

  const copyLine = useCallback(async () => {
    const text = draft?.copy_line || product?.description;
    if (!text) return;
    await navigator.clipboard.writeText(text);
    setActionMsg("Línea copiada al portapapeles.");
  }, [draft, product]);

  if (loading) {
    return (
      <AppShell title={m.prices.productDetail} description={m.prices.description}>
        <p className="text-sm text-muted-foreground">{m.common.loading}</p>
      </AppShell>
    );
  }

  if (error || !product) {
    return (
      <AppShell title={m.prices.productDetail} description={m.prices.description}>
        <p className="text-sm text-destructive">{error ?? "Producto no encontrado"}</p>
        <Button variant="outline" className="mt-4" onClick={() => router.push("/prices")}>
          <ArrowLeft className="mr-2 h-4 w-4" /> Volver
        </Button>
      </AppShell>
    );
  }

  const priceUsed = product.preferred_price ?? product.price;
  const stockLabel = product.stock_text_original
    ?? (product.stock != null ? String(product.stock) : "sin stock informado");

  return (
    <AppShell title={m.prices.productDetail} description={product.description ?? product.sku ?? ""}>
      <div className="mb-4 flex flex-wrap gap-3">
        <Link href="/prices" className="text-sm text-primary hover:underline inline-flex items-center gap-1">
          <ArrowLeft className="h-3 w-3" /> Volver a Inteligencia de Precios
        </Link>
        <Link href="/prices/drafts" className="text-sm text-primary hover:underline">
          Ver borradores de cotización
        </Link>
      </div>

      {product.cotizable_warning && (
        <div className="mb-4 flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          {product.cotizable_warning}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-base">Resumen comercial</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <Row label="Clasificación" value={product.classification_label ?? product.product_type} />
            <Row label="Proveedor" value={product.supplier} />
            <Row label="Fabricante / Marca" value={`${product.manufacturer ?? "—"} / ${product.brand ?? "—"}`} />
            <Row label="SKU / MPN" value={`${product.sku ?? "—"} / ${product.mpn ?? "—"}`} />
            <Row label="Tipo" value={product.product_type} />
            <Row label="Categoría" value={product.category} />
            <Row label={product.comparison_price_label} value={priceUsed ? `${product.currency} ${priceUsed}` : "requiere revisión"} />
            <Row label="Columna precio" value={product.preferred_price_field} />
            <Row label="Stock" value={stockLabel} />
            <Row label="Columna stock" value={product.stock_source_column} />
            <Row label="Tránsito" value={product.in_transit != null ? String(product.in_transit) : "—"} />
            <Row label="Fecha lista" value={formatDate(product.source_file_date, product.source_file_date_estimated)} />
            <Row label="Indexado" value={new Date(product.indexed_at).toLocaleString("es-DO")} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-base">Origen del dato</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <Row label="Archivo" value={product.source_filename} />
            <Row label="Hoja" value={product.source_sheet} />
            <Row label="Fila" value={product.source_row?.toString()} />
            {odooMatch && (
              <div className="rounded-md bg-muted p-2 text-xs">
                Odoo: {odooMatch.message}
                {odooMatch.found && odooMatch.product_id && (
                  <Button size="sm" variant="link" className="h-auto p-0 ml-1" onClick={() => window.open(`/odoo/products/${odooMatch.product_id}`, "_blank")}>
                    Abrir producto en Odoo
                  </Button>
                )}
              </div>
            )}
            <div className="flex flex-wrap gap-2 pt-2">
              <Button size="sm" variant="outline" onClick={() => router.push(`/documents?search=${encodeURIComponent(product.source_filename)}`)}>
                <ExternalLink className="mr-1 h-3 w-3" /> Ver archivo origen
              </Button>
              <Button size="sm" variant="outline" onClick={() => window.open("/odoo", "_blank")}>
                Abrir Odoo
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-base">Precios originales del archivo</CardTitle></CardHeader>
          <CardContent className="text-sm space-y-1">
            {Object.entries(product.prices_original).map(([k, v]) => (
              <div key={k}><span className="text-muted-foreground">{k}:</span> {String(v)}</div>
            ))}
            {product.price_regular != null && <div>Precio regular: {product.currency} {product.price_regular}</div>}
            {product.price_discount != null && <div>Precio descuento: {product.currency} {product.price_discount}</div>}
            {product.price_rebate != null && <div>Rebate: {product.currency} {product.price_rebate}</div>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-base">Especificaciones detectadas</CardTitle></CardHeader>
          <CardContent className="text-sm space-y-1">
            <Row label="RAM" value={product.ram_gb ? `${product.ram_gb} GB` : null} />
            <Row label="Almacenamiento" value={product.storage_gb ? `${product.storage_gb} GB ${product.storage_type ?? ""}` : null} />
            <Row label="Procesador" value={product.processor} />
            <Row label="Pantalla" value={product.display} />
            <Row label="SO" value={product.operating_system} />
            <Row label="Garantía" value={product.warranty} />
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FileSpreadsheet className="h-4 w-4" /> Línea original Excel
          </CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="py-2 pr-4">Columna</th>
                <th className="py-2">Valor</th>
              </tr>
            </thead>
            <tbody>
              {product.raw_columns_json.map((col) => (
                <tr key={`${col.index}-${col.column}`} className="border-b border-border/40">
                  <td className="py-2 pr-4 font-mono text-xs">{col.column}</td>
                  <td className="py-2">{col.value == null ? "—" : String(col.value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {product.is_cotizable !== false && (
        <Card className="mt-6 border-primary/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ShoppingCart className="h-4 w-4" /> Preparar cotización
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Crea borrador operativo + tarea para ventas. No envía a Odoo automáticamente.
            </p>
            <div className="flex flex-wrap gap-2">
              <Input placeholder="Cliente (opcional)" value={clientName} onChange={(e) => setClientName(e.target.value)} className="max-w-xs" />
              <Input placeholder="Cantidad" value={quantity} onChange={(e) => setQuantity(e.target.value)} className="w-24" />
              <Button onClick={() => void prepareQuote()}>Preparar cotización</Button>
              <Button variant="outline" onClick={() => void copyLine()}><Copy className="mr-1 h-3 w-3" /> Copiar línea</Button>
            </div>
            {draft && (
              <div className="space-y-2">
                <div className="rounded-md bg-muted p-3 text-sm font-mono">{draft.copy_line}</div>
                {draft.task_id && (
                  <Button size="sm" onClick={() => router.push(`/tasks/${draft.task_id}`)}>
                    Ir a tarea de revisión
                  </Button>
                )}
              </div>
            )}
            {actionMsg && <p className="text-sm text-success">{actionMsg}</p>}
          </CardContent>
        </Card>
      )}
    </AppShell>
  );
}

function Row({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <span className="text-muted-foreground">{label}: </span>
      <span>{value ?? "—"}</span>
    </div>
  );
}
