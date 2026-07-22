"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  Building2,
  CheckCircle2,
  ClipboardCopy,
  FileWarning,
  Mail,
  RefreshCw,
  Shield,
} from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { DocumentViewButton } from "@/components/documents/document-view-button";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import type { CompanyLegalSummary, LegalDocumentItem, LegalDocumentsDashboard } from "@/lib/licitador";
import { VIGENCY_STYLES } from "@/lib/licitador";

export default function DocumentosLegalesPage() {
  const [data, setData] = useState<LegalDocumentsDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<string>("justech");
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
      const draft = await apiClient.requestLegalUpdateEmail(key);
      setEmailDraft(draft);
    } finally {
      setEmailLoading(false);
    }
  };

  const copyEmail = () => {
    if (!emailDraft) return;
    void navigator.clipboard.writeText(`Asunto: ${emailDraft.subject}\n\n${emailDraft.body}`);
  };

  return (
    <AppShell title="Documentos legales" description="Checklist legal por empresa — OneDrive 01_DOCUMENTOS_LEGALES">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
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
                  <FileWarning className="h-4 w-4" />
                  Falta: {m.replace(/_/g, " ")}
                </div>
              ))}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Acciones</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button className="w-full" size="sm" onClick={() => requestEmail(company.company_key)} disabled={emailLoading}>
                <Mail className="mr-2 h-4 w-4" />
                Solicitar actualización
              </Button>
              {emailDraft && (
                <>
                  <Button className="w-full" size="sm" variant="outline" onClick={copyEmail}>
                    <ClipboardCopy className="mr-2 h-4 w-4" />
                    Copiar correo
                  </Button>
                  <pre className="max-h-48 overflow-auto rounded-lg bg-muted p-2 text-xs">{emailDraft.body}</pre>
                </>
              )}
              <Button className="w-full" size="sm" variant="ghost" asChild>
                <Link href="/documentos/empresas">Ver perfiles empresa</Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      )}

      {!company && !loading && (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            Sin datos legales. Sincronice <code>01_DOCUMENTOS_LEGALES</code>.
          </CardContent>
        </Card>
      )}
    </AppShell>
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
