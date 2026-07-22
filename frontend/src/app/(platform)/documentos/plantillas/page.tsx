"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ExternalLink,
  Eye,
  FileSpreadsheet,
  FileText,
  Filter,
  RefreshCw,
  Search,
} from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { DocumentViewButton } from "@/components/documents/document-view-button";
import { M365TemplateOperationalBanner } from "@/components/m365/m365-template-operational-banner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api";
import {
  COMPANY_OPTIONS,
  TEMPLATE_TYPE_LABELS,
  type DgcpTemplateItem,
  type DgcpTemplatesDashboard,
  type TemplatePreview,
} from "@/lib/licitador";

export default function PlantillasDgcpPage() {
  const [data, setData] = useState<DgcpTemplatesDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<string | null>(null);
  const [companyKey, setCompanyKey] = useState("justech");
  const [preview, setPreview] = useState<TemplatePreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [selected, setSelected] = useState<DgcpTemplateItem | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    apiClient
      .getDocumentsHubTemplates()
      .then(setData)
      .catch(() => apiClient.getLicitadorTemplatesDashboard().then(setData).catch(() => setData(null)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(() => {
    if (!data) return [];
    return data.templates.filter((t) => {
      if (category && t.document_category !== category) return false;
      if (search.trim()) {
        const q = search.toLowerCase();
        return t.name.toLowerCase().includes(q) || (t.template_type || "").includes(q);
      }
      return true;
    });
  }, [data, search, category]);

  const runPreview = async (template: DgcpTemplateItem) => {
    setSelected(template);
    setPreviewLoading(true);
    setPreview(null);
    try {
      const type = template.template_type?.toUpperCase() || template.name.split(".")[0];
      const res = await apiClient.previewLicitadorTemplate(type, companyKey);
      setPreview(res);
    } catch {
      setPreview(null);
    } finally {
      setPreviewLoading(false);
    }
  };

  const mimeIcon = (mime?: string | null) => {
    if (mime?.includes("spreadsheet") || mime?.includes("excel")) return FileSpreadsheet;
    return FileText;
  };

  return (
    <AppShell title="Plantillas DGCP" description="Formularios SNCC, ofertas y documentos oficiales">
      <div className="space-y-6">
        <M365TemplateOperationalBanner />
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="relative min-w-[200px] flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input className="pl-9" placeholder="Buscar plantilla…" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={load} disabled={loading}>
              <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Actualizar
            </Button>
            <Button size="sm" variant="outline" asChild>
              <Link href="/documentos/repositorios">Sync plantillas</Link>
            </Button>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-4">
          <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-transparent md:col-span-1">
            <CardContent className="pt-6">
              <p className="text-3xl font-semibold">{data?.total ?? 0}</p>
              <p className="text-xs text-muted-foreground">plantillas indexadas</p>
            </CardContent>
          </Card>
          <Card className="md:col-span-3">
            <CardContent className="flex flex-wrap items-center gap-2 pt-6">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <Button size="sm" variant={category === null ? "default" : "outline"} onClick={() => setCategory(null)}>
                Todas
              </Button>
              {Object.entries(data?.by_category || {}).map(([cat, count]) => (
                <Button key={cat} size="sm" variant={category === cat ? "default" : "outline"} onClick={() => setCategory(cat)}>
                  {cat} ({count})
                </Button>
              ))}
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <div className="space-y-3 lg:col-span-2">
            {filtered.length === 0 ? (
              <Card>
                <CardContent className="py-10 text-center text-sm text-muted-foreground">
                  No hay plantillas. Sincronice <code className="text-xs">02_PLANTILLAS/DGCP</code>.
                </CardContent>
              </Card>
            ) : (
              filtered.map((t) => {
                const Icon = mimeIcon(t.mime_type);
                return (
                  <Card key={t.id} className={selected?.id === t.id ? "border-primary ring-1 ring-primary/20" : ""}>
                    <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
                      <div className="flex min-w-0 flex-1 items-start gap-3">
                        <Icon className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
                        <div className="min-w-0">
                          <p className="truncate font-medium">{t.name}</p>
                          <p className="truncate text-xs text-muted-foreground">{t.parent_path || "OneDrive"}</p>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {t.template_type && (
                              <Badge variant="secondary">{TEMPLATE_TYPE_LABELS[t.template_type] || t.template_type}</Badge>
                            )}
                            {t.document_category && <Badge variant="outline">{t.document_category}</Badge>}
                          </div>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" onClick={() => runPreview(t)}>
                          <Eye className="mr-1 h-4 w-4" />
                          Autollenado
                        </Button>
                        <DocumentViewButton m365FileId={t.id} webUrl={t.web_url} label="Ver documento" variant="ghost" />
                      </div>
                    </CardContent>
                  </Card>
                );
              })
            )}
          </div>

          <Card className="h-fit lg:sticky lg:top-4">
            <CardHeader>
              <CardTitle className="text-base">Vista previa autollenado</CardTitle>
              <CardDescription>Datos desde 00_DATOS_EMPRESAS</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-2">
                {COMPANY_OPTIONS.map((c) => (
                  <Button key={c.key} size="sm" variant={companyKey === c.key ? "default" : "outline"} onClick={() => setCompanyKey(c.key)}>
                    {c.label}
                  </Button>
                ))}
              </div>
              {previewLoading && <p className="text-sm text-muted-foreground">Cargando campos…</p>}
              {preview && !previewLoading && (
                <>
                  <p className="text-sm font-medium">{preview.template_label}</p>
                  <div className="max-h-64 space-y-2 overflow-y-auto">
                    {preview.fields.map((f) => (
                      <div key={f.key} className="rounded-md border px-3 py-2 text-sm">
                        <p className="text-xs text-muted-foreground">{f.label}</p>
                        <p className="font-medium">{f.value || "—"}</p>
                      </div>
                    ))}
                  </div>
                </>
              )}
              {!preview && !previewLoading && (
                <p className="text-sm text-muted-foreground">Seleccione una plantilla y pulse Autollenado.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}
