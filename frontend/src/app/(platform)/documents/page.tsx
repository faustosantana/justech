"use client";

import {
  AlertTriangle,
  FileText,
  FolderOpen,
  RefreshCw,
  Search,
  Upload,
} from "lucide-react";
import { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { AuthenticatedFileViewer } from "@/components/documents/authenticated-file-viewer";
import { AppShell } from "@/components/layout/app-shell";
import { BulkActionsBar } from "@/components/ui/bulk-actions-bar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { t } from "@/i18n";
import { ApiError, apiClient } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import {
  REPOSITORY_CATEGORY_FILTERS,
  type DocumentAlert,
  type DocumentHealth,
  type DocumentItem,
  type DocumentSearchHit,
  type KnowledgeAssetItem,
  type KnowledgeHealth,
} from "@/lib/documents";
import { cn } from "@/lib/utils";

const m = t();

export default function DocumentsPage() {
  return (
    <Suspense
      fallback={
        <AppShell title={m.documents.title} description={m.documents.description}>
          <p className="text-sm text-muted-foreground">{m.common.loading}</p>
        </AppShell>
      }
    >
      <DocumentsPageContent />
    </Suspense>
  );
}

function DocumentsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedId = searchParams.get("id");

  const [health, setHealth] = useState<DocumentHealth | null>(null);
  const [knowledgeHealth, setKnowledgeHealth] = useState<KnowledgeHealth | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [assets, setAssets] = useState<KnowledgeAssetItem[]>([]);
  const [total, setTotal] = useState(0);
  const [selectedAsset, setSelectedAsset] = useState<KnowledgeAssetItem | null>(null);
  const [alerts, setAlerts] = useState<DocumentAlert[]>([]);
  const [selected, setSelected] = useState<DocumentItem | null>(null);
  const [contentQuery, setContentQuery] = useState("");
  const [contentHits, setContentHits] = useState<DocumentSearchHit[]>([]);
  const [listSearch, setListSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [docTotal, setDocTotal] = useState(0);

  const downloadCsv = (csv: string, filename: string) => {
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const load = useCallback(async () => {
    if (!getAccessToken()) {
      router.replace("/login");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [h, kh, list, docList, alertList] = await Promise.all([
        apiClient.getDocumentsHealth(),
        apiClient.getKnowledgeHealth(),
        apiClient.listKnowledgeAssets({
          search: listSearch || undefined,
          repository_category: categoryFilter || undefined,
          limit: 200,
        }),
        apiClient.getDocuments({ search: listSearch || undefined, limit: 200 }),
        apiClient.getDocumentAlerts(),
      ]);
      setHealth(h);
      setKnowledgeHealth(kh);
      setAssets(list.items as KnowledgeAssetItem[]);
      setTotal(list.total);
      setDocuments(docList.items);
      setDocTotal(docList.total);
      setSelectedDocIds([]);
      setAlerts(alertList);
    } catch (err) {
      if (err instanceof Error && err.message === "UNAUTHORIZED") return;
      setError(
        err instanceof ApiError
          ? err.message
          : "No se pudo cargar el repositorio documental.",
      );
    } finally {
      setLoading(false);
    }
  }, [router, listSearch, categoryFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!selectedId) {
      setSelected(null);
      setSelectedAsset(null);
      return;
    }
    const asset = assets.find((a) => a.id === selectedId);
    if (asset) {
      setSelectedAsset(asset);
      setSelected(null);
      return;
    }
    apiClient
      .getDocument(selectedId)
      .then((doc) => {
        setSelected(doc);
        setSelectedAsset(null);
      })
      .catch(() => {
        setSelected(null);
        setSelectedAsset(null);
      });
  }, [selectedId, assets]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const doc = await apiClient.uploadDocument(file);
      await load();
      router.push(`/documents?id=${doc.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al registrar documento.");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleContentSearch = async () => {
    const q = contentQuery.trim();
    if (q.length < 2) return;
    setSearching(true);
    try {
      const res = await apiClient.searchDocuments(q);
      setContentHits(res.hits);
    } finally {
      setSearching(false);
    }
  };

  const handleScan = async () => {
    setScanning(true);
    try {
      await apiClient.syncKnowledgeRepository();
      await load();
    } finally {
      setScanning(false);
    }
  };


  const handleAnalyze = async (id: string) => {
    const doc = await apiClient.analyzeDocument(id);
    setSelected(doc);
    await load();
  };

  const handleCreateTask = async (id: string, title: string) => {
    await apiClient.createDocumentTask(id, `Revisar: ${title}`);
  };

  const summary = selected?.intelligence?.summary as string | undefined;
  const risks = (selected?.intelligence?.risks as string[] | undefined) ?? [];

  const cats = knowledgeHealth?.category_counts ?? {};

  return (
    <AppShell title={m.documents.title} description={m.documents.description}>
      <div className="space-y-6">
        {error && (
          <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        )}

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
          <MetricCard label="Archivos corporativos" value={cats.corporativos ?? total} />
          <MetricCard label="Documentos legales" value={cats.documento_legal ?? 0} />
          <MetricCard label="Plantillas/Formularios" value={cats.plantilla_formulario ?? 0} />
          <MetricCard label="Proveedores/Listas" value={cats.proveedor_lista_precios ?? 0} />
          <MetricCard label="Clientes/Cotizaciones" value={cats.clientes_cotizaciones ?? 0} />
          <MetricCard label="Fichas técnicas" value={cats.ficha_tecnica ?? 0} />
          <MetricCard
            label="Chunks internos"
            value={knowledgeHealth?.chunks_count ?? health?.chunks_count ?? 0}
            sub="No son documentos"
          />
        </div>

        <div className="flex flex-wrap gap-2">
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90">
            <Upload className="h-4 w-4" />
            {uploading ? m.documents.uploading : m.documents.upload}
            <input type="file" className="hidden" accept=".pdf,.docx,.xlsx,.txt,.csv,.rtf,.odt" onChange={handleUpload} disabled={uploading} />
          </label>
          <Button variant="outline" onClick={() => void handleScan()} disabled={scanning}>
            <FolderOpen className="mr-2 h-4 w-4" />
            {scanning ? "Sincronizando…" : "Sincronizar repositorio"}
          </Button>
          <Button variant="outline" onClick={() => void load()} disabled={loading}>
            <RefreshCw className={cn("mr-2 h-4 w-4", loading && "animate-spin")} />
            {m.common.refresh}
          </Button>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Search className="h-4 w-4" />
              {m.documents.contentSearch}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex gap-2">
              <input
                type="search"
                value={contentQuery}
                onChange={(e) => setContentQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void handleContentSearch()}
                placeholder={m.documents.contentSearchPlaceholder}
                className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm"
              />
              <Button onClick={() => void handleContentSearch()} disabled={searching}>
                {searching ? m.common.loading : m.common.search}
              </Button>
            </div>
            {contentHits.length > 0 && (
              <div className="divide-y rounded-lg border">
                {contentHits.map((hit) => (
                  <button
                    key={`${hit.document_id}-${hit.page_number}-${hit.snippet.slice(0, 20)}`}
                    type="button"
                    className="w-full px-4 py-3 text-left hover:bg-muted/50"
                    onClick={() => router.push(`/documents?id=${hit.document_id}`)}
                  >
                    <p className="font-medium text-sm">{hit.title}</p>
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{hit.snippet}</p>
                    <p className="text-[10px] text-muted-foreground mt-1">
                      Pág. {hit.page_number ?? "—"} · Relevancia {hit.score.toFixed(0)}
                    </p>
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-4">
            <div className="flex flex-wrap gap-2">
              <input
                type="search"
                value={listSearch}
                onChange={(e) => setListSearch(e.target.value)}
                placeholder={m.documents.filterPlaceholder}
                className="flex-1 min-w-[200px] rounded-lg border border-border bg-background px-3 py-2 text-sm"
              />
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
              >
                {REPOSITORY_CATEGORY_FILTERS.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>

            <BulkActionsBar
              selectedIds={selectedDocIds}
              allIds={documents.map((d) => d.id)}
              onSelectAll={() => setSelectedDocIds(documents.map((d) => d.id))}
              onClearSelection={() => setSelectedDocIds([])}
              actions={[
                {
                  id: "archive",
                  label: "Archivar",
                  variant: "destructive",
                  onRun: async (ids) => {
                    const res = await apiClient.bulkDocuments({ ids, action: "archive" });
                    await load();
                    return res.message;
                  },
                },
                {
                  id: "mark-review",
                  label: "Marcar revisión",
                  onRun: async (ids) => {
                    const res = await apiClient.bulkDocuments({ ids, action: "mark_review" });
                    await load();
                    return res.message;
                  },
                },
                {
                  id: "create-task",
                  label: "Crear tarea",
                  onRun: async (ids) => {
                    const res = await apiClient.bulkDocuments({ ids, action: "create_task" });
                    await load();
                    return res.message;
                  },
                },
                {
                  id: "export",
                  label: "Exportar listado",
                  onRun: async (ids) => {
                    const res = await apiClient.bulkDocuments({ ids, action: "export" });
                    if (res.export_csv) {
                      downloadCsv(res.export_csv, "documentos.csv");
                    }
                    return res.message;
                  },
                },
              ]}
            />

            <Card data-testid="documents-bulk-panel">
              <CardHeader>
                <CardTitle className="text-base">
                  Documentos registrados ({docTotal})
                </CardTitle>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <p className="text-sm text-muted-foreground">{m.common.loading}</p>
                ) : documents.length === 0 ? (
                  <p className="text-sm text-muted-foreground" data-testid="documents-empty">
                    No hay documentos subidos. Use «Subir documento» para registrar archivos con acciones masivas.
                  </p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm" data-testid="documents-bulk-table">
                      <thead>
                        <tr className="border-b border-border text-left text-muted-foreground">
                          <th className="pb-2 pr-2 w-8" />
                          <th className="pb-2 pr-4">Documento</th>
                          <th className="pb-2 pr-4">Categoría</th>
                          <th className="pb-2 pr-4">Empresa</th>
                          <th className="pb-2">Cliente</th>
                        </tr>
                      </thead>
                      <tbody>
                        {documents.map((doc) => (
                          <tr
                            key={doc.id}
                            data-testid={`bulk-row-${doc.id}`}
                            className={cn(
                              "border-b border-border/50 hover:bg-muted/30",
                              selectedId === doc.id && "bg-primary/5",
                            )}
                          >
                            <td className="py-3 pr-2">
                              <input
                                type="checkbox"
                                checked={selectedDocIds.includes(doc.id)}
                                onChange={(e) =>
                                  setSelectedDocIds((prev) =>
                                    e.target.checked
                                      ? [...prev, doc.id]
                                      : prev.filter((id) => id !== doc.id),
                                  )
                                }
                              />
                            </td>
                            <td className="py-3 pr-4">
                              <button
                                type="button"
                                className="font-medium text-primary hover:underline text-left"
                                onClick={() => router.push(`/documents?id=${doc.id}`)}
                              >
                                {doc.display_name ?? doc.title ?? doc.filename}
                              </button>
                              <p className="text-xs text-muted-foreground">{doc.filename}</p>
                            </td>
                            <td className="py-3 pr-4 text-muted-foreground capitalize">{doc.category}</td>
                            <td className="py-3 pr-4 text-muted-foreground">{doc.company ?? "—"}</td>
                            <td className="py-3 text-muted-foreground">{doc.client_name ?? "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  {m.documents.repository} ({total})
                </CardTitle>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <p className="text-sm text-muted-foreground">{m.common.loading}</p>
                ) : assets.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No hay documentos corporativos indexados. Pulse «Sincronizar repositorio».
                  </p>
                ) : (
                  <div className="divide-y">
                    {assets.map((asset) => (
                      <button
                        key={asset.id}
                        type="button"
                        className={cn(
                          "flex w-full items-start gap-3 px-2 py-3 text-left hover:bg-muted/50 rounded-lg",
                          selectedId === asset.id && "bg-primary/5",
                        )}
                        onClick={() => router.push(`/documents?id=${asset.id}`)}
                      >
                        <FileText className="h-5 w-5 shrink-0 text-muted-foreground mt-0.5" />
                        <div className="min-w-0 flex-1">
                          <p className="font-medium text-sm truncate">
                            {asset.display_name ?? asset.filename}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {asset.display_type} · {asset.repository_category_label}
                            {asset.display_status ? ` · ${asset.display_status}` : ""}
                          </p>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <div className="space-y-4">
            {alerts.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base text-amber-600">
                    <AlertTriangle className="h-4 w-4" />
                    {m.documents.alerts}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {alerts.slice(0, 5).map((a) => (
                    <div key={a.id} className="rounded border px-3 py-2 text-xs">
                      <p className="font-medium">{a.title}</p>
                      <p className="text-muted-foreground mt-0.5">{a.message}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            <Card>
              <CardHeader>
                <CardTitle className="text-base">{m.documents.detail}</CardTitle>
              </CardHeader>
              <CardContent>
                {!selected && !selectedAsset ? (
                  <p className="text-sm text-muted-foreground">{m.documents.selectHint}</p>
                ) : selectedAsset ? (
                  <div className="space-y-3 text-sm">
                    <div>
                      <p className="font-semibold">{selectedAsset.display_name ?? selectedAsset.filename}</p>
                      <p className="text-xs text-muted-foreground">{selectedAsset.relative_path}</p>
                    </div>
                    <dl className="grid gap-2 text-xs">
                      <div className="flex justify-between gap-4">
                        <dt className="text-muted-foreground">Tipo</dt>
                        <dd className="font-medium text-right">{selectedAsset.display_type}</dd>
                      </div>
                      <div className="flex justify-between gap-4">
                        <dt className="text-muted-foreground">Categoría</dt>
                        <dd className="font-medium text-right">{selectedAsset.repository_category_label}</dd>
                      </div>
                      {selectedAsset.sncc_label && (
                        <div className="flex justify-between gap-4">
                          <dt className="text-muted-foreground">Formulario</dt>
                          <dd className="font-medium text-right">{selectedAsset.sncc_label}</dd>
                        </div>
                      )}
                      {selectedAsset.detected_supplier && (
                        <div className="flex justify-between gap-4">
                          <dt className="text-muted-foreground">Proveedor</dt>
                          <dd className="font-medium text-right">{selectedAsset.detected_supplier}</dd>
                        </div>
                      )}
                      {selectedAsset.requires_vigency && selectedAsset.valid_from && (
                        <div className="flex justify-between gap-4">
                          <dt className="text-muted-foreground">Fecha emisión</dt>
                          <dd className="font-medium text-right">{selectedAsset.valid_from}</dd>
                        </div>
                      )}
                      {selectedAsset.requires_vigency && selectedAsset.valid_until && (
                        <div className="flex justify-between gap-4">
                          <dt className="text-muted-foreground">Fecha vencimiento</dt>
                          <dd className="font-medium text-right">{selectedAsset.valid_until}</dd>
                        </div>
                      )}
                      <div className="flex justify-between gap-4">
                        <dt className="text-muted-foreground">Estado</dt>
                        <dd className="font-medium text-right">{selectedAsset.display_status}</dd>
                      </div>
                    </dl>
                    <AuthenticatedFileViewer
                      filePath={`/knowledge/assets/${selectedAsset.id}/file`}
                      filenameHint={selectedAsset.filename}
                      relativePath={selectedAsset.relative_path}
                      className="pt-4 border-t"
                    />
                  </div>
                ) : selected ? (
                  <div className="space-y-3 text-sm">
                    <div>
                      <p className="font-semibold">{selected.display_name ?? selected.filename}</p>
                      <p className="text-xs text-muted-foreground">{selected.filename}</p>
                    </div>
                    {summary && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                          {m.documents.summary}
                        </p>
                        <p className="mt-1 text-sm leading-relaxed">{summary}</p>
                      </div>
                    )}
                    {risks.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                          {m.documents.risks}
                        </p>
                        <ul className="mt-1 list-disc pl-4 space-y-0.5">
                          {risks.map((r) => (
                            <li key={r}>{r}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {selected.valid_until && (
                      <p className="text-xs">
                        <span className="text-muted-foreground">{m.documents.validUntil}: </span>
                        {selected.valid_until}
                      </p>
                    )}
                    <div className="flex flex-wrap gap-2 pt-2">
                      <Button size="sm" variant="outline" onClick={() => void handleAnalyze(selected.id)}>
                        {m.documents.reanalyze}
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => void handleCreateTask(selected.id, selected.title)}
                      >
                        {m.documents.createTask}
                      </Button>
                    </div>
                    <AuthenticatedFileViewer
                      filePath={`/documents/${selected.id}/download`}
                      filenameHint={selected.filename}
                      className="pt-4 border-t"
                    />
                  </div>
                ) : null}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

function MetricCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string | number;
  sub?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-2xl font-bold mt-1">{value}</p>
        {sub && <p className="text-[10px] text-muted-foreground mt-1">{sub}</p>}
      </CardContent>
    </Card>
  );
}
