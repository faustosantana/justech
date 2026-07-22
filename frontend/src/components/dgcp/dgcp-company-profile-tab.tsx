"use client";

import { ExternalLink, Loader2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { DocumentViewButton } from "@/components/documents/document-view-button";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import type { CompanyCompletion, CompanyDocumentProfile, CompanyFieldStatus } from "@/lib/documents-hub";
import { progressBadgeVariant } from "@/lib/documents-hub";
import { cn } from "@/lib/utils";

type Props = {
  companyKey?: string;
};

function fieldBadgeVariant(field: CompanyFieldStatus): "default" | "secondary" | "destructive" | "outline" {
  const u = field.unified_status || field.status;
  if (u === "validated" || u === "complete") return "default";
  if (u === "detected" || u === "pending_analysis" || u === "partial") return "secondary";
  if (u === "expired") return "destructive";
  return "outline";
}

export function DgcpCompanyProfileTab({ companyKey = "justech" }: Props) {
  const [profile, setProfile] = useState<CompanyDocumentProfile | null>(null);
  const [completion, setCompletion] = useState<CompanyCompletion | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const hub = await apiClient.getDocumentsHubDashboard();
        const card = hub.company_cards?.find((c) => c.company_key === companyKey);
        if (!card) {
          if (!cancelled) setError("Perfil empresarial no encontrado.");
          return;
        }
        const [prof, comp] = await Promise.all([
          apiClient.getDocumentsHubCompany(card.id),
          apiClient.getDocumentsHubCompletion(card.id),
        ]);
        if (!cancelled) {
          setProfile(prof);
          setCompletion(comp);
        }
      } catch {
        if (!cancelled) setError("No se pudo cargar el perfil empresarial.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [companyKey]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground py-8">
        <Loader2 className="h-4 w-4 animate-spin" />
        Cargando perfil empresarial…
      </div>
    );
  }

  if (error || !profile) {
    return (
      <p className="text-sm text-muted-foreground py-4">
        {error ?? "Sin datos de perfil."}{" "}
        <Link href="/documents" className="text-primary hover:underline">
          Ir a Documentos
        </Link>
      </p>
    );
  }

  const legalFields =
    completion?.fields.filter(
      (f) =>
        f.kind === "document" &&
        /dgii|tss|mercantil|estatuto|acta|poder|certif|rpe|proveedor/i.test(f.label),
    ) ?? [];

  const rpeValue =
    profile.proveedor_estado ||
    completion?.fields.find((f) => f.field_key === "proveedor_estado")?.text_value ||
    (profile.raw_json?.rpe as string) ||
    (profile.raw_json?.proveedor_estado as string);

  const cargoField = completion?.fields.find((f) => f.field_key === "cargo_representante");
  const cargoValue = profile.cargo_representante || cargoField?.text_value;
  const cargoMissing = cargoField?.badge === "Falta" || !cargoValue;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">
          Perfil empresarial — fuente única de verdad corporativa (mismo repositorio que checklist, Hermes y
          autollenado).
        </p>
        <Button size="sm" variant="outline" asChild>
          <Link href={`/documents/companies/${profile.id}`}>
            <ExternalLink className="h-3.5 w-3.5 mr-1" />
            Editar perfil
          </Link>
        </Button>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between gap-2">
            <CardTitle className="text-base">{profile.razon_social ?? profile.company_key}</CardTitle>
            {completion && (
              <Badge variant={progressBadgeVariant(completion.progress_semaphore, completion.completeness_score)}>
                {completion.completeness_score}% completo
              </Badge>
            )}
          </div>
          {profile.nombre_comercial && (
            <p className="text-sm text-muted-foreground">{profile.nombre_comercial}</p>
          )}
        </CardHeader>
        <CardContent className="grid sm:grid-cols-2 gap-3 text-sm">
          <Field label="RNC" value={profile.rnc} />
          <Field label="RPE" value={rpeValue} emphasizePending={rpeValue?.includes("número pendiente")} />
          <Field label="Dirección" value={profile.direccion} className="sm:col-span-2" />
          <Field label="Teléfono" value={profile.telefono} />
          <Field label="Correo" value={profile.correo} />
          <Field label="Representante legal" value={profile.representante_legal} />
          <Field
            label="Cargo"
            value={cargoValue}
            missingEditable={cargoMissing}
            editHref={`/documents/companies/${profile.id}`}
          />
        </CardContent>
      </Card>

      {legalFields.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Documentación legal</CardTitle>
            <p className="text-xs text-muted-foreground">
              Estados: detectado · validado · vencido · pendiente análisis
            </p>
          </CardHeader>
          <CardContent className="divide-y">
            {legalFields.map((f) => (
              <div key={f.field_key} className="py-2 flex flex-wrap items-center justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-sm">{f.label}</p>
                  {f.document_name && (
                    <p className="text-xs text-muted-foreground truncate">{f.document_name}</p>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Badge variant={fieldBadgeVariant(f)} className={cn(f.unified_status === "detected" && "bg-amber-500/15 text-amber-800 dark:text-amber-200")}>
                    {f.badge || f.status}
                  </Badge>
                  {(f.knowledge_asset_id || f.document_id || f.view_url || f.onedrive_url) && (
                    <DocumentViewButton
                      knowledgeAssetId={f.knowledge_asset_id ?? undefined}
                      documentId={f.document_id ?? undefined}
                      viewUrl={f.view_url}
                      webUrl={f.onedrive_url}
                      label="Ver documento"
                      variant="outline"
                      size="sm"
                    />
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {completion && completion.representatives_count != null && completion.representatives_count > 0 && (
        <p className="text-xs text-muted-foreground">
          {completion.representatives_count} representante(s) registrado(s) con firmas y documentos asociados.
        </p>
      )}
    </div>
  );
}

function Field({
  label,
  value,
  className,
  missingEditable,
  editHref,
  emphasizePending,
}: {
  label: string;
  value?: string | null;
  className?: string;
  missingEditable?: boolean;
  editHref?: string;
  emphasizePending?: boolean;
}) {
  return (
    <div className={className}>
      <p className="text-xs uppercase text-muted-foreground">{label}</p>
      {value ? (
        <p className={cn(emphasizePending && "text-amber-800 dark:text-amber-200")}>{value}</p>
      ) : missingEditable && editHref ? (
        <p className="text-muted-foreground italic">
          Falta —{" "}
          <Link href={editHref} className="text-primary hover:underline not-italic">
            completar en Documentos
          </Link>
        </p>
      ) : (
        <p className="text-muted-foreground italic">—</p>
      )}
    </div>
  );
}
