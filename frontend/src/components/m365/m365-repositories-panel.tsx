"use client";

import { useCallback, useEffect, useState } from "react";
import { Database, File, FolderOpen, RefreshCw, Search } from "lucide-react";

import { DocumentViewLink } from "@/components/documents/document-view-button";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api";
import { REPOSITORY_CATEGORIES, type M365RepositoryFile } from "@/lib/m365-intelligence";
import { formatBytes } from "@/lib/m365-workspace";
import { cn } from "@/lib/utils";

export function M365RepositoriesPanel({ accountId, connected }: { accountId?: string | null; connected: boolean }) {
  const [files, setFiles] = useState<M365RepositoryFile[]>([]);
  const [categories, setCategories] = useState<Record<string, number>>({});
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!connected) return;
    setLoading(true);
    const res = await apiClient.getM365RepositoryFiles({
      category: activeCategory ?? undefined,
      search: search.trim() || undefined,
      account_id: accountId ?? undefined,
    });
    setFiles(res.items);
    setCategories(res.categories);
    setLoading(false);
  }, [connected, activeCategory, search, accountId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSync(source: "all" | "onedrive" | "sharepoint" = "all") {
    setSyncing(true);
    setMessage(null);
    const res = await apiClient.syncM365Repository(accountId ?? undefined, source);
    setMessage(res.message);
    setSyncing(false);
    await load();
  }

  if (!connected) {
    return (
      <div className="flex flex-1 items-center justify-center p-8 text-muted-foreground">
        Conecte Microsoft 365 para indexar repositorios.
      </div>
    );
  }

  return (
    <div className="flex flex-1 min-h-0">
      <aside className="w-56 shrink-0 border-r p-3 overflow-y-auto">
        <Button className="mb-2 w-full" size="sm" onClick={() => void handleSync("all")} disabled={syncing}>
          <RefreshCw className={cn("mr-2 h-4 w-4", syncing && "animate-spin")} />
          {syncing ? "Indexando…" : "Sincronizar todo"}
        </Button>
        <div className="mb-3 flex gap-1">
          <Button className="flex-1" size="sm" variant="outline" onClick={() => void handleSync("onedrive")} disabled={syncing}>
            OneDrive
          </Button>
          <Button className="flex-1" size="sm" variant="outline" onClick={() => void handleSync("sharepoint")} disabled={syncing}>
            SharePoint
          </Button>
        </div>
        <TemplatesSection accountId={accountId} />
        <button
          type="button"
          className={cn(
            "mb-1 w-full rounded-lg px-3 py-2 text-left text-sm",
            !activeCategory && "bg-primary/10 font-medium text-primary",
          )}
          onClick={() => setActiveCategory(null)}
        >
          Todos ({Object.values(categories).reduce((a, b) => a + b, 0)})
        </button>
        {REPOSITORY_CATEGORIES.map((cat) => {
          const count = categories[cat.id] ?? 0;
          if (count === 0 && cat.id !== "general") return null;
          return (
            <button
              key={cat.id}
              type="button"
              className={cn(
                "mb-1 w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-muted",
                activeCategory === cat.id && "bg-primary/10 font-medium text-primary",
              )}
              onClick={() => setActiveCategory(cat.id)}
            >
              {cat.label}
              {count > 0 && <span className="ml-1 text-xs text-muted-foreground">({count})</span>}
            </button>
          );
        })}
      </aside>
      <div className="flex flex-1 flex-col p-4 min-h-0">
        {message && <p className="mb-2 text-sm text-primary">{message}</p>}
        <div className="mb-3 flex gap-2">
          <Input
            placeholder="Buscar documentos…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && void load()}
            className="max-w-md"
          />
          <Button variant="secondary" size="icon" onClick={() => void load()}>
            <Search className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto divide-y rounded-xl border">
          {loading && <p className="p-4 text-sm text-muted-foreground">Cargando repositorio…</p>}
          {!loading && files.length === 0 && (
            <div className="flex flex-col items-center gap-2 py-16 text-center text-muted-foreground">
              <Database className="h-10 w-10 opacity-40" />
              <p>Sin documentos indexados</p>
              <p className="text-xs">Pulse Sincronizar para clasificar archivos de OneDrive</p>
            </div>
          )}
          {files.map((f) => {
            const catStyle = REPOSITORY_CATEGORIES.find((c) => c.id === f.document_category);
            return (
              <div key={f.id} className="flex items-center gap-3 px-4 py-3 hover:bg-muted/30">
                {f.is_folder ? (
                  <FolderOpen className="h-5 w-5 text-amber-500" />
                ) : (
                  <File className="h-5 w-5 text-primary" />
                )}
                <div className="flex-1 min-w-0">
                  <p className="truncate font-medium">{f.name}</p>
                  <p className="truncate text-xs text-muted-foreground">
                    {f.parent_path || "OneDrive"} · {formatBytes(f.size_bytes)}
                  </p>
                </div>
                <span className={cn("shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium", catStyle?.color)}>
                  {f.document_category_label}
                </span>
                {!f.is_folder && (
                  <DocumentViewLink
                    m365FileId={f.id}
                    graphItemId={f.graph_item_id}
                    webUrl={f.web_url ?? f.download_url}
                    label="Ver documento"
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function TemplatesSection({ accountId: _accountId }: { accountId?: string | null }) {
  const [templates, setTemplates] = useState<Array<{ id: string; name: string }>>([]);
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    apiClient.getM365Templates().then((r) => setTemplates(r.items.slice(0, 6)));
  }, []);

  async function handleGenerate(templateType: string) {
    setLoading(true);
    const res = await apiClient.generateM365Template(templateType);
    if (res.ok && res.content_base64) {
      const blob = new Blob([Uint8Array.from(atob(res.content_base64), (c) => c.charCodeAt(0))], {
        type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = res.filename;
      a.click();
      URL.revokeObjectURL(url);
      setPreview(res.message);
    }
    setLoading(false);
  }

  return (
    <div className="mt-4 rounded-xl border p-3">
      <p className="mb-2 text-xs font-semibold uppercase text-muted-foreground">Plantillas</p>
      {templates.map((t) => (
        <button
          key={t.id}
          type="button"
          className="mb-1 block w-full rounded-lg px-2 py-1.5 text-left text-xs hover:bg-muted"
          onClick={() => void handleGenerate(t.id)}
          disabled={loading}
        >
          {t.name}
        </button>
      ))}
      {preview && <p className="mt-2 text-[10px] text-primary">{preview}</p>}
    </div>
  );
}
