"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Loader2, MoreHorizontal, Plus, Upload } from "lucide-react";

import { AuthenticatedFileViewer } from "@/components/documents/authenticated-file-viewer";
import { DgcpAutofillDocumentPanel } from "@/components/dgcp/dgcp-autofill-document-panel";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiClient, ApiError } from "@/lib/api";
import { downloadAuthenticatedBlob, fetchAuthenticatedFile } from "@/lib/authenticated-file";
import {
  CHECKLIST_STATUS_LABELS,
  PROCESS_DOC_ROLE_LABELS,
  type DGCPChecklist,
  type DGCPChecklistItem,
  type DGCPFormPreview,
  type DGCPProcessDocument,
  type DGCPProcessDocuments,
} from "@/lib/dgcp";
import { dgcpSmartAutofillEnabled } from "@/lib/dgcp-feature-flags";
import type { DocumentItem, KnowledgeAssetItem } from "@/lib/documents";

const ACCEPT =
  ".pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.zip,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

type LinkFilter = "todos" | "corporativos" | "proceso" | "formularios" | "cargados";

type LinkCandidate = {
  key: string;
  kind: "knowledge" | "document" | "process";
  id: string;
  name: string;
  tipo: string;
  fecha: string;
  vigencia: string;
  origen: string;
  empresa: string;
  estado: string;
};

function apiErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error && err.message !== "UNAUTHORIZED") return err.message;
  return fallback;
}

function hasLinkedFile(item: DGCPChecklistItem): boolean {
  return Boolean(item.document_id || item.knowledge_asset_id || item.process_document_id);
}

function linkedFilePath(opportunityId: string, item: DGCPChecklistItem): string | null {
  if (item.process_document_id) {
    return `/dgcp/opportunities/${opportunityId}/process-documents/${item.process_document_id}/file?disposition=inline`;
  }
  if (item.knowledge_asset_id) {
    return `/knowledge/assets/${item.knowledge_asset_id}/file`;
  }
  if (item.document_id) {
    return `/documents/${item.document_id}/download`;
  }
  return null;
}

function RowMenu({
  actions,
}: {
  actions: Array<{ label: string; onClick: () => void; danger?: boolean }>;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative inline-block">
      <Button type="button" size="sm" variant="ghost" onClick={() => setOpen((v) => !v)}>
        <MoreHorizontal className="h-4 w-4" />
      </Button>
      {open ? (
        <div className="absolute right-0 z-20 mt-1 min-w-[200px] rounded-md border bg-background p-1 shadow-md">
          {actions.map((a) => (
            <button
              key={a.label}
              type="button"
              className={`block w-full rounded px-3 py-1.5 text-left text-sm hover:bg-muted ${a.danger ? "text-destructive" : ""}`}
              onClick={() => {
                setOpen(false);
                a.onClick();
              }}
            >
              {a.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function LinkExistingDocumentModal({
  processDocs,
  busy,
  onClose,
  onPick,
}: {
  opportunityId: string;
  processDocs: DGCPProcessDocument[];
  busy: boolean;
  onClose: () => void;
  onPick: (payload: {
    document_id?: string;
    knowledge_asset_id?: string;
    process_document_id?: string;
  }) => void;
}) {
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<LinkFilter>("todos");
  const [knowledge, setKnowledge] = useState<KnowledgeAssetItem[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);

  useEffect(() => {
    let cancelled = false;
    void Promise.all([
      apiClient.listKnowledgeAssets({ limit: 80 }),
      apiClient.getDocuments({ limit: 80 }),
    ])
      .then(([k, d]) => {
        if (cancelled) return;
        setKnowledge(k.items || []);
        setDocuments(d.items || []);
      })
      .catch(() => {
        if (!cancelled) {
          setKnowledge([]);
          setDocuments([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const candidates = useMemo(() => {
    const rows: LinkCandidate[] = [];
    for (const k of knowledge) {
      const isForm =
        (k.folder_category || "").includes("02_") ||
        (k.repository_category || "").includes("formulario") ||
        (k.document_type || "").toLowerCase().includes("form");
      rows.push({
        key: `k-${k.id}`,
        kind: "knowledge",
        id: k.id,
        name: k.title || k.display_name || k.filename,
        tipo: k.display_type || k.document_type || "corporativo",
        fecha: k.valid_from || "—",
        vigencia: k.valid_until || k.vigency_status || "—",
        origen: isForm ? "Formulario" : "Documento corporativo",
        empresa: k.company_key || "—",
        estado: k.display_status || k.vigency_status || "—",
      });
    }
    for (const d of documents) {
      rows.push({
        key: `d-${d.id}`,
        kind: "document",
        id: d.id,
        name: d.title || d.display_name || d.filename,
        tipo: d.category || d.format || "cargado",
        fecha: d.created_at?.slice(0, 10) || "—",
        vigencia: d.valid_until?.slice(0, 10) || "—",
        origen: "Documento cargado",
        empresa: d.company || d.client_name || "—",
        estado: d.analyzed_at ? "Analizado" : "Disponible",
      });
    }
    for (const p of processDocs) {
      rows.push({
        key: `p-${p.id}`,
        kind: "process",
        id: p.id,
        name: p.title,
        tipo: PROCESS_DOC_ROLE_LABELS[p.doc_role] ?? p.doc_role,
        fecha: (p as { created_at?: string }).created_at?.slice(0, 10) || "—",
        vigencia: "—",
        origen: p.doc_role === "formulario" ? "Formulario" : "Documento del proceso",
        empresa: "Proceso",
        estado: p.display_status || p.ingestion_status || "—",
      });
    }
    const q = query.trim().toLowerCase();
    return rows.filter((r) => {
      if (filter === "corporativos" && r.origen !== "Documento corporativo") return false;
      if (filter === "proceso" && r.origen !== "Documento del proceso") return false;
      if (filter === "formularios" && r.origen !== "Formulario") return false;
      if (filter === "cargados" && r.origen !== "Documento cargado") return false;
      if (!q) return true;
      return (
        r.name.toLowerCase().includes(q) ||
        r.tipo.toLowerCase().includes(q) ||
        r.origen.toLowerCase().includes(q) ||
        r.empresa.toLowerCase().includes(q)
      );
    });
  }, [knowledge, documents, processDocs, query, filter]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
      role="presentation"
    >
      <Card
        className="flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Enlazar archivo existente</CardTitle>
          <p className="text-sm text-muted-foreground">
            Seleccione un documento ya disponible. No se duplica el archivo físico. Debe validarlo
            después.
          </p>
        </CardHeader>
        <CardContent className="flex-1 space-y-3 overflow-y-auto">
          <div className="flex flex-wrap gap-2">
            <Input
              placeholder="Buscar por nombre, tipo, origen…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="max-w-sm"
            />
            {(
              [
                ["todos", "Todos"],
                ["corporativos", "Corporativos"],
                ["proceso", "Del proceso"],
                ["formularios", "Formularios"],
                ["cargados", "Cargados"],
              ] as Array<[LinkFilter, string]>
            ).map(([id, label]) => (
              <Button
                key={id}
                type="button"
                size="sm"
                variant={filter === id ? "default" : "outline"}
                onClick={() => setFilter(id)}
              >
                {label}
              </Button>
            ))}
          </div>
          {loading ? (
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Cargando documentos disponibles…
            </p>
          ) : candidates.length === 0 ? (
            <p className="text-sm text-muted-foreground">No hay documentos que coincidan con el filtro.</p>
          ) : (
            <div className="max-h-[50vh] overflow-x-auto rounded border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/30 text-left text-xs text-muted-foreground">
                    <th className="px-2 py-2">Nombre</th>
                    <th className="px-2 py-2">Tipo</th>
                    <th className="px-2 py-2">Fecha</th>
                    <th className="px-2 py-2">Vigencia</th>
                    <th className="px-2 py-2">Origen</th>
                    <th className="px-2 py-2">Empresa</th>
                    <th className="px-2 py-2">Estado</th>
                    <th className="px-2 py-2" />
                  </tr>
                </thead>
                <tbody>
                  {candidates.map((c) => (
                    <tr key={c.key} className="border-b border-border/40">
                      <td className="px-2 py-2 font-medium">{c.name}</td>
                      <td className="px-2 py-2 text-xs">{c.tipo}</td>
                      <td className="px-2 py-2 text-xs">{c.fecha}</td>
                      <td className="px-2 py-2 text-xs">{c.vigencia}</td>
                      <td className="px-2 py-2 text-xs">{c.origen}</td>
                      <td className="px-2 py-2 text-xs">{c.empresa}</td>
                      <td className="px-2 py-2 text-xs">{c.estado}</td>
                      <td className="px-2 py-2">
                        <Button
                          type="button"
                          size="sm"
                          disabled={busy}
                          onClick={() => {
                            if (c.kind === "knowledge") onPick({ knowledge_asset_id: c.id });
                            else if (c.kind === "document") onPick({ document_id: c.id });
                            else onPick({ process_document_id: c.id });
                          }}
                        >
                          Enlazar
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <Button type="button" variant="ghost" size="sm" onClick={onClose} disabled={busy}>
            Cancelar
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

export function DgcpDocumentosOperativosTab({
  opportunityId,
  opportunityCode,
  companyKey = "justech",
  formTypeHint,
}: {
  opportunityId: string;
  opportunityCode: string;
  companyKey?: string;
  formTypeHint?: string;
}) {
  const smartAutofill = dgcpSmartAutofillEnabled();
  const [checklist, setChecklist] = useState<DGCPChecklist | null>(null);
  const [processDocs, setProcessDocs] = useState<DGCPProcessDocuments | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [showAddReq, setShowAddReq] = useState(false);
  const [showUploadProcess, setShowUploadProcess] = useState(false);
  const [linkItemId, setLinkItemId] = useState<string | null>(null);
  const [previewItem, setPreviewItem] = useState<DGCPChecklistItem | null>(null);
  const [addForm, setAddForm] = useState({
    name: "",
    document_type: "",
    tipo: "administrativo",
    mandatory: true,
    description: "",
    source: "manual",
    page: "",
    due_date: "",
    assignee: "",
    notes: "",
  });
  const [uploadMeta, setUploadMeta] = useState({
    name: "",
    doc_role: "pliego",
    is_primary: true,
    include_in_analysis: true,
    observation: "",
  });
  const uploadRef = useRef<HTMLInputElement | null>(null);
  const itemUploadRef = useRef<HTMLInputElement | null>(null);
  const [uploadItemId, setUploadItemId] = useState<string | null>(null);
  const [formType, setFormType] = useState(formTypeHint || "SNCC.F042");
  const [formPreview, setFormPreview] = useState<DGCPFormPreview | null>(null);
  const [formQuery, setFormQuery] = useState("");

  useEffect(() => {
    if (formTypeHint) setFormType(formTypeHint);
  }, [formTypeHint]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [chk, docs] = await Promise.all([
        apiClient.getDGCPChecklist(opportunityId).catch(() => null),
        apiClient.getDGCPProcessDocuments(opportunityId).catch(() => null),
      ]);
      setChecklist(chk);
      setProcessDocs(docs);
    } catch (e) {
      setError(apiErrorMessage(e, "No se pudieron cargar documentos"));
    } finally {
      setLoading(false);
    }
  }, [opportunityId]);

  useEffect(() => {
    void load();
  }, [load]);

  const items = checklist?.items ?? [];
  const processItems = (processDocs?.items ?? []).filter((d) => d.source_type !== "portal");

  async function handleAddRequested() {
    if (!addForm.name.trim()) {
      setError("Indique el nombre del documento");
      return;
    }
    setBusy("add");
    setError(null);
    try {
      const res = await apiClient.addDGCPChecklistItem(opportunityId, {
        name: addForm.name.trim(),
        document_type: addForm.document_type || addForm.name,
        tipo: addForm.tipo,
        mandatory: addForm.mandatory,
        description: addForm.description || undefined,
        source: addForm.source || undefined,
        page: addForm.page || undefined,
        due_date: addForm.due_date || undefined,
        assignee: addForm.assignee || undefined,
        notes: addForm.notes || undefined,
      });
      setChecklist(res.checklist);
      setShowAddReq(false);
      setAddForm({
        name: "",
        document_type: "",
        tipo: "administrativo",
        mandatory: true,
        description: "",
        source: "manual",
        page: "",
        due_date: "",
        assignee: "",
        notes: "",
      });
      setMessage("Documento solicitado agregado.");
    } catch (e) {
      setError(apiErrorMessage(e, "No se pudo agregar el documento"));
    } finally {
      setBusy(null);
    }
  }

  async function handleUploadProcess(file: File) {
    setBusy("upload-process");
    setError(null);
    try {
      await apiClient.uploadDGCPProcessDocument(opportunityId, file, uploadMeta.doc_role);
      setMessage(`Documento subido al proceso: ${uploadMeta.name || file.name}`);
      setShowUploadProcess(false);
      await load();
    } catch (e) {
      setError(apiErrorMessage(e, "No se pudo subir el documento"));
    } finally {
      setBusy(null);
      if (uploadRef.current) uploadRef.current.value = "";
    }
  }

  async function handleItemUpload(itemId: string, file: File) {
    setBusy(`upload-${itemId}`);
    setError(null);
    try {
      const res = await apiClient.uploadDGCPChecklistDocument(opportunityId, itemId, file);
      setChecklist(res.checklist);
      setMessage("Archivo vinculado al documento solicitado.");
    } catch (e) {
      setError(apiErrorMessage(e, "No se pudo subir el archivo"));
    } finally {
      setBusy(null);
      setUploadItemId(null);
      if (itemUploadRef.current) itemUploadRef.current.value = "";
    }
  }

  async function handleLinkExisting(payload: {
    document_id?: string;
    knowledge_asset_id?: string;
    process_document_id?: string;
  }) {
    if (!linkItemId) return;
    setBusy(`link-${linkItemId}`);
    setError(null);
    try {
      const res = await apiClient.associateDGCPChecklistDocument(opportunityId, linkItemId, payload);
      setChecklist(res.checklist);
      setLinkItemId(null);
      setMessage("Archivo enlazado. Valide el documento para completarlo.");
    } catch (e) {
      setError(apiErrorMessage(e, "No se pudo enlazar el archivo"));
    } finally {
      setBusy(null);
    }
  }

  async function handleUnlink(item: DGCPChecklistItem) {
    setBusy(`unlink-${item.id}`);
    setError(null);
    try {
      const res = await apiClient.unlinkDGCPChecklistDocument(opportunityId, item.id);
      setChecklist(res.checklist);
      setMessage("Vínculo removido. El archivo físico no se eliminó.");
    } catch (e) {
      setError(apiErrorMessage(e, "No se pudo desenlazar"));
    } finally {
      setBusy(null);
    }
  }

  async function handleDownloadLinked(item: DGCPChecklistItem) {
    const path = linkedFilePath(opportunityId, item);
    if (!path) {
      setError("No hay archivo enlazado para descargar");
      return;
    }
    try {
      const file = await fetchAuthenticatedFile(
        path.replace("disposition=inline", "disposition=attachment"),
      );
      downloadAuthenticatedBlob(file.blob, item.document_title || file.filename || "documento");
    } catch (e) {
      setError(apiErrorMessage(e, "No se pudo descargar"));
    }
  }

  async function handleValidate(item: DGCPChecklistItem) {
    setBusy(`val-${item.id}`);
    try {
      const res = await apiClient.manualValidateDGCPRequirement(opportunityId, item.id, {
        status: "validado_manual",
        note: "Validado como completado desde Documentos solicitados",
      });
      setChecklist(res.checklist);
      setMessage("Documento validado. Checklist y expediente actualizados.");
    } catch (e) {
      setError(apiErrorMessage(e, "No se pudo validar"));
    } finally {
      setBusy(null);
    }
  }

  async function handleNoAplica(item: DGCPChecklistItem) {
    setBusy(`na-${item.id}`);
    try {
      const res = await apiClient.manualValidateDGCPRequirement(opportunityId, item.id, {
        status: "no_aplica",
        note: "Marcado como no aplica",
      });
      setChecklist(res.checklist);
      setMessage("Marcado como no aplica.");
    } catch (e) {
      setError(apiErrorMessage(e, "No se pudo actualizar"));
    } finally {
      setBusy(null);
    }
  }

  async function handleProcessFlag(
    doc: DGCPProcessDocument,
    patch: { is_primary?: boolean; include_in_analysis?: boolean; doc_role?: string },
  ) {
    setBusy(`flag-${doc.id}`);
    try {
      await apiClient.updateDGCPProcessDocumentFlags(opportunityId, doc.id, patch);
      setMessage("Documento de proceso actualizado.");
      await load();
    } catch (e) {
      setError(apiErrorMessage(e, "No se pudo actualizar el documento"));
    } finally {
      setBusy(null);
    }
  }

  const forms = ["SNCC.F033", "SNCC.F042", "SNCC.F047", "OFERTA.ECONOMICA", "CARTA.PRESENTACION"].filter(
    (f) => !formQuery || f.toLowerCase().includes(formQuery.toLowerCase()),
  );

  if (loading && !checklist && !processDocs) {
    return (
      <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Cargando documentos…
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {message ? (
        <p className="rounded-lg border border-success/30 px-3 py-2 text-sm text-success">{message}</p>
      ) : null}
      {error ? (
        <p className="rounded-lg border border-destructive/30 px-3 py-2 text-sm text-destructive">{error}</p>
      ) : null}

      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold">A. Documentos solicitados</h3>
          <Button type="button" size="sm" onClick={() => setShowAddReq(true)}>
            <Plus className="mr-1 h-4 w-4" />
            Agregar documento solicitado
          </Button>
        </div>
        {items.length === 0 ? (
          <Card>
            <CardContent className="py-6 text-sm text-muted-foreground">
              No hay documentos solicitados todavía. Analice el pliego o agregue uno manualmente.
            </CardContent>
          </Card>
        ) : (
          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/30 text-left text-xs text-muted-foreground">
                  <th className="px-3 py-2">Documento</th>
                  <th className="px-3 py-2">Tipo</th>
                  <th className="px-3 py-2">Obligatorio</th>
                  <th className="px-3 py-2">Fuente</th>
                  <th className="px-3 py-2">Responsable</th>
                  <th className="px-3 py-2">Estado</th>
                  <th className="px-3 py-2">Archivo</th>
                  <th className="px-3 py-2">Acción</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const linked = hasLinkedFile(item);
                  const actions: Array<{ label: string; onClick: () => void; danger?: boolean }> = [
                    {
                      label: "Enlazar existente",
                      onClick: () => setLinkItemId(item.id),
                    },
                    {
                      label: "Subir archivo nuevo",
                      onClick: () => {
                        setUploadItemId(item.id);
                        itemUploadRef.current?.click();
                      },
                    },
                  ];
                  if (linked) {
                    actions.push(
                      { label: "Ver documento", onClick: () => setPreviewItem(item) },
                      { label: "Descargar", onClick: () => void handleDownloadLinked(item) },
                      { label: "Reemplazar vínculo", onClick: () => setLinkItemId(item.id) },
                      {
                        label: "Desenlazar",
                        onClick: () => void handleUnlink(item),
                        danger: true,
                      },
                    );
                  }
                  actions.push(
                    {
                      label: "Validar documento",
                      onClick: () => void handleValidate(item),
                    },
                    {
                      label: "Marcar no aplica",
                      onClick: () => void handleNoAplica(item),
                    },
                  );
                  return (
                    <tr key={item.id} className="border-b border-border/40">
                      <td className="px-3 py-2 font-medium">{item.requirement}</td>
                      <td className="px-3 py-2 text-xs">{item.tipo}</td>
                      <td className="px-3 py-2">{item.mandatory ? "Sí" : "No"}</td>
                      <td className="px-3 py-2 text-xs">{item.match_source || "—"}</td>
                      <td className="px-3 py-2 text-xs">{item.assignee || "—"}</td>
                      <td className="px-3 py-2 text-xs">
                        {CHECKLIST_STATUS_LABELS[item.status] || item.display_status || item.status}
                      </td>
                      <td className="px-3 py-2 text-xs">{item.document_title || "—"}</td>
                      <td className="px-3 py-2">
                        <RowMenu actions={actions} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        <input
          ref={itemUploadRef}
          type="file"
          accept={ACCEPT}
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f && uploadItemId) void handleItemUpload(uploadItemId, f);
          }}
        />
        {showAddReq ? (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Agregar documento solicitado</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1 sm:col-span-2">
                <Label>Nombre del documento</Label>
                <Input
                  value={addForm.name}
                  onChange={(e) => setAddForm((s) => ({ ...s, name: e.target.value }))}
                  placeholder="Ej. Certificación bancaria"
                />
              </div>
              <div className="space-y-1">
                <Label>Tipo / código</Label>
                <Input
                  value={addForm.document_type}
                  onChange={(e) => setAddForm((s) => ({ ...s, document_type: e.target.value }))}
                  placeholder="Nuevo tipo si no existe"
                />
              </div>
              <div className="space-y-1">
                <Label>Categoría</Label>
                <select
                  className="h-9 w-full rounded-md border bg-background px-2 text-sm"
                  value={addForm.tipo}
                  onChange={(e) => setAddForm((s) => ({ ...s, tipo: e.target.value }))}
                >
                  <option value="legal">Legal</option>
                  <option value="tecnico">Técnico</option>
                  <option value="financiero">Financiero</option>
                  <option value="administrativo">Administrativo</option>
                  <option value="formulario">Formulario</option>
                </select>
              </div>
              <div className="space-y-1">
                <Label>Obligatorio</Label>
                <select
                  className="h-9 w-full rounded-md border bg-background px-2 text-sm"
                  value={addForm.mandatory ? "si" : "no"}
                  onChange={(e) => setAddForm((s) => ({ ...s, mandatory: e.target.value === "si" }))}
                >
                  <option value="si">Obligatorio</option>
                  <option value="no">Condicional</option>
                </select>
              </div>
              <div className="space-y-1">
                <Label>Responsable</Label>
                <Input
                  value={addForm.assignee}
                  onChange={(e) => setAddForm((s) => ({ ...s, assignee: e.target.value }))}
                />
              </div>
              <div className="space-y-1">
                <Label>Página del pliego</Label>
                <Input
                  value={addForm.page}
                  onChange={(e) => setAddForm((s) => ({ ...s, page: e.target.value }))}
                />
              </div>
              <div className="space-y-1">
                <Label>Fecha límite</Label>
                <Input
                  type="date"
                  value={addForm.due_date}
                  onChange={(e) => setAddForm((s) => ({ ...s, due_date: e.target.value }))}
                />
              </div>
              <div className="space-y-1 sm:col-span-2">
                <Label>Observaciones</Label>
                <Input
                  value={addForm.notes}
                  onChange={(e) => setAddForm((s) => ({ ...s, notes: e.target.value }))}
                />
              </div>
              <div className="flex gap-2 sm:col-span-2">
                <Button type="button" disabled={busy === "add"} onClick={() => void handleAddRequested()}>
                  {busy === "add" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  Guardar
                </Button>
                <Button type="button" variant="outline" onClick={() => setShowAddReq(false)}>
                  Cancelar
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : null}
      </section>

      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold">B. Documentos subidos en el proceso</h3>
          <Button type="button" size="sm" onClick={() => setShowUploadProcess(true)}>
            <Upload className="mr-1 h-4 w-4" />
            Subir documento al proceso
          </Button>
        </div>
        {processItems.length === 0 ? (
          <Card>
            <CardContent className="py-6 text-sm text-muted-foreground">
              No hay archivos del proceso. Suba el pliego, anexos o circulares.
            </CardContent>
          </Card>
        ) : (
          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/30 text-left text-xs text-muted-foreground">
                  <th className="px-3 py-2">Nombre</th>
                  <th className="px-3 py-2">Tipo</th>
                  <th className="px-3 py-2">Categoría</th>
                  <th className="px-3 py-2">Estado</th>
                  <th className="px-3 py-2">Principal</th>
                  <th className="px-3 py-2">Analizado</th>
                  <th className="px-3 py-2">Acción</th>
                </tr>
              </thead>
              <tbody>
                {processItems.map((doc) => {
                  const meta = (doc.metadata || {}) as Record<string, unknown>;
                  const isPrimary = Boolean(doc.is_primary ?? meta.is_primary);
                  const include = doc.include_in_analysis ?? meta.include_in_analysis ?? true;
                  return (
                    <tr key={doc.id} className="border-b border-border/40">
                      <td className="px-3 py-2 font-medium">{doc.title}</td>
                      <td className="px-3 py-2 text-xs">{doc.format}</td>
                      <td className="px-3 py-2 text-xs">
                        {PROCESS_DOC_ROLE_LABELS[doc.doc_role] ?? doc.doc_role}
                      </td>
                      <td className="px-3 py-2 text-xs">{doc.display_status || doc.ingestion_status}</td>
                      <td className="px-3 py-2 text-xs">{isPrimary ? "Sí" : "No"}</td>
                      <td className="px-3 py-2 text-xs">{doc.has_text ? "Sí" : "No"}</td>
                      <td className="px-3 py-2">
                        <RowMenu
                          actions={[
                            {
                              label: "Marcar como pliego principal",
                              onClick: () =>
                                void handleProcessFlag(doc, { is_primary: true, doc_role: "pliego" }),
                            },
                            {
                              label: include ? "Excluir del análisis" : "Incluir en análisis",
                              onClick: () =>
                                void handleProcessFlag(doc, { include_in_analysis: !include }),
                            },
                            {
                              label: "Reingestar",
                              onClick: () => {
                                void apiClient
                                  .reingestDGCPProcessDocument(opportunityId, doc.id)
                                  .then(() => load())
                                  .catch((e) => setError(apiErrorMessage(e, "No se pudo reingestar")));
                              },
                            },
                          ]}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {showUploadProcess ? (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Subir documento al proceso</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1 sm:col-span-2">
                <Label>Nombre (opcional)</Label>
                <Input
                  value={uploadMeta.name}
                  onChange={(e) => setUploadMeta((s) => ({ ...s, name: e.target.value }))}
                  placeholder={`Relacionado a ${opportunityCode}`}
                />
              </div>
              <div className="space-y-1">
                <Label>Categoría</Label>
                <select
                  className="h-9 w-full rounded-md border bg-background px-2 text-sm"
                  value={uploadMeta.doc_role}
                  onChange={(e) => setUploadMeta((s) => ({ ...s, doc_role: e.target.value }))}
                >
                  <option value="pliego">Pliego</option>
                  <option value="tdr">TDR</option>
                  <option value="anexo">Anexo</option>
                  <option value="enmienda">Enmienda / circular</option>
                  <option value="ficha_tecnica">Especificaciones</option>
                  <option value="cronograma">Cronograma</option>
                  <option value="contrato">Modelo de contrato</option>
                  <option value="formulario">Formulario</option>
                  <option value="general">Otro</option>
                </select>
              </div>
              <div className="space-y-1">
                <Label>Principal / analizar</Label>
                <div className="flex gap-3 pt-2 text-sm">
                  <label className="flex items-center gap-1">
                    <input
                      type="checkbox"
                      checked={uploadMeta.is_primary}
                      onChange={(e) => setUploadMeta((s) => ({ ...s, is_primary: e.target.checked }))}
                    />
                    Principal
                  </label>
                  <label className="flex items-center gap-1">
                    <input
                      type="checkbox"
                      checked={uploadMeta.include_in_analysis}
                      onChange={(e) =>
                        setUploadMeta((s) => ({ ...s, include_in_analysis: e.target.checked }))
                      }
                    />
                    Incluir en análisis
                  </label>
                </div>
              </div>
              <div className="flex gap-2 sm:col-span-2">
                <input
                  ref={uploadRef}
                  type="file"
                  accept={ACCEPT}
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) void handleUploadProcess(f);
                  }}
                />
                <Button
                  type="button"
                  disabled={busy === "upload-process"}
                  onClick={() => uploadRef.current?.click()}
                >
                  {busy === "upload-process" ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Upload className="mr-2 h-4 w-4" />
                  )}
                  Seleccionar archivo
                </Button>
                <Button type="button" variant="outline" onClick={() => setShowUploadProcess(false)}>
                  Cancelar
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : null}
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold">C. Formularios</h3>
        {smartAutofill ? (
          <DgcpAutofillDocumentPanel
            opportunityId={opportunityId}
            formType={formType}
            onFormTypeChange={setFormType}
            onGenerated={() => {
              setMessage("Formulario actualizado.");
              void load();
            }}
          />
        ) : (
          <Card>
            <CardContent className="space-y-3 pt-4">
              <Input
                placeholder="Buscar formulario…"
                value={formQuery}
                onChange={(e) => setFormQuery(e.target.value)}
              />
              <div className="flex flex-wrap gap-2">
                {forms.map((f) => (
                  <Button
                    key={f}
                    size="sm"
                    variant={formType === f ? "default" : "outline"}
                    onClick={() => setFormType(f)}
                  >
                    {f}
                  </Button>
                ))}
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  onClick={() =>
                    void apiClient
                      .previewDGCPForm(opportunityId, formType, companyKey)
                      .then(setFormPreview)
                      .catch((e) => setError(apiErrorMessage(e, "No se pudo previsualizar")))
                  }
                >
                  Completar / vista previa
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() =>
                    void apiClient
                      .generateDGCPForm(opportunityId, formType, companyKey)
                      .then(() => setMessage("Copia de trabajo generada."))
                      .catch((e) => setError(apiErrorMessage(e, "No se pudo generar")))
                  }
                >
                  Crear copia de trabajo
                </Button>
              </div>
              {formPreview ? (
                <div className="space-y-1 rounded border p-3 text-sm">
                  <p className="font-medium">{formPreview.form_type}</p>
                  <p className="text-xs text-muted-foreground">
                    Confianza {(formPreview.overall_confidence * 100).toFixed(0)}% · faltantes:{" "}
                    {formPreview.missing?.length || 0}
                  </p>
                </div>
              ) : null}
            </CardContent>
          </Card>
        )}
      </section>

      {linkItemId ? (
        <LinkExistingDocumentModal
          opportunityId={opportunityId}
          processDocs={processItems}
          busy={Boolean(busy?.startsWith("link-"))}
          onClose={() => setLinkItemId(null)}
          onPick={(payload) => void handleLinkExisting(payload)}
        />
      ) : null}

      {previewItem ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="max-h-[90vh] w-full max-w-5xl space-y-3 overflow-auto rounded-lg bg-background p-4 shadow-lg">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">
                Vista previa — {previewItem.document_title || previewItem.requirement}
              </p>
              <Button size="sm" variant="ghost" onClick={() => setPreviewItem(null)}>
                Cerrar
              </Button>
            </div>
            <AuthenticatedFileViewer
              filePath={linkedFilePath(opportunityId, previewItem)}
              filenameHint={previewItem.document_title || "documento"}
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}
