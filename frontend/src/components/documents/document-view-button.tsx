"use client";

import { Eye, Loader2 } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { openDocument, type DocumentAccessParams } from "@/lib/document-access";

export type DocumentViewButtonProps = DocumentAccessParams & {
  /** Fallback solo si no hay IDs — preferir IDs para pasar por DocumentAccessService */
  webUrl?: string | null;
  viewUrl?: string | null;
  label?: string;
  variant?: "default" | "outline" | "ghost" | "secondary";
  size?: "default" | "sm" | "lg" | "icon";
  className?: string;
  disabled?: boolean;
  stopPropagation?: boolean;
};

function hasResolvableTarget(props: DocumentViewButtonProps): boolean {
  return Boolean(
    props.knowledgeAssetId ||
      props.documentId ||
      props.documentLinkId ||
      props.m365FileId ||
      props.graphItemId ||
      props.processDocumentId ||
      props.webUrl ||
      props.viewUrl,
  );
}

export function DocumentViewButton({
  webUrl,
  viewUrl,
  label = "Ver documento",
  variant = "outline",
  size = "sm",
  className,
  disabled,
  stopPropagation,
  ...params
}: DocumentViewButtonProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!hasResolvableTarget({ ...params, webUrl, viewUrl })) return null;

  const handleClick = async (e?: React.MouseEvent) => {
    if (stopPropagation) e?.stopPropagation();
    setBusy(true);
    setError(null);
    try {
      await openDocument({ ...params, webUrl: webUrl ?? viewUrl ?? undefined });
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo abrir el documento.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <span className={className}>
      <Button
        size={size}
        variant={variant}
        disabled={disabled || busy}
        onClick={(e) => void handleClick(e)}
      >
        {busy ? <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" /> : <Eye className="mr-1 h-3.5 w-3.5" />}
        {label}
      </Button>
      {error && <span className="ml-2 text-xs text-destructive">{error}</span>}
    </span>
  );
}

/** Alias compacto para listados M365 indexados */
export function DocumentViewLink(props: DocumentViewButtonProps) {
  return <DocumentViewButton {...props} label={props.label ?? "Abrir"} variant={props.variant ?? "ghost"} size="sm" />;
}
