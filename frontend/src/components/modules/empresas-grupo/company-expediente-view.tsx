"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  ClipboardCopy,
  Download,
  FileText,
  Mail,
  RefreshCw,
} from "lucide-react";

import { CompanyProfileForm } from "@/components/documents/company-profile-form";
import { CompanyRepresentativesPanel } from "@/components/documents/company-representatives-panel";
import { DocumentViewButton } from "@/components/documents/document-view-button";
import { VigencyBadge } from "@/components/documents/vigency-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";
import type { CompanyCompletion, CompanyDocumentProfile, MissingItems, ProfileFormResult } from "@/lib/documents-hub";
import { progressBarClass, progressBadgeVariant } from "@/lib/documents-hub";
import type { LegalDocumentsDashboard } from "@/lib/licitador";
import { cn } from "@/lib/utils";

const TABS = [
  "perfil",
  "representantes",
  "legales",
  "identidad",
  "firmas",
  "plantillas",
  "licitaciones",
  "historial",
  "faltantes",
] as const;

type Tab = (typeof TABS)[number];

const TAB_LABELS: Record<Tab, string> = {
  perfil: "Información general",
  representantes: "Representantes y firmantes",
  legales: "Documentos legales",
  identidad: "Identidad corporativa",
  firmas: "Firmas y sellos",
  plantillas: "Plantillas",
  licitaciones: "Licitaciones",
  historial: "Historial",
  faltantes: "Requeridos / faltantes",
};

export function CompanyExpedienteView({
  companyId,
  backHref = "/apps/empresas-grupo/empresas",
  backLabel = "← Empresas del grupo",
}: {
  companyId: string;
  backHref?: string;
  backLabel?: string;
}) {
  const [tab, setTab] = useState<Tab>("perfil");
  const [profile, setProfile] = useState<CompanyDocumentProfile | null>(null);
  const [missing, setMissing] = useState<MissingItems | null>(null);
  const [legal, setLegal] = useState<LegalDocumentsDashboard | null>(null);
  const [identity, setIdentity] = useState<Record<string, unknown> | null>(null);
  const [emailDraft, setEmailDraft] = useState<{ subject: string; body: string } | null>(null);
  const [profileForm, setProfileForm] = useState<ProfileFormResult | null>(null);
  const [completion, setCompletion] = useState<CompanyCompletion | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [p, m, l, c] = await Promise.all([
        apiClient.getDocumentsHubCompany(companyId),
        apiClient.getDocumentsHubMissing(companyId),
        apiClient.getDocumentsHubLegal(),
        apiClient.getDocumentsHubCompletion(companyId).catch(() => null),
      ]);
      setProfile(p);
      setMissing(m);
      setLegal(l);
      setCompletion(c);
      if (p.company_key) {
        apiClient.getDocumentsHubCorporateIdentity(p.company_key).then(setIdentity).catch(() => setIdentity(null));
      }
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 404) {
          setError("Empresa no encontrada. Verifique el enlace o vuelva al listado.");
        } else if (err.status === 403) {
          setError("No tiene permiso para ver el perfil de esta empresa.");
        } else if (err.status >= 500) {
          setError("Error del servidor al cargar el perfil. Intente de nuevo.");
        } else {
          setError(err.message || "No se pudo cargar el perfil de la empresa.");
        }
      } else {
        setError("No se pudo cargar el perfil de la empresa.");
      }
      setProfile(null);
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => {
    load();
  }, [load]);

  const requestDocs = async () => {
    const result = await apiClient.requestDocumentsHubMissing(companyId, {
      create_task: true,
      send_email: true,
    });
    setEmailDraft({ subject: result.subject, body: result.body });
    setTab("faltantes");
  };

  const generateForm = async () => {
    const result = await apiClient.generateDocumentsProfileForm(companyId);
    setProfileForm(result);
    setTab("faltantes");
  };

  const companyLegal = legal?.companies?.find((c) => c.company_key === profile?.company_key);

  if (loading && !profile) {
    return <p className="p-4 text-sm text-muted-foreground">Cargando expediente…</p>;
  }

  if (error && !profile) {
    return (
      <div className="space-y-4 p-1">
        <Link href={backHref} className="text-sm text-primary hover:underline">
          {backLabel}
        </Link>
        <Card className="border-amber-500/40 bg-amber-500/5">
          <CardContent className="flex flex-wrap items-center gap-3 py-4 text-sm text-amber-800">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span className="flex-1">{error}</span>
            <Button size="sm" variant="outline" onClick={() => void load()}>
              <RefreshCw className="mr-1 h-4 w-4" />
              Reintentar
            </Button>
            <Button size="sm" variant="ghost" asChild>
              <Link href={backHref}>Volver al módulo</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-1">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Link href={backHref} className="text-sm text-primary hover:underline">
          {backLabel}
        </Link>
        <p className="text-xs text-muted-foreground">Expediente · empresa interna del grupo</p>
      </div>

      {error && (
        <Card className="border-amber-500/40 bg-amber-500/5">
          <CardContent className="flex items-center gap-2 py-3 text-sm text-amber-800">
            <AlertTriangle className="h-4 w-4" />
            {error}
            <Button size="sm" variant="outline" className="ml-auto" onClick={() => void load()}>
              Reintentar
            </Button>
          </CardContent>
        </Card>
      )}

      {profile && (
        <Card>
          <CardContent className="flex flex-wrap items-center gap-4 py-4">
            <div className="flex-1 min-w-[200px]">
              <div className="mb-1 flex flex-wrap items-center gap-2">
                <h1 className="text-lg font-semibold">{profile.razon_social}</h1>
                <Badge variant={progressBadgeVariant(completion?.progress_semaphore, completion?.completeness_score ?? profile.completeness_score)}>
                  {(completion?.completeness_score ?? profile.completeness_score)}% completo
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                RNC {profile.rnc || "—"} · {profile.nombre_comercial || profile.company_key}
              </p>
              {completion?.progress_note && (
                <p className="text-xs text-amber-700">{completion.progress_note}</p>
              )}
              <div className="mt-2 h-2 max-w-md overflow-hidden rounded-full bg-muted">
                <div
                  className={cn(
                    "h-full rounded-full",
                    progressBarClass(completion?.progress_semaphore, completion?.completeness_score ?? profile.completeness_score),
                  )}
                  style={{ width: `${completion?.completeness_score ?? profile.completeness_score}%` }}
                />
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="outline" onClick={requestDocs}>
                <Mail className="mr-1 h-4 w-4" />
                Solicitar pendientes
              </Button>
              <Button size="sm" variant="outline" onClick={generateForm}>
                <FileText className="mr-1 h-4 w-4" />
                Formulario externo
              </Button>
              <Button size="sm" variant="outline" onClick={load} disabled={loading}>
                <RefreshCw className={cn("mr-1 h-4 w-4", loading && "animate-spin")} />
                Actualizar
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="flex flex-wrap gap-1 border-b border-border/60 pb-2">
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={cn(
              "rounded-lg px-3 py-1.5 text-sm font-medium",
              tab === t ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted",
            )}
          >
            {TAB_LABELS[t]}
          </button>
        ))}
      </div>

      {tab === "perfil" && profile && (
        <CompanyProfileForm
          companyId={companyId}
          onSaved={load}
          onGenerateForm={generateForm}
          onRequestAll={requestDocs}
          onAddRepresentative={() => setTab("representantes")}
        />
      )}

      {tab === "representantes" && (
        <CompanyRepresentativesPanel companyId={companyId} onChanged={load} />
      )}

      {tab === "legales" && companyLegal && (
        <div className="space-y-3">
          {companyLegal.documents.map((d) => (
            <Card key={d.id}>
              <CardContent className="flex items-center justify-between gap-3 py-3">
                <span className="text-sm font-medium">{d.name}</span>
                <div className="flex items-center gap-2">
                  <VigencyBadge status={d.vigency_status} required />
                  {d.valid_until && (
                    <span className="text-xs text-muted-foreground">hasta {d.valid_until}</span>
                  )}
                  {d.web_url || d.source === "knowledge" ? (
                    <DocumentViewButton
                      knowledgeAssetId={d.source === "knowledge" ? d.id : undefined}
                      m365FileId={d.source === "onedrive" ? d.id : undefined}
                      webUrl={d.web_url}
                      label="Ver documento"
                    />
                  ) : null}
                </div>
              </CardContent>
            </Card>
          ))}
          {companyLegal.missing_documents.map((d) => (
            <Card key={d} className="border-red-300/50">
              <CardContent className="flex items-center justify-between py-3 text-sm">
                <span>{d.replace(/_/g, " ")}</span>
                <VigencyBadge missing label="Pendiente obligatorio" />
              </CardContent>
            </Card>
          ))}
          {companyLegal.expired_documents?.map((d) => (
            <Card key={`exp-${d}`} className="border-red-400/50 bg-red-50/30 dark:bg-red-950/10">
              <CardContent className="flex items-center justify-between py-3 text-sm">
                <span>{d.replace(/_/g, " ")}</span>
                <VigencyBadge status="vencido" />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {tab === "identidad" && (
        <Card>
          <CardContent className="space-y-2 py-4 text-sm">
            {identity ? (
              <>
                <p>Firmas: {((identity.signatures as unknown[]) || []).length}</p>
                <p>Sellos: {((identity.stamps as unknown[]) || []).length}</p>
                {((identity.missing as string[]) || []).map((m) => (
                  <p key={m} className="text-red-700">• Falta: {m}</p>
                ))}
              </>
            ) : (
              <p className="text-muted-foreground">Sin datos de identidad corporativa.</p>
            )}
            <Button size="sm" variant="outline" asChild className="mt-2">
              <Link href="/documentos/identidad">Gestionar identidad</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {tab === "firmas" && (
        <Card>
          <CardContent className="py-6 text-sm text-muted-foreground">
            Suba firma y sello desde la pestaña <strong>Información general</strong> o desde Identidad corporativa.
          </CardContent>
        </Card>
      )}

      {tab === "faltantes" && missing && (
        <div className="space-y-4">
          <CompanyRepresentativesPanel
            companyId={companyId}
            title="Documentos por representante — administración"
            onChanged={load}
          />
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Documentos requeridos</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {missing.missing_fields.map((f) => (
                <div key={f} className="flex items-center justify-between gap-2">
                  <span>Dato: {f.replace(/_/g, " ")}</span>
                  <VigencyBadge missing label="Pendiente" />
                </div>
              ))}
              {missing.missing_documents.map((d) => (
                <div key={d} className="flex items-center justify-between gap-2">
                  <span>{d.replace(/_/g, " ")}</span>
                  <VigencyBadge missing label="Pendiente obligatorio" />
                </div>
              ))}
              {missing.expired_documents.map((d) => (
                <div key={d} className="flex items-center justify-between gap-2">
                  <span>{d.replace(/_/g, " ")}</span>
                  <VigencyBadge status="vencido" />
                </div>
              ))}
              {missing.identity_missing.map((d) => (
                <div key={d} className="flex items-center justify-between gap-2">
                  <span>Identidad: {d}</span>
                  <VigencyBadge missing />
                </div>
              ))}
            </CardContent>
          </Card>
          {emailDraft && (
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-base">Borrador de correo</CardTitle>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => void navigator.clipboard.writeText(`Asunto: ${emailDraft.subject}\n\n${emailDraft.body}`)}
                >
                  <ClipboardCopy className="mr-1 h-4 w-4" />
                  Copiar
                </Button>
              </CardHeader>
              <CardContent>
                <p className="text-sm font-medium">{emailDraft.subject}</p>
                <pre className="mt-2 whitespace-pre-wrap text-xs text-muted-foreground">{emailDraft.body}</pre>
              </CardContent>
            </Card>
          )}
          {profileForm && (
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-base">Formulario externo</CardTitle>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => void navigator.clipboard.writeText(profileForm.form_url)}>
                    Copiar enlace
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      const blob = new Blob([profileForm.html], { type: "text/html" });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement("a");
                      a.href = url;
                      a.download = `perfil_${profile?.company_key || "empresa"}.html`;
                      a.click();
                      URL.revokeObjectURL(url);
                    }}
                  >
                    <Download className="mr-1 h-4 w-4" />
                    Descargar
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground">
                Válido hasta: {new Date(profileForm.expires_at).toLocaleString()}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {tab === "plantillas" && (
        <Card>
          <CardContent className="py-6 text-center">
            <Button size="sm" variant="outline" asChild>
              <Link href="/apps/documentos/plantillas">Plantillas documentales</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {tab === "licitaciones" && (
        <Card>
          <CardContent className="py-6 text-center">
            <Button size="sm" variant="outline" asChild>
              <Link href="/apps/licitaciones/expedientes">Expedientes DGCP del grupo</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {tab === "historial" && (
        <Card>
          <CardContent className="py-6 text-sm text-muted-foreground">
            Historial de sincronizaciones OneDrive y solicitudes de documentos.
          </CardContent>
        </Card>
      )}
    </div>
  );
}
