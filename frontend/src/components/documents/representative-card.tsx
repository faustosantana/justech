"use client";

import {
  CheckCircle2,
  Download,
  ExternalLink,
  FileText,
  History,
  Loader2,
  Pencil,
  RefreshCw,
  Search,
  ShieldCheck,
  Trash2,
  Upload,
  UserMinus,
  XCircle,
} from "lucide-react";
import { useState } from "react";

import { DocumentViewButton } from "@/components/documents/document-view-button";
import { M365DocumentSearchPicker } from "@/components/m365/m365-document-search-picker";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";
import type { CompanyRepresentative, RepresentativeDocument } from "@/lib/company-representatives";
import { documentBadgeClass, validationBadgeClass } from "@/lib/company-representatives";
import { cn } from "@/lib/utils";

const FIELD_BY_DOC: Record<string, string> = {
  cedula: "cedula_representante",
  poder_notarial: "poderes",
  acta_designacion: "acta_asamblea",
};

const DOC_LABELS: Record<string, string> = {
  cedula: "Cédula",
  poder_notarial: "Poder notarial",
  acta_designacion: "Acta de designación",
};

function missingDoc(docType: string): RepresentativeDocument {
  return {
    id: "",
    document_type: docType,
    document_label: DOC_LABELS[docType] ?? docType,
    status: "missing",
    badge: "Pendiente",
    validation_status: "pending",
    validation_badge: "Pendiente de validar",
    requires_validation: docType === "cedula",
  };
}

export function RepresentativeCard({
  companyId,
  rep,
  onEdit,
  onChanged,
  documentTypes,
  showHeaderActions = true,
}: {
  companyId: string;
  rep: CompanyRepresentative;
  onEdit: (rep: CompanyRepresentative) => void;
  onChanged?: () => void;
  documentTypes?: string[];
  showHeaderActions?: boolean;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [historyDoc, setHistoryDoc] = useState<RepresentativeDocument | null>(null);
  const [picker, setPicker] = useState<{ fieldKey: string; label: string; query: string } | null>(null);

  const docs = documentTypes?.length
    ? documentTypes.map((t) => rep.documents.find((d) => d.document_type === t) ?? missingDoc(t))
    : rep.documents;

  const canDelete = rep.documents_loaded === 0;

  const runValidation = async (
    doc: RepresentativeDocument,
    validation_status: string,
    confirmMsg?: string,
  ) => {
    if (doc.document_type === "cedula" && validation_status === "validated" && !rep.identification_number?.trim()) {
      setError("Indique el número de cédula del representante antes de validar.");
      return;
    }
    if (confirmMsg && !window.confirm(confirmMsg)) return;
    setBusy(`${rep.id}:${doc.document_type}:${validation_status}`);
    setError(null);
    try {
      await apiClient.validateRepresentativeDocument(companyId, rep.id, doc.document_type, {
        validation_status,
        validation_method: "manual",
      });
      onChanged?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar la validación.");
    } finally {
      setBusy(null);
    }
  };

  const deactivate = async () => {
    if (!window.confirm(`¿Desactivar a ${rep.full_name}? Dejará de aparecer en el expediente.`)) return;
    setBusy(`${rep.id}:deactivate`);
    setError(null);
    try {
      await apiClient.deactivateCompanyRepresentative(companyId, rep.id);
      onChanged?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo desactivar.");
    } finally {
      setBusy(null);
    }
  };

  const remove = async () => {
    if (!window.confirm(`¿Eliminar permanentemente a ${rep.full_name}?`)) return;
    setBusy(`${rep.id}:delete`);
    setError(null);
    try {
      await apiClient.deleteCompanyRepresentativePermanent(companyId, rep.id);
      onChanged?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo eliminar.");
    } finally {
      setBusy(null);
    }
  };

  const download = (url: string, name: string) => {
    const a = document.createElement("a");
    a.href = url;
    a.target = "_blank";
    a.rel = "noreferrer";
    a.download = name;
    a.click();
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base">{rep.full_name}</CardTitle>
            <p className="text-sm text-muted-foreground">
              {rep.relation_label}
              {rep.position ? ` · ${rep.position}` : ""}
              {rep.identification_number ? ` · ${rep.identification_number}` : ""}
            </p>
            <div className="mt-2 flex flex-wrap gap-1">
              <Badge variant={rep.is_active ? "default" : "secondary"}>
                {rep.is_active ? "Activo" : "Inactivo"}
              </Badge>
              {rep.is_legal_representative && (
                <Badge variant="outline" className="border-emerald-300 text-emerald-800">
                  Representante legal
                </Badge>
              )}
              {rep.can_sign && (
                <Badge variant="outline" className="border-blue-300 text-blue-800">
                  Puede firmar
                </Badge>
              )}
              {rep.can_participate_in_bids && (
                <Badge variant="outline">Participa en licitaciones</Badge>
              )}
            </div>
            <p className="mt-1 text-xs text-muted-foreground">{rep.status_summary}</p>
          </div>
          {showHeaderActions && (
            <div className="flex flex-wrap gap-1">
              <Button size="sm" variant="outline" onClick={() => onEdit(rep)} disabled={!!busy}>
                <Pencil className="mr-1 h-3.5 w-3.5" />
                Editar
              </Button>
              <Button size="sm" variant="outline" onClick={() => void deactivate()} disabled={!!busy}>
                {busy === `${rep.id}:deactivate` ? (
                  <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                ) : (
                  <UserMinus className="mr-1 h-3.5 w-3.5" />
                )}
                Desactivar
              </Button>
              {canDelete && (
                <Button size="sm" variant="destructive" onClick={() => void remove()} disabled={!!busy}>
                  {busy === `${rep.id}:delete` ? (
                    <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Trash2 className="mr-1 h-3.5 w-3.5" />
                  )}
                  Eliminar
                </Button>
              )}
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {error && <p className="rounded-md bg-amber-50 px-2 py-1 text-xs text-amber-900">{error}</p>}
        {docs.map((doc) => (
          <div key={`${rep.id}-${doc.document_type}`} className="rounded-lg border bg-muted/20 px-3 py-3">
            <div className="mb-2">
              <p className="text-sm font-medium">
                {doc.document_label} — {rep.full_name}
              </p>
              <p className="text-xs text-muted-foreground">
                Cargo: {rep.relation_label}
                {doc.filename ? ` · Archivo: ${doc.filename}` : ""}
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                <Badge className={cn("border", documentBadgeClass(doc.status, doc.validation_status))}>
                  {doc.badge}
                </Badge>
                {doc.requires_validation && (
                  <Badge className={cn("border", validationBadgeClass(doc.validation_status))}>
                    {doc.validation_badge}
                  </Badge>
                )}
              </div>
              {doc.validation_status === "validated" && doc.validated_at && (
                <p className="mt-2 text-xs text-emerald-800">
                  <CheckCircle2 className="mr-1 inline h-3.5 w-3.5" />
                  Validado
                  {doc.validated_by_name ? ` por ${doc.validated_by_name}` : ""}
                  {" · "}
                  {new Date(doc.validated_at).toLocaleString()}
                </p>
              )}
            </div>
            <div className="flex flex-wrap gap-1 border-t border-border/40 pt-2">
              {doc.status === "loaded" && doc.requires_validation && doc.validation_status !== "validated" && (
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={!!busy}
                  onClick={() =>
                    void runValidation(
                      doc,
                      "validated",
                      `¿Confirmas que ${doc.document_label} corresponde a ${rep.full_name}?`,
                    )
                  }
                >
                  {busy === `${rep.id}:${doc.document_type}:validated` ? (
                    <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                  ) : (
                    <ShieldCheck className="mr-1 h-3 w-3" />
                  )}
                  Validar documento
                </Button>
              )}
              {doc.status === "loaded" && doc.requires_validation && doc.validation_status !== "rejected" && (
                <Button
                  size="sm"
                  variant="outline"
                  disabled={!!busy}
                  onClick={() =>
                    void runValidation(doc, "rejected", `¿Rechazar ${doc.document_label} de ${rep.full_name}?`)
                  }
                >
                  {busy === `${rep.id}:${doc.document_type}:rejected` ? (
                    <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                  ) : (
                    <XCircle className="mr-1 h-3 w-3" />
                  )}
                  Rechazar documento
                </Button>
              )}
              {doc.validation_status === "validated" && (
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={!!busy}
                  onClick={() =>
                    void runValidation(doc, "pending", "¿Revertir la validación de este documento?")
                  }
                >
                  <RefreshCw className="mr-1 h-3 w-3" />
                  Revertir validación
                </Button>
              )}
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  setPicker({
                    fieldKey: FIELD_BY_DOC[doc.document_type] ?? "cedula_representante",
                    label: doc.document_label,
                    query: rep.full_name,
                  })
                }
              >
                <Search className="mr-1 h-3 w-3" />
                Buscar documento
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  setPicker({
                    fieldKey: FIELD_BY_DOC[doc.document_type] ?? "cedula_representante",
                    label: `Reemplazar ${doc.document_label}`,
                    query: rep.full_name,
                  })
                }
              >
                <Upload className="mr-1 h-3 w-3" />
                Reemplazar documento
              </Button>
              <DocumentViewButton
                knowledgeAssetId={doc.knowledge_asset_id}
                webUrl={doc.m365_web_url}
              />
              {(doc.validated_at || doc.validation_notes) && (
                <Button size="sm" variant="ghost" onClick={() => setHistoryDoc(doc)}>
                  <History className="mr-1 h-3 w-3" />
                  Ver historial
                </Button>
              )}
            </div>
          </div>
        ))}
      </CardContent>

      <M365DocumentSearchPicker
        open={!!picker}
        onClose={() => setPicker(null)}
        companyId={companyId}
        representativeId={rep.id}
        fieldKey={picker?.fieldKey}
        fieldLabel={picker?.label}
        initialQuery={picker?.query ?? ""}
        title={picker?.label ?? "Buscar documento"}
        onLinked={() => {
          setPicker(null);
          onChanged?.();
        }}
      />

      {historyDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <Card className="w-full max-w-md">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">Historial — {historyDoc.document_label}</CardTitle>
              <button type="button" onClick={() => setHistoryDoc(null)}>
                <FileText className="h-5 w-5 text-muted-foreground" />
              </button>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p>
                <strong>Estado:</strong> {historyDoc.validation_badge}
              </p>
              {historyDoc.validation_method && (
                <p>
                  <strong>Método:</strong> {historyDoc.validation_method}
                </p>
              )}
              {historyDoc.validated_by_name && (
                <p>
                  <strong>Validado por:</strong> {historyDoc.validated_by_name}
                </p>
              )}
              {historyDoc.validated_at && (
                <p>
                  <strong>Fecha:</strong> {new Date(historyDoc.validated_at).toLocaleString()}
                </p>
              )}
              {historyDoc.validation_notes && (
                <p>
                  <strong>Notas:</strong> {historyDoc.validation_notes}
                </p>
              )}
              <Button className="mt-2 w-full" variant="outline" onClick={() => setHistoryDoc(null)}>
                Cerrar
              </Button>
            </CardContent>
          </Card>
        </div>
      )}
    </Card>
  );
}
