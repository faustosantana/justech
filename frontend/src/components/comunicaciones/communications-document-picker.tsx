"use client";

import { Cloud, File, FolderOpen, Paperclip, Search, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { M365DocumentPicker } from "@/components/m365/m365-document-picker";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api";
import type { CommunicationsRepositoryItem } from "@/lib/communications";
import type { M365DocumentItem } from "@/lib/m365-documents";
import { cn } from "@/lib/utils";

function formatSize(bytes?: number | null) {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const SOURCE_TABS: { id: string; label: string }[] = [
  { id: "", label: "Todos" },
  { id: "m365_repository", label: "M365 indexado" },
  { id: "jaios_document", label: "JAIOS" },
];

function m365PayloadFor(item: M365DocumentItem) {
  return {
    item_id: item.item_id || item.id,
    drive_id: item.drive_id ?? undefined,
    source_type: item.source_type,
    site_id: item.site_id ?? undefined,
    name: item.name,
    web_url: item.web_url ?? undefined,
    path: item.path,
  };
}

export function CommunicationsDocumentPicker({
  open,
  onClose,
  onAttach,
  onAttachM365,
  attaching,
}: {
  open: boolean;
  onClose: () => void;
  onAttach: (item: CommunicationsRepositoryItem, caption: string) => void | Promise<void>;
  onAttachM365?: (item: M365DocumentItem, caption: string) => void | Promise<void>;
  attaching?: boolean;
}) {
  const [items, setItems] = useState<CommunicationsRepositoryItem[]>([]);
  const [categories, setCategories] = useState<Record<string, number>>({});
  const [search, setSearch] = useState("");
  const [source, setSource] = useState("");
  const [category, setCategory] = useState("");
  const [loading, setLoading] = useState(false);
  const [caption, setCaption] = useState("");
  const [selected, setSelected] = useState<CommunicationsRepositoryItem | null>(null);
  const [m365Open, setM365Open] = useState(false);

  const categoryOptions = useMemo(() => {
    return Object.entries(categories)
      .sort((a, b) => b[1] - a[1])
      .map(([key, count]) => ({ key, count }));
  }, [categories]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.listCommunicationsRepository({
        q: search,
        category: category || undefined,
        source: source || undefined,
        limit: 80,
      });
      setItems(res.items);
      setCategories(res.categories);
    } finally {
      setLoading(false);
    }
  }, [search, category, source]);

  useEffect(() => {
    if (open) void load();
  }, [open, load]);

  useEffect(() => {
    if (!open) {
      setM365Open(false);
      setSelected(null);
      setCaption("");
    }
  }, [open]);

  if (!open) return null;

  return (
    <>
      <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 p-4">
        <div className="flex max-h-[85vh] w-full max-w-xl flex-col rounded-2xl border bg-background shadow-2xl">
          <div className="flex items-center justify-between border-b px-4 py-3">
            <div className="flex items-center gap-2">
              <FolderOpen className="h-5 w-5 text-primary" />
              <p className="font-semibold">Adjuntar documento</p>
            </div>
            <button type="button" onClick={onClose} className="rounded-lg p-1 hover:bg-muted">
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="space-y-3 border-b px-4 py-3">
            <Button
              type="button"
              variant="outline"
              className="w-full justify-start gap-2"
              onClick={() => setM365Open(true)}
            >
              <Cloud className="h-4 w-4 text-sky-600" />
              Buscar en Microsoft 365
            </Button>
            <p className="text-xs text-muted-foreground">
              O elija un documento del repositorio indexado en JAIOS (sync M365 + documentos locales).
            </p>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                className="pl-9"
                placeholder="Buscar en repositorio…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void load()}
              />
            </div>
            <div className="flex flex-wrap gap-1.5">
              {SOURCE_TABS.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setSource(tab.id)}
                  className={cn(
                    "rounded-full px-3 py-1 text-xs font-medium transition-colors",
                    source === tab.id ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:bg-muted/80",
                  )}
                >
                  {tab.label}
                </button>
              ))}
            </div>
            {categoryOptions.length > 0 && (
              <select
                className="w-full rounded-lg border bg-background px-3 py-2 text-sm"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                <option value="">Todas las categorías</option>
                {categoryOptions.map((c) => (
                  <option key={c.key} value={c.key}>
                    {c.key} ({c.count})
                  </option>
                ))}
              </select>
            )}
          </div>

          <div className="flex-1 overflow-y-auto divide-y">
            {loading && <p className="p-4 text-sm text-muted-foreground">Cargando repositorio…</p>}
            {!loading && items.length === 0 && (
              <p className="p-6 text-center text-sm text-muted-foreground">
                No hay documentos indexados. Use Microsoft 365 en vivo o sincronice el repositorio.
              </p>
            )}
            {!loading &&
              items.map((item) => (
                <button
                  key={`${item.source}-${item.id}`}
                  type="button"
                  className={cn(
                    "flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-muted/40",
                    selected?.id === item.id && selected?.source === item.source && "bg-primary/5",
                  )}
                  onClick={() => setSelected(item)}
                >
                  <File className="h-5 w-5 shrink-0 text-sky-600" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{item.name}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {item.source_label} · {item.category_label}
                      {item.size_bytes ? ` · ${formatSize(item.size_bytes)}` : ""}
                    </p>
                  </div>
                </button>
              ))}
          </div>

          {selected && (
            <div className="space-y-2 border-t bg-muted/20 px-4 py-3">
              <p className="text-xs font-medium text-muted-foreground">
                Seleccionado: <span className="text-foreground">{selected.name}</span>
              </p>
              <Input
                placeholder="Mensaje opcional (caption)…"
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
              />
              <div className="flex gap-2">
                <Button
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700"
                  disabled={attaching}
                  onClick={() => void onAttach(selected, caption)}
                >
                  <Paperclip className="mr-2 h-4 w-4" />
                  {attaching ? "Enviando…" : "Enviar por WhatsApp"}
                </Button>
                <Button variant="ghost" onClick={() => setSelected(null)}>
                  Cancelar
                </Button>
              </div>
            </div>
          )}

          <div className="border-t px-4 py-3">
            <Button variant="ghost" onClick={onClose}>
              Cerrar
            </Button>
          </div>
        </div>
      </div>

      <M365DocumentPicker
        open={m365Open}
        onClose={() => setM365Open(false)}
        entityId=""
        title="Adjuntar desde Microsoft 365"
        mode="both"
        attachMode={{
          label: "Enviar por WhatsApp",
          attaching,
          onAttach: async (item) => {
            if (!onAttachM365) return;
            await onAttachM365(item, "");
          },
        }}
      />
    </>
  );
}

export { m365PayloadFor };
