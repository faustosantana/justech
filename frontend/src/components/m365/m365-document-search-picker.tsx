"use client";

import {
  ChevronRight,
  File,
  Folder,
  FolderOpen,
  Link2,
  Loader2,
  Search,
  Upload,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { DocumentViewLink } from "@/components/documents/document-view-button";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError, apiClient } from "@/lib/api";
import type { M365DocumentItem } from "@/lib/m365-documents";
import { isPathLikeM365Query, type M365DgcpChecklistTarget, type M365RepositoryTarget } from "@/lib/m365-query-utils";
import { sanitizeMicrosoftUrl } from "@/lib/m365-urls";
import { cn } from "@/lib/utils";

type TabId = "search" | "browse" | "recent" | "linked";

function formatSize(bytes?: number | null) {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value?: string | null) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleDateString("es-DO");
}

export function M365DocumentSearchPicker({
  open,
  onClose,
  companyId,
  entityId,
  entityType = "internal_company",
  representativeId,
  fieldKey,
  fieldLabel,
  requirementId,
  initialQuery = "",
  initialTab,
  mode = "both",
  title = "Buscar documento en Microsoft 365",
  onLinked,
  onImported,
  onSelected,
  dgcpChecklist,
  repositoryTarget,
  onDgcpAssociated,
  attachMode,
}: {
  open: boolean;
  onClose: () => void;
  companyId?: string;
  entityId?: string;
  entityType?: string;
  representativeId?: string;
  fieldKey?: string;
  fieldLabel?: string;
  requirementId?: string;
  initialQuery?: string;
  initialTab?: TabId;
  mode?: "link" | "import" | "both";
  title?: string;
  onLinked?: (message: string) => void;
  onImported?: (message: string) => void;
  onSelected?: (item: M365DocumentItem) => void;
  dgcpChecklist?: M365DgcpChecklistTarget;
  repositoryTarget?: M365RepositoryTarget;
  onDgcpAssociated?: (result: {
    checklist: import("@/lib/dgcp").DGCPChecklist;
    bid_package: import("@/lib/dgcp").DGCPBidPackage;
    expediente_status: string;
  }) => void;
  attachMode?: {
    label?: string;
    attaching?: boolean;
    onAttach: (item: M365DocumentItem) => void | Promise<void>;
  };
}) {
  const resolvedCompanyId = companyId || entityId || "";
  const [tab, setTab] = useState<TabId>(
    initialTab || (isPathLikeM365Query(initialQuery) ? "browse" : "search"),
  );
  const [search, setSearch] = useState(initialQuery);
  const [items, setItems] = useState<M365DocumentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [acting, setActing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<M365DocumentItem | null>(null);
  const [browseCtx, setBrowseCtx] = useState<{
    source_type: string;
    drive_id?: string;
    site_id?: string;
    folder_id?: string;
    label: string;
  }>({ source_type: "sites", label: "SharePoint sitios" });

  const [pathBrowse, setPathBrowse] = useState<string | null>(null);
  const [suggestFolderPath, setSuggestFolderPath] = useState<string | null>(null);

  const canAssociate = Boolean(
    (resolvedCompanyId && fieldKey) ||
      (dgcpChecklist?.opportunityId && dgcpChecklist?.itemId) ||
      repositoryTarget?.bindingId,
  );

  const m365PayloadFor = (item: M365DocumentItem) => ({
    item_id: item.item_id || item.id,
    drive_id: item.drive_id ?? undefined,
    source_type: item.source_type,
    site_id: item.site_id ?? undefined,
    name: item.name,
    web_url: item.web_url ?? undefined,
    path: item.path,
  });

  const loadSearch = useCallback(async () => {
    const q = search.trim();
    if (!q) {
      setItems([]);
      return;
    }
    if (isPathLikeM365Query(q)) {
      setTab("browse");
      setPathBrowse(q);
      return;
    }
    setLoading(true);
    setError(null);
    setSuggestFolderPath(null);
    try {
      const res = await apiClient.searchM365Documents(q, 40);
      setItems(res.items.filter((i) => !i.is_folder));
      if (!res.items.length) setError(res.message || "Sin resultados.");
      else setError(null);
      if (res.suggest_open_as_folder && res.folder_path) {
        setSuggestFolderPath(res.folder_path);
        setError(
          res.message ||
            "No pude buscar esa ruta como texto. ¿Quieres abrirla como carpeta?",
        );
      }
    } catch (err) {
      setItems([]);
      const msg = err instanceof ApiError ? err.message : "Error al buscar documentos.";
      setError(msg);
      if (isPathLikeM365Query(q)) {
        setSuggestFolderPath(q);
      }
    } finally {
      setLoading(false);
    }
  }, [search]);

  const loadPathBrowse = useCallback(async (folderPath: string) => {
    setLoading(true);
    setError(null);
    setSuggestFolderPath(null);
    try {
      const res = await apiClient.browseM365DocumentsByPath(folderPath, 80);
      setItems(res.items);
      if (res.message) setError(res.connected ? null : res.message);
      else setError(null);
    } catch (err) {
      setItems([]);
      setError(err instanceof ApiError ? err.message : "No se pudo abrir la carpeta indicada.");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadRecent = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getM365DocumentsRecent(40);
      setItems(res.items.filter((i) => !i.is_folder));
      if (!res.items.length) setError("No hay documentos indexados. Sincronice OneDrive/SharePoint primero.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar recientes.");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadBrowse = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.browseM365Documents({
        source_type: browseCtx.source_type,
        drive_id: browseCtx.drive_id,
        site_id: browseCtx.site_id,
        folder_id: browseCtx.folder_id,
      });
      setItems(res.items);
      if (!res.connected) setError(res.message);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al explorar carpetas.");
    } finally {
      setLoading(false);
    }
  }, [browseCtx]);

  useEffect(() => {
    if (!open) return;
    const q = initialQuery.trim();
    const pathLike = isPathLikeM365Query(q);
    const nextTab = initialTab || (pathLike ? "browse" : "search");
    setSearch(q);
    setSelected(null);
    setError(null);
    setSuggestFolderPath(null);
    setPathBrowse(pathLike ? q : null);
    setTab(nextTab);
    if (pathLike) {
      setBrowseCtx({ source_type: "onedrive", label: "OneDrive" });
    }
    if (nextTab === "browse" && pathLike) {
      void loadPathBrowse(q);
    }
  }, [open, initialQuery, initialTab, loadPathBrowse]);

  useEffect(() => {
    if (!open) return;
    const browsePath =
      pathBrowse ||
      (tab === "browse" && initialQuery.trim() && isPathLikeM365Query(initialQuery)
        ? initialQuery.trim()
        : null);
    if (tab === "search" && search.trim() && !isPathLikeM365Query(search)) {
      const t = window.setTimeout(() => void loadSearch(), 350);
      return () => window.clearTimeout(t);
    }
    if (tab === "browse" && browsePath) return;
    if (tab === "recent" || tab === "linked") void loadRecent();
    else if (tab === "browse") void loadBrowse();
  }, [open, tab, search, pathBrowse, initialQuery, loadSearch, loadPathBrowse, loadRecent, loadBrowse]);

  const openFolder = (item: M365DocumentItem) => {
    if (!item.is_folder) return;
    if (item.source_type === "sharepoint" && item.site_id && !item.drive_id) {
      setBrowseCtx({ source_type: "site_drives", site_id: item.site_id, label: item.name });
    } else if (item.drive_id) {
      setBrowseCtx({
        source_type: "sharepoint",
        drive_id: item.drive_id,
        site_id: item.site_id ?? undefined,
        folder_id: item.item_id ?? undefined,
        label: item.name,
      });
    } else {
      setBrowseCtx({
        source_type: "onedrive",
        folder_id: item.item_id ?? undefined,
        label: item.name,
      });
    }
    setSelected(null);
  };

  const repositoryPayloadFor = (item: M365DocumentItem) => ({
    binding_id: repositoryTarget!.bindingId,
    item_id: item.item_id || item.id,
    drive_id: item.drive_id ?? undefined,
    source_type: item.source_type,
    site_id: item.site_id ?? undefined,
    name: item.name,
    web_url: item.web_url ?? undefined,
    path: item.path,
  });

  const payloadFor = (item: M365DocumentItem) => ({
    company_id: resolvedCompanyId,
    field_key: fieldKey!,
    representative_id: representativeId,
    item_id: item.item_id || item.id,
    drive_id: item.drive_id ?? undefined,
    source_type: item.source_type,
    site_id: item.site_id ?? undefined,
    name: item.name,
    web_url: item.web_url ?? undefined,
    path: item.path,
    requirement_id: requirementId,
    entity_type: entityType,
    entity_id: entityId || resolvedCompanyId,
  });

  const linkDocument = async (item: M365DocumentItem) => {
    if (!canAssociate) return;
    setActing(`link:${item.id}`);
    setError(null);
    try {
      if (dgcpChecklist) {
        const result = await apiClient.linkDGCPChecklistM365(
          dgcpChecklist.opportunityId,
          dgcpChecklist.itemId,
          m365PayloadFor(item),
        );
        onDgcpAssociated?.(result);
        onLinked?.(
          result.document_title
            ? `Documento «${result.document_title}» asociado al requisito.`
            : "Documento vinculado desde Microsoft 365.",
        );
      } else if (repositoryTarget?.bindingId) {
        const res = await apiClient.linkM365RepositoryDocument(repositoryPayloadFor(item));
        onLinked?.(res.message);
      } else {
        const res = await apiClient.linkM365Document(payloadFor(item));
        onLinked?.(res.message);
      }
      onSelected?.(item);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No pude vincular el documento.");
    } finally {
      setActing(null);
    }
  };

  const importDocument = async (item: M365DocumentItem) => {
    if (!canAssociate) return;
    setActing(`import:${item.id}`);
    setError(null);
    try {
      if (dgcpChecklist) {
        const result = await apiClient.importDGCPChecklistM365(
          dgcpChecklist.opportunityId,
          dgcpChecklist.itemId,
          m365PayloadFor(item),
        );
        onDgcpAssociated?.(result);
        onImported?.(
          result.document_title
            ? `Documento «${result.document_title}» importado y asociado.`
            : "Documento importado desde Microsoft 365.",
        );
      } else if (repositoryTarget?.bindingId) {
        const res = await apiClient.importM365RepositoryDocument(repositoryPayloadFor(item));
        onImported?.(res.message);
      } else {
        const res = await apiClient.importM365Document(payloadFor(item));
        onImported?.(res.message);
      }
      onSelected?.(item);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No pude importar el documento.");
    } finally {
      setActing(null);
    }
  };

  const browseRoots = useMemo(
    () => [
      { id: "sites", label: "SharePoint sitios", source_type: "sites" },
      { id: "onedrive", label: "OneDrive", source_type: "onedrive" },
    ],
    [],
  );

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 p-4">
      <div className="flex max-h-[90vh] w-full max-w-3xl flex-col rounded-2xl border bg-background shadow-2xl">
        <div className="flex items-start justify-between border-b px-4 py-3">
          <div>
            <div className="flex items-center gap-2">
              <FolderOpen className="h-5 w-5 text-primary" />
              <p className="font-semibold">{title}</p>
            </div>
            {fieldLabel && (
              <p className="mt-1 text-xs text-muted-foreground">
                Requisito: <span className="font-medium text-foreground">{fieldLabel}</span>
              </p>
            )}
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-1 hover:bg-muted">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex gap-1 border-b px-4 pt-2">
          {(
            [
              ["search", "Buscar"],
              ["browse", "Explorar"],
              ["recent", "Recientes"],
              ["linked", "Vinculados"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => setTab(id)}
              className={cn(
                "rounded-t-lg px-4 py-2 text-sm font-medium",
                tab === id ? "bg-muted text-primary" : "text-muted-foreground hover:text-foreground",
              )}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="space-y-3 border-b px-4 py-3">
          {tab === "search" && (
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                className="pl-9"
                placeholder="Buscar por nombre o ruta…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void loadSearch()}
                autoFocus
              />
            </div>
          )}
          {tab === "browse" && (
            <div className="flex flex-wrap items-center gap-2">
              {pathBrowse ? (
                <>
                  <span className="font-mono text-xs text-muted-foreground">/{pathBrowse}</span>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setPathBrowse(null);
                      setBrowseCtx({ source_type: "onedrive", label: "OneDrive" });
                    }}
                  >
                    Salir de ruta
                  </Button>
                </>
              ) : (
                browseRoots.map((r) => (
                  <Button
                    key={r.id}
                    size="sm"
                    variant={browseCtx.source_type === r.source_type ? "default" : "outline"}
                    onClick={() => {
                      setBrowseCtx({ source_type: r.source_type, label: r.label });
                      setSelected(null);
                    }}
                  >
                    {r.label}
                  </Button>
                ))
              )}
              {!pathBrowse && (
                <span className="flex items-center text-xs text-muted-foreground">{browseCtx.label}</span>
              )}
            </div>
          )}
          {error && (
            <div className="space-y-2">
              <p className="text-sm text-amber-800">{error}</p>
              {suggestFolderPath && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setTab("browse");
                    setPathBrowse(suggestFolderPath);
                  }}
                >
                  Abrir carpeta
                </Button>
              )}
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto divide-y">
          {loading && (
            <p className="flex items-center gap-2 p-4 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Consultando Microsoft Graph…
            </p>
          )}
          {!loading && items.length === 0 && !error && (
            <p className="p-6 text-center text-sm text-muted-foreground">
              {tab === "search" ? "Escriba un término para buscar." : "Sin elementos en esta ubicación."}
            </p>
          )}
          {!loading &&
            items.map((item) => {
              const webUrl = sanitizeMicrosoftUrl(item.web_url);
              const isSelected = selected?.id === item.id;
              return (
                <div
                  key={`${item.source_type}-${item.id}`}
                  className={cn(
                    "px-4 py-3 hover:bg-muted/30",
                    isSelected && "bg-primary/5",
                    item.is_folder && "cursor-pointer",
                  )}
                  onClick={() => {
                    if (item.is_folder) openFolder(item);
                    else setSelected(item);
                  }}
                >
                  <div className="flex items-start gap-3">
                    {item.is_folder ? (
                      <Folder className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
                    ) : (
                      <File className="mt-0.5 h-5 w-5 shrink-0 text-sky-600" />
                    )}
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{item.name}</p>
                      <p className="truncate text-xs text-muted-foreground">
                        {item.source_label}
                        {item.path ? ` · /${item.path.replace(/^\/+/, "")}` : ""}
                      </p>
                      {!item.is_folder && (
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          Modificado: {formatDate(item.modified_at)} · {formatSize(item.size_bytes)}
                          {item.owner_name ? ` · ${item.owner_name}` : ""}
                        </p>
                      )}
                    </div>
                    {item.is_folder && <ChevronRight className="h-4 w-4 text-muted-foreground" />}
                  </div>
                  {!item.is_folder && isSelected && attachMode && (
                    <div className="mt-3 flex flex-wrap gap-2 pl-8">
                      <Button
                        size="sm"
                        className="bg-emerald-600 hover:bg-emerald-700"
                        disabled={!!acting || attachMode.attaching}
                        onClick={(e) => {
                          e.stopPropagation();
                          void attachMode.onAttach(item);
                        }}
                      >
                        {acting === `attach:${item.id}` || attachMode.attaching ? (
                          <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                        ) : (
                          <Upload className="mr-1 h-4 w-4" />
                        )}
                        {attachMode.label || "Adjuntar"}
                      </Button>
                      <DocumentViewLink
                        graphItemId={item.id}
                        webUrl={webUrl}
                        label="Ver en M365"
                        stopPropagation
                      />
                    </div>
                  )}
                  {!item.is_folder && isSelected && canAssociate && !attachMode && (
                    <div className="mt-3 flex flex-wrap gap-2 pl-8">
                      {(mode === "both" || mode === "link") && (
                        <Button
                          size="sm"
                          disabled={!!acting}
                          onClick={(e) => {
                            e.stopPropagation();
                            void linkDocument(item);
                          }}
                        >
                          {acting === `link:${item.id}` ? (
                            <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                          ) : (
                            <Link2 className="mr-1 h-4 w-4" />
                          )}
                          Vincular
                        </Button>
                      )}
                      {(mode === "both" || mode === "import") && (
                        <Button
                          size="sm"
                          variant="secondary"
                          disabled={!!acting}
                          onClick={(e) => {
                            e.stopPropagation();
                            void importDocument(item);
                          }}
                        >
                          {acting === `import:${item.id}` ? (
                            <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                          ) : (
                            <Upload className="mr-1 h-4 w-4" />
                          )}
                          Importar a JAIOS
                        </Button>
                      )}
                      <DocumentViewLink
                        graphItemId={item.id}
                        webUrl={webUrl ?? item.download_url}
                        label="Ver en M365"
                        stopPropagation
                      />
                    </div>
                  )}
                </div>
              );
            })}
        </div>

        <div className="flex items-center justify-between border-t px-4 py-3">
          <p className="text-xs text-muted-foreground">
            {attachMode
              ? "Seleccione un archivo y elija Adjuntar."
              : canAssociate
                ? "Seleccione un archivo y elija Vincular o Importar."
                : "Seleccione un requisito documental primero."}
          </p>
          <Button variant="ghost" onClick={onClose}>
            Cerrar
          </Button>
        </div>
      </div>
    </div>
  );
}
