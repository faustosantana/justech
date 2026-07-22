"use client";

import Link from "next/link";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  ExternalLink,
  FileText,
  ImageIcon,
  Loader2,
  RefreshCw,
  Sparkles,
  Trash2,
  Upload,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiClient } from "@/lib/api";
import type { DGCPTechSheetBrandingAssetStatus, DGCPTechSheetBrandingContext, DGCPTechSheetItem, DGCPTechSheetsResponse } from "@/lib/dgcp";
import { dgcpTechSheetsEnabled } from "@/lib/dgcp-feature-flags";
import { TECH_SHEET_BRANDING_GUIDE } from "@/lib/tech-sheet-branding-guide";
import { cn } from "@/lib/utils";

const STATUS_LABELS: Record<string, string> = {
  detectada: "Detectada",
  pendiente_producto: "Pendiente producto",
  lista_para_generar: "Lista para generar",
  borrador_generado: "Borrador generado",
  requiere_revision: "Requiere revisión",
  aprobada: "Aprobada",
  rechazada: "Rechazada",
  no_aplica: "No aplica",
};

const STATUS_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  detectada: "secondary",
  pendiente_producto: "outline",
  lista_para_generar: "default",
  borrador_generado: "default",
  requiere_revision: "destructive",
  aprobada: "default",
  rechazada: "destructive",
  no_aplica: "secondary",
};

type Props = {
  opportunityId: string;
};

export function DgcpTechnicalSheetsPanel({ opportunityId }: Props) {
  const enabled = dgcpTechSheetsEnabled();
  const [data, setData] = useState<DGCPTechSheetsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [detecting, setDetecting] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [productDraft, setProductDraft] = useState({
    brand: "",
    model: "",
    manufacturer: "",
    description: "",
    sku: "",
  });

  const load = useCallback(async () => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getDGCPTechnicalSheets(opportunityId);
      setData(res);
      setSelectedId((cur) => cur ?? res.items[0]?.id ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudieron cargar las fichas técnicas.");
    } finally {
      setLoading(false);
    }
  }, [enabled, opportunityId]);

  useEffect(() => {
    void load();
  }, [load]);

  const selected = useMemo(
    () => data?.items.find((i) => i.id === selectedId) ?? null,
    [data, selectedId],
  );

  useEffect(() => {
    if (!selected?.offered_product) return;
    setProductDraft({
      brand: selected.offered_product.brand ?? "",
      model: selected.offered_product.model ?? "",
      manufacturer: selected.offered_product.manufacturer ?? "",
      description: selected.offered_product.description ?? "",
      sku: selected.offered_product.sku ?? "",
    });
  }, [selected?.id, selected?.offered_product]);

  async function handleDetect() {
    setDetecting(true);
    setError(null);
    try {
      const res = await apiClient.detectDGCPTechnicalSheets(opportunityId);
      setData(res);
      if (res.items.length > 0) setSelectedId(res.items[0].id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al detectar fichas técnicas.");
    } finally {
      setDetecting(false);
    }
  }

  async function handleSelectProduct() {
    if (!selected) return;
    setError(null);
    try {
      const updated = await apiClient.selectDGCPTechSheetProduct(opportunityId, selected.id, {
        ...productDraft,
        source: "manual",
      });
      setData((prev) =>
        prev
          ? { ...prev, items: prev.items.map((i) => (i.id === updated.id ? updated : i)) }
          : prev,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo guardar el producto ofertado.");
    }
  }

  async function handleGenerateDraft() {
    if (!selected) return;
    setGenerating(true);
    setError(null);
    try {
      const res = await apiClient.generateDGCPTechSheetDraft(opportunityId, selected.id);
      await load();
      setSelectedId(res.sheet_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo generar el borrador.");
    } finally {
      setGenerating(false);
    }
  }

  async function handleApprove() {
    if (!selected) return;
    await apiClient.approveDGCPTechSheet(opportunityId, selected.id);
    await load();
  }

  async function handleReject() {
    if (!selected) return;
    await apiClient.rejectDGCPTechSheet(opportunityId, selected.id);
    await load();
  }

  async function handleExportMarkdown() {
    if (!selected) return;
    const res = await apiClient.exportDGCPTechSheet(opportunityId, selected.id, "markdown");
    const blob = new Blob([res.content], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = res.filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function handleExportPdf() {
    if (!selected) return;
    setError(null);
    try {
      await apiClient.exportDGCPTechSheetPdf(opportunityId, selected.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo exportar el PDF.");
    }
  }

  async function handleUploadImage(file: File) {
    if (!selected) return;
    setUploadingImage(true);
    setError(null);
    try {
      const updated = await apiClient.addDGCPTechSheetImage(opportunityId, selected.id, file);
      setData((prev) =>
        prev ? { ...prev, items: prev.items.map((i) => (i.id === updated.id ? updated : i)) } : prev,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo subir la imagen.");
    } finally {
      setUploadingImage(false);
    }
  }

  async function handleRemoveImage(imageId: string) {
    if (!selected) return;
    setError(null);
    try {
      const updated = await apiClient.removeDGCPTechSheetImage(opportunityId, selected.id, imageId);
      setData((prev) =>
        prev ? { ...prev, items: prev.items.map((i) => (i.id === updated.id ? updated : i)) } : prev,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo eliminar la imagen.");
    }
  }

  if (!enabled) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-sm text-muted-foreground">
          Fichas técnicas deshabilitadas (NEXT_PUBLIC_DGCP_TECH_SHEETS=false).
        </CardContent>
      </Card>
    );
  }

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center py-12 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin mr-2" />
        Cargando fichas técnicas…
      </div>
    );
  }

  const summary = data?.summary;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-base font-semibold flex items-center gap-2">
            <FileText className="h-4 w-4 text-primary" />
            Fichas Técnicas
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Borradores asistidos — requieren revisión humana. Nada se envía automáticamente.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
            <RefreshCw className={cn("h-3.5 w-3.5 mr-1", loading && "animate-spin")} />
            Actualizar
          </Button>
          <Button size="sm" onClick={() => void handleDetect()} disabled={detecting}>
            {detecting ? (
              <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
            ) : (
              <Sparkles className="h-3.5 w-3.5 mr-1" />
            )}
            Detectar bienes del pliego
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          <SummaryCard label="Total" value={summary.total} />
          <SummaryCard label="Pendientes producto" value={summary.pendientes_producto} />
          <SummaryCard label="Borradores" value={summary.borradores} />
          <SummaryCard label="Aprobadas" value={summary.aprobadas} />
          <SummaryCard label="Con riesgo" value={summary.con_riesgo} highlight={summary.con_riesgo > 0} />
          <SummaryCard label="Detectadas" value={summary.detectadas} />
        </div>
      )}

      {summary?.message && (
        <p className="text-sm text-muted-foreground">{summary.message}</p>
      )}

      {!data?.items.length ? (
        <Card>
          <CardContent className="py-10 text-center">
            <p className="text-sm text-muted-foreground">
              {summary?.requires_technical_sheets
                ? "No se detectaron bienes específicos. Ejecute «Detectar bienes del pliego» tras analizar requisitos, o use Expediente → Oferta técnica."
                : "No se detectaron fichas técnicas requeridas."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid lg:grid-cols-5 gap-4">
          <Card className="lg:col-span-2">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Listado de fichas</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <ul className="divide-y max-h-[480px] overflow-y-auto">
                {data.items.map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      onClick={() => setSelectedId(item.id)}
                      className={cn(
                        "w-full text-left px-4 py-3 hover:bg-muted/50 transition-colors",
                        selectedId === item.id && "bg-primary/5 border-l-2 border-primary",
                      )}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <p className="text-sm font-medium">{item.required_product_name}</p>
                          <p className="text-xs text-muted-foreground line-clamp-1">
                            {item.offered_product?.model ||
                              item.offered_product?.description ||
                              "Sin producto ofertado"}
                          </p>
                        </div>
                        <Badge variant={STATUS_VARIANT[item.status] ?? "secondary"} className="text-[10px] shrink-0">
                          {STATUS_LABELS[item.status] ?? item.status}
                        </Badge>
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          {selected && (
            <Card className="lg:col-span-3">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">{selected.required_product_name}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {selected.required_description && (
                  <p className="text-sm text-muted-foreground">{selected.required_description}</p>
                )}

                <div className="grid sm:grid-cols-2 gap-2 text-xs">
                  {selected.quantity && (
                    <Meta label="Cantidad" value={selected.quantity} />
                  )}
                  {selected.source_section && (
                    <Meta label="Fuente" value={selected.source_section} />
                  )}
                  {selected.source_page != null && (
                    <Meta label="Página" value={String(selected.source_page)} />
                  )}
                  <Meta label="Confianza" value={`${Math.round((selected.confidence || 0) * 100)}%`} />
                </div>

                {selected.required_specs.length > 0 && (
                  <div>
                    <p className="text-xs font-medium mb-1">Especificaciones mínimas (pliego)</p>
                    <ul className="text-xs text-muted-foreground list-disc pl-4 space-y-0.5">
                      {selected.required_specs.map((s) => (
                        <li key={s}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {!selected.offered_product?.model && !selected.offered_product?.description && (
                  <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-sm">
                    Seleccione o indique el producto que se ofertará para esta partida.
                  </div>
                )}

                <div className="space-y-2 rounded-lg border p-3">
                  <p className="text-xs font-medium">Producto ofertado</p>
                  <div className="grid sm:grid-cols-2 gap-2">
                    <Field label="Marca" value={productDraft.brand} onChange={(v) => setProductDraft((d) => ({ ...d, brand: v }))} />
                    <Field label="Modelo" value={productDraft.model} onChange={(v) => setProductDraft((d) => ({ ...d, model: v }))} />
                    <Field label="Fabricante" value={productDraft.manufacturer} onChange={(v) => setProductDraft((d) => ({ ...d, manufacturer: v }))} />
                    <Field label="SKU" value={productDraft.sku} onChange={(v) => setProductDraft((d) => ({ ...d, sku: v }))} />
                  </div>
                  <Field label="Descripción" value={productDraft.description} onChange={(v) => setProductDraft((d) => ({ ...d, description: v }))} />
                  <Button size="sm" variant="secondary" onClick={() => void handleSelectProduct()}>
                    Guardar producto ofertado
                  </Button>
                </div>

                {selected.branding && (
                  <BrandingSection branding={selected.branding} onRefresh={() => void load()} />
                )}

                <div className="space-y-2 rounded-lg border p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-xs font-medium flex items-center gap-1">
                      <ImageIcon className="h-3.5 w-3.5" />
                      Imágenes del producto
                    </p>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) void handleUploadImage(file);
                        e.target.value = "";
                      }}
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      type="button"
                      disabled={uploadingImage}
                      onClick={() => fileInputRef.current?.click()}
                    >
                      {uploadingImage ? (
                        <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                      ) : (
                        <Upload className="h-3.5 w-3.5 mr-1" />
                      )}
                      Subir imagen
                    </Button>
                  </div>
                  {(selected.product_images?.length ?? 0) === 0 ? (
                    <p className="text-xs text-muted-foreground italic">Imagen pendiente</p>
                  ) : (
                    <ul className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                      {[...(selected.product_images ?? [])]
                        .sort((a, b) => a.sort_order - b.sort_order)
                        .map((img) => (
                          <li key={img.id} className="relative rounded border p-2 text-xs">
                            <p className="font-medium truncate">{img.label ?? "Imagen"}</p>
                            <p className="text-muted-foreground truncate">{img.source}</p>
                            {img.url && (
                              // eslint-disable-next-line @next/next/no-img-element
                              <img src={img.url} alt={img.label ?? ""} className="mt-1 h-16 w-full object-contain rounded" />
                            )}
                            {!img.url && !img.local_path && (
                              <p className="mt-1 italic text-muted-foreground">Imagen pendiente</p>
                            )}
                            {img.id !== "offered-default" && (
                              <Button
                                size="icon"
                                variant="ghost"
                                className="absolute top-1 right-1 h-6 w-6"
                                onClick={() => void handleRemoveImage(img.id)}
                              >
                                <Trash2 className="h-3 w-3" />
                              </Button>
                            )}
                          </li>
                        ))}
                    </ul>
                  )}
                </div>

                {selected.missing_fields.length > 0 && (
                  <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3">
                    <p className="text-xs font-medium flex items-center gap-1 text-amber-700 dark:text-amber-400">
                      <AlertTriangle className="h-3.5 w-3.5" />
                      Información pendiente
                    </p>
                    <ul className="text-xs mt-1 flex flex-wrap gap-1">
                      {selected.missing_fields.map((f) => (
                        <Badge key={f} variant="outline" className="text-[10px]">
                          {f}
                        </Badge>
                      ))}
                    </ul>
                  </div>
                )}

                {selected.draft?.compliance_matrix && selected.draft.compliance_matrix.length > 0 && (
                  <div>
                    <p className="text-xs font-medium mb-2">Tabla de cumplimiento</p>
                    <div className="overflow-x-auto rounded border text-xs">
                      <table className="w-full">
                        <thead className="bg-muted/50">
                          <tr>
                            <th className="text-left p-2">Requisito pliego</th>
                            <th className="text-left p-2">Producto ofertado</th>
                            <th className="text-left p-2">Cumple</th>
                            <th className="text-left p-2">Observación</th>
                          </tr>
                        </thead>
                        <tbody>
                          {selected.draft.compliance_matrix.map((row, idx) => (
                            <tr key={idx} className="border-t">
                              <td className="p-2">{row.pliego_requirement}</td>
                              <td className="p-2">{row.offered_product ?? "—"}</td>
                              <td className="p-2">{row.complies}</td>
                              <td className="p-2 text-muted-foreground">{row.observation ?? "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {selected.draft?.review_notes && selected.draft.review_notes.length > 0 && (
                  <div>
                    <p className="text-xs font-medium mb-1">Notas de revisión</p>
                    <ul className="text-xs text-muted-foreground list-disc pl-4">
                      {selected.draft.review_notes.map((n) => (
                        <li key={n}>{n}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {selected.draft && (
                  <div>
                    <p className="text-xs font-medium mb-1">Vista previa del borrador</p>
                    <pre className="text-[11px] bg-muted/30 rounded p-3 max-h-48 overflow-y-auto whitespace-pre-wrap">
                      {JSON.stringify(selected.draft.header, null, 2)}
                    </pre>
                  </div>
                )}

                <div className="flex flex-wrap gap-2 pt-2 border-t">
                  <Button size="sm" onClick={() => void handleGenerateDraft()} disabled={generating}>
                    {generating ? (
                      <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                    ) : (
                      <Sparkles className="h-3.5 w-3.5 mr-1" />
                    )}
                    Generar borrador
                  </Button>
                  {selected.draft && (
                    <>
                      <Button size="sm" variant="outline" onClick={() => void handleExportMarkdown()}>
                        <Download className="h-3.5 w-3.5 mr-1" />
                        Exportar Markdown
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => void handleExportPdf()}>
                        <FileText className="h-3.5 w-3.5 mr-1" />
                        Exportar PDF
                      </Button>
                    </>
                  )}
                  <Button size="sm" variant="secondary" onClick={() => void handleApprove()}>
                    <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
                    Aprobar
                  </Button>
                  <Button size="sm" variant="destructive" onClick={() => void handleReject()}>
                    <XCircle className="h-3.5 w-3.5 mr-1" />
                    Rechazar
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

function BrandingSection({
  branding,
  onRefresh,
}: {
  branding: DGCPTechSheetBrandingContext;
  onRefresh?: () => void;
}) {
  const [companyId, setCompanyId] = useState<string | null>(null);
  const [companyProfileHref, setCompanyProfileHref] = useState<string | null>(null);
  const [uploading, setUploading] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void apiClient.getDocumentsHubDashboard().then((hub) => {
      if (cancelled) return;
      const card = hub.company_cards?.find((c) => c.company_key === branding.company_key);
      setCompanyId(card?.id ?? null);
      setCompanyProfileHref(card?.id ? `/apps/empresas-grupo/perfil/${card.id}` : null);
    }).catch(() => {
      if (!cancelled) {
        setCompanyId(null);
        setCompanyProfileHref(null);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [branding.company_key]);

  async function handleUpload(assetKey: "logo" | "signature" | "stamp", file: File) {
    setUploading(assetKey);
    setUploadError(null);
    try {
      if (assetKey === "logo") {
        if (!companyId) {
          throw new Error("Perfil empresarial no encontrado. Suba el logo desde Empresas del grupo.");
        }
        await apiClient.uploadDocumentsHubCompanyDocument(companyId, "logo", file);
      } else if (assetKey === "signature") {
        await apiClient.uploadCorporateSignature(file);
      } else {
        await apiClient.uploadCorporateStamp(branding.company_key, file);
      }
      onRefresh?.();
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "No se pudo subir el activo.");
    } finally {
      setUploading(null);
    }
  }

  return (
    <div className="space-y-3 rounded-lg border p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs font-medium">Activos corporativos — {branding.company_name}</p>
          <p className="text-[10px] text-muted-foreground mt-0.5">
            Requeridos para el PDF de ficha técnica. Suba archivos reales (no de prueba).
          </p>
        </div>
      </div>
      {uploadError && (
        <p className="text-[10px] text-destructive rounded border border-destructive/30 bg-destructive/5 p-2">
          {uploadError}
        </p>
      )}
      <div className="grid sm:grid-cols-3 gap-2">
        <BrandingAssetCard
          guide={TECH_SHEET_BRANDING_GUIDE.logo}
          asset={branding.logo}
          uploading={uploading === "logo"}
          onUpload={(file) => void handleUpload("logo", file)}
          manageHref={companyProfileHref}
          manageLabel="Perfil empresarial"
        />
        <BrandingAssetCard
          guide={TECH_SHEET_BRANDING_GUIDE.signature}
          asset={branding.signature}
          uploading={uploading === "signature"}
          onUpload={(file) => void handleUpload("signature", file)}
          manageHref="/documents/identity"
          manageLabel="Identidad corporativa"
        />
        <BrandingAssetCard
          guide={TECH_SHEET_BRANDING_GUIDE.stamp}
          asset={branding.stamp}
          uploading={uploading === "stamp"}
          onUpload={(file) => void handleUpload("stamp", file)}
          manageHref="/documents/identity"
          manageLabel="Identidad corporativa"
        />
      </div>
      <details className="text-[10px] text-muted-foreground">
        <summary className="cursor-pointer font-medium text-foreground">Requisitos de archivos (Justech)</summary>
        <ul className="mt-2 space-y-2 list-disc pl-4">
          <li>
            <strong>Logo:</strong> PNG ~700×340 px · OneDrive{" "}
            <code className="text-[9px]">Justech-AI/IDENTIDAD_CORPORATIVA/JUSTECH/</code> ·{" "}
            <code className="text-[9px]">document_type=logo</code>
          </li>
          <li>
            <strong>Firma:</strong> <code className="text-[9px]">firma_fausto.png</code> · PNG transparente ~600×200 px
          </li>
          <li>
            <strong>Sello:</strong> <code className="text-[9px]">sello_justech.png</code> · PNG transparente ~400×400 px
          </li>
        </ul>
      </details>
    </div>
  );
}

function BrandingAssetCard({
  guide,
  asset,
  uploading,
  onUpload,
  manageHref,
  manageLabel,
}: {
  guide: (typeof TECH_SHEET_BRANDING_GUIDE)["logo"];
  asset: DGCPTechSheetBrandingAssetStatus;
  uploading: boolean;
  onUpload: (file: File) => void;
  manageHref: string | null;
  manageLabel: string;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const isDetected = asset.status === "detectado";
  const statusLabel =
    asset.status === "detectado"
      ? "Detectado"
      : asset.status === "requiere_actualizacion"
        ? "Requiere actualización"
        : "Falta";
  const variant =
    asset.status === "detectado"
      ? "default"
      : asset.status === "requiere_actualizacion"
        ? "outline"
        : "destructive";

  return (
    <div className={cn("rounded border p-2 space-y-2", isDetected ? "border-emerald-500/30 bg-emerald-500/5" : "border-amber-500/30 bg-amber-500/5")}>
      <div className="flex items-center justify-between gap-1">
        <p className="font-medium text-xs">{guide.label}</p>
        {isDetected ? (
          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" aria-hidden />
        ) : (
          <XCircle className="h-3.5 w-3.5 text-amber-600 shrink-0" aria-hidden />
        )}
      </div>
      <Badge variant={variant} className="text-[10px]">
        {statusLabel}
      </Badge>
      <p className="text-[10px] text-muted-foreground">
        Esperado: <span className="font-mono">{asset.filename ?? guide.expectedFilename}</span>
      </p>
      <p className="text-[10px] text-muted-foreground">{guide.format} · {guide.sizeHint}</p>
      <p className="text-[10px] text-muted-foreground">{guide.backgroundHint}</p>
      <input
        ref={inputRef}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onUpload(file);
          e.target.value = "";
        }}
      />
      <div className="flex flex-col gap-1">
        <Button
          size="sm"
          variant="outline"
          type="button"
          className="h-7 text-[10px] justify-start"
          disabled={uploading}
          onClick={() => inputRef.current?.click()}
        >
          {uploading ? (
            <Loader2 className="h-3 w-3 mr-1 animate-spin" />
          ) : (
            <Upload className="h-3 w-3 mr-1" />
          )}
          Subir {guide.label.toLowerCase()}
        </Button>
        {manageHref && (
          <Button size="sm" variant="ghost" type="button" className="h-7 text-[10px] justify-start" asChild>
            <Link href={manageHref}>
              <ExternalLink className="h-3 w-3 mr-1" />
              {manageLabel}
            </Link>
          </Button>
        )}
      </div>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  highlight,
}: {
  label: string;
  value: number;
  highlight?: boolean;
}) {
  return (
    <Card className={cn(highlight && "border-amber-500/40")}>
      <CardContent className="py-3 px-4">
        <p className="text-[10px] uppercase text-muted-foreground">{label}</p>
        <p className="text-xl font-semibold">{value}</p>
      </CardContent>
    </Card>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-muted-foreground">{label}: </span>
      <span>{value}</span>
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
      <Label className="text-[10px]">{label}</Label>
      <Input className="h-8 text-xs" value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}
