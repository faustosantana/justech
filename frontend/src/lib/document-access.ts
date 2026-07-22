import { apiClient } from "@/lib/api";
import { openAuthenticatedBlobInNewTab, fetchAuthenticatedFile } from "@/lib/authenticated-file";

export interface DocumentAccess {
  source_type: string;
  source_id: string;
  view_mode: "local" | "external";
  filename?: string | null;
  web_url?: string | null;
  local_api_path?: string | null;
  canonical_source_id?: string | null;
  relative_path?: string | null;
  available: boolean;
  reason?: string | null;
}

export type DocumentAccessParams = {
  knowledgeAssetId?: string | null;
  documentId?: string | null;
  documentLinkId?: string | null;
  m365FileId?: string | null;
  graphItemId?: string | null;
  processDocumentId?: string | null;
  opportunityId?: string | null;
};

const REASON_MESSAGES: Record<string, string> = {
  asset_not_found: "El documento ya no está disponible o fue consolidado sin ruta válida.",
  document_not_found: "Documento no encontrado en JAIOS.",
  link_not_found: "Vínculo documental no encontrado.",
  m365_file_not_found: "Archivo no encontrado en el índice M365.",
  no_local_or_web_url: "No hay copia local ni enlace OneDrive para este documento.",
  storage_missing: "El archivo no está en almacenamiento local.",
  no_access_path: "No se encontró ruta de acceso para el documento vinculado.",
  no_web_url: "El archivo M365 no tiene URL de acceso.",
  no_source_specified: "Indique qué documento desea abrir.",
  not_found: "Documento no encontrado.",
  process_document_not_found: "Documento de proceso no encontrado.",
};

function humanAccessError(reason?: string | null): string {
  if (!reason) return "No se pudo abrir el documento.";
  return REASON_MESSAGES[reason] ?? `No se pudo abrir el documento (${reason}).`;
}

function toApiParams(params: DocumentAccessParams) {
  return {
    knowledge_asset_id: params.knowledgeAssetId ?? undefined,
    document_id: params.documentId ?? undefined,
    document_link_id: params.documentLinkId ?? undefined,
    m365_file_id: params.m365FileId ?? undefined,
    graph_item_id: params.graphItemId ?? undefined,
    process_document_id: params.processDocumentId ?? undefined,
    opportunity_id: params.opportunityId ?? undefined,
  };
}

function hasApiTarget(params: DocumentAccessParams): boolean {
  return Boolean(
    params.knowledgeAssetId ||
      params.documentId ||
      params.documentLinkId ||
      params.m365FileId ||
      params.graphItemId ||
      params.processDocumentId,
  );
}

export async function resolveDocumentAccess(params: DocumentAccessParams): Promise<DocumentAccess> {
  return apiClient.resolveDocumentAccess(toApiParams(params));
}

/** Abre documento vía DocumentAccessService (local, M365 o canónico deduplicado). */
export async function openDocument(params: DocumentAccessParams & { webUrl?: string | null }): Promise<void> {
  if (hasApiTarget(params)) {
    const access = await resolveDocumentAccess(params);
    if (!access.available) {
      throw new Error(humanAccessError(access.reason));
    }
    if (access.view_mode === "external" && access.web_url) {
      window.open(access.web_url, "_blank", "noopener,noreferrer");
      return;
    }
    if (access.local_api_path) {
      const file = await fetchAuthenticatedFile(access.local_api_path);
      openAuthenticatedBlobInNewTab(file.objectUrl);
      return;
    }
    throw new Error(humanAccessError(access.reason));
  }

  if (params.webUrl?.startsWith("http")) {
    window.open(params.webUrl, "_blank", "noopener,noreferrer");
    return;
  }

  throw new Error("No hay ruta válida para abrir este documento.");
}
