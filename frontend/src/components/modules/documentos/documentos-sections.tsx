"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ClipboardCopy, FileSpreadsheet, FileText, Mail, RefreshCw, Send, Shield } from "lucide-react";

import { DocumentsHubM365Panel } from "@/components/documents/documents-hub-m365-panel";
import { DocumentViewButton } from "@/components/documents/document-view-button";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api";
import {
  TEMPLATE_TYPE_LABELS,
  VIGENCY_STYLES,
  type DgcpTemplateItem,
  type DgcpTemplatesDashboard,
  type LegalDocumentItem,
  type LegalDocumentsDashboard,
} from "@/lib/licitador";

export function DocumentosEmpresasSection() {
  const [companies, setCompanies] = useState<Awaited<ReturnType<typeof apiClient.getDocumentsHubDashboard>>["company_cards"]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    apiClient
      .getDocumentsHubDashboard()
      .then((d) => setCompanies(d.company_cards || []))
      .finally(() => setLoading(false));
  }, []);

  const filtered = companies.filter((c) => {
    const q = search.toLowerCase();
    return !q || c.razon_social.toLowerCase().includes(q) || (c.rnc || "").includes(q);
  });

  if (loading) return <p className="text-sm text-muted-foreground">Cargando empresas…</p>;

  return (
    <div className="space-y-4">
      <Input placeholder="Buscar empresa, RNC…" value={search} onChange={(e) => setSearch(e.target.value)} className="max-w-md" />
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {filtered.map((c) => (
          <Link key={c.id} href={c.href || `/apps/empresas-grupo/perfil/${c.id}`} className="rounded-xl border bg-card p-4 transition hover:border-primary/30">
            <p className="font-medium">{c.razon_social}</p>
            <p className="text-xs text-muted-foreground">RNC {c.rnc || "—"} · {c.completeness_score}% completo</p>
          </Link>
        ))}
      </div>
    </div>
  );
}

export function DocumentosPlantillasSection() {
  const [data, setData] = useState<DgcpTemplatesDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    apiClient
      .getDocumentsHubTemplates()
      .then(setData)
      .catch(() => apiClient.getLicitadorTemplatesDashboard().then(setData))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(() => {
    if (!data) return [];
    const q = search.toLowerCase();
    return data.templates.filter((t) => !q || t.name.toLowerCase().includes(q));
  }, [data, search]);

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Input placeholder="Buscar plantilla…" value={search} onChange={(e) => setSearch(e.target.value)} className="max-w-sm" />
        <Button variant="outline" size="sm" onClick={load}><RefreshCw className="h-4 w-4" /></Button>
      </div>
      {loading ? (
        <p className="text-sm text-muted-foreground">Cargando…</p>
      ) : (
        <div className="grid gap-2 md:grid-cols-2">
          {filtered.map((t) => (
            <TemplateRow key={t.id || t.name} template={t} />
          ))}
        </div>
      )}
    </div>
  );
}

function TemplateRow({ template }: { template: DgcpTemplateItem }) {
  const Icon = template.mime_type?.includes("sheet") ? FileSpreadsheet : FileText;
  return (
    <div className="flex items-center gap-3 rounded-lg border p-3 text-sm">
      <Icon className="h-5 w-5 text-muted-foreground" />
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium">{template.name}</p>
        <p className="text-xs text-muted-foreground">{TEMPLATE_TYPE_LABELS[template.template_type || ""] || template.template_type}</p>
      </div>
      <DocumentViewButton m365FileId={template.id} webUrl={template.web_url} label="Ver documento" />
    </div>
  );
}

export function DocumentosPendientesSection() {
  const [items, setItems] = useState<Awaited<ReturnType<typeof apiClient.getDocumentsHubPending>>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.getDocumentsHubPending().then(setItems).finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-muted-foreground">Cargando pendientes…</p>;

  return (
    <ul className="divide-y rounded-xl border">
      {items.map((i) => (
        <li key={i.id} className="px-4 py-3 text-sm">
          <p className="font-medium">{i.item_label}</p>
          <p className="text-xs text-muted-foreground">{i.company_label} · {i.status}</p>
        </li>
      ))}
      {!items.length && <li className="px-4 py-8 text-center text-muted-foreground">Sin pendientes</li>}
    </ul>
  );
}

export function DocumentosRepositoriosSection() {
  const [repos, setRepos] = useState<Awaited<ReturnType<typeof apiClient.getDocumentsHubRepositories>>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.getDocumentsHubRepositories().then(setRepos).finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-muted-foreground">Cargando repositorios…</p>;

  return (
    <div className="space-y-4">
      <DocumentsHubM365Panel compact />
      <div className="grid gap-3 md:grid-cols-2">
      {repos.map((r) => (
        <Card key={r.id || r.folder_key}>
          <CardHeader className="pb-2"><CardTitle className="text-sm">{r.label}</CardTitle></CardHeader>
          <CardContent className="text-xs text-muted-foreground">
            {r.indexed_files} archivos · {r.status}
            {r.last_sync_at && ` · ${new Date(r.last_sync_at).toLocaleDateString("es-DO")}`}
          </CardContent>
        </Card>
      ))}
      </div>
    </div>
  );
}

export function DocumentosLegalesSection() {
  const [data, setData] = useState<LegalDocumentsDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState("justech");
  const [emailDraft, setEmailDraft] = useState<{ subject: string; body: string } | null>(null);
  const [emailLoading, setEmailLoading] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    apiClient
      .getDocumentsHubLegal()
      .then(setData)
      .catch(() => apiClient.getLicitadorLegalDashboard().then(setData).catch(() => setData(null)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const company = data?.companies.find((c) => c.company_key === selected);

  const requestEmail = async (key: string) => {
    setEmailLoading(true);
    try {
      setEmailDraft(await apiClient.requestLegalUpdateEmail(key));
    } finally {
      setEmailLoading(false);
    }
  };

  if (loading) return <p className="text-sm text-muted-foreground">Cargando documentos legales…</p>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-2">
          {data?.companies.map((c) => (
            <Button
              key={c.company_key}
              size="sm"
              variant={selected === c.company_key ? "default" : "outline"}
              onClick={() => setSelected(c.company_key)}
            >
              {c.company_label}
            </Button>
          ))}
        </div>
        <Button size="sm" variant="outline" onClick={load} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Actualizar
        </Button>
      </div>
      {company && (
        <div className="grid gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Shield className="h-4 w-4" />
                {company.company_label}
              </CardTitle>
              <CardDescription>
                {company.documents.length} documentos · {company.missing_documents.length} faltantes
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {company.documents.map((d) => (
                <div key={d.id} className="flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm">
                  <span>{d.name}</span>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className={VIGENCY_STYLES[d.vigency_status] || ""}>
                      {d.vigency_status}
                    </Badge>
                    <LegalDocumentViewButton doc={d} />
                  </div>
                </div>
              ))}
              {company.missing_documents.map((m) => (
                <div key={m} className="flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-sm text-amber-800">
                  Falta: {m.replace(/_/g, " ")}
                </div>
              ))}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle className="text-base">Acciones</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              <Button
                className="w-full"
                size="sm"
                disabled={emailLoading}
                onClick={() => void requestEmail(company.company_key)}
              >
                <Mail className="mr-2 h-4 w-4" />
                Solicitar actualización
              </Button>
              {emailDraft && (
                <div className="rounded-lg border bg-muted/30 p-3 text-xs">
                  <p className="font-medium">{emailDraft.subject}</p>
                  <p className="mt-2 whitespace-pre-wrap text-muted-foreground">{emailDraft.body}</p>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="mt-2"
                    onClick={() => void navigator.clipboard.writeText(`Asunto: ${emailDraft.subject}\n\n${emailDraft.body}`)}
                  >
                    <ClipboardCopy className="mr-1 h-3.5 w-3.5" />
                    Copiar
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

function LegalDocumentViewButton({ doc }: { doc: LegalDocumentItem }) {
  return (
    <DocumentViewButton
      knowledgeAssetId={doc.source === "knowledge" ? doc.id : undefined}
      m365FileId={doc.source === "onedrive" ? doc.id : undefined}
      webUrl={doc.web_url}
      label="Ver documento"
    />
  );
}

export function DocumentosSalidasSection() {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
        <Send className="h-10 w-10 text-muted-foreground/50" />
        <p className="max-w-md text-sm text-muted-foreground">
          Los expedientes y documentos de salida se almacenan en{" "}
          <code className="text-xs">Justech-AI/SALIDAS</code>. Configure la carpeta en Repositorios y sincronice.
        </p>
        <Button size="sm" variant="outline" asChild>
          <Link href="/apps/documentos/repositorio">Configurar repositorio SALIDAS</Link>
        </Button>
      </CardContent>
    </Card>
  );
}
