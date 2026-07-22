export interface CorporateIdentityAsset {
  id?: string | null;
  asset_type: string;
  company_key?: string | null;
  company_label?: string | null;
  filename: string;
  status: string;
  storage_relative_path?: string | null;
  uploaded_at?: string | null;
  uploaded_by?: string | null;
  preview_url?: string | null;
  warnings?: string[];
}

export interface CorporateIdentityOverview {
  root_path: string;
  metadata_loaded: boolean;
  default_signature: string;
  active_company_key?: string | null;
  active_company_label?: string | null;
  signature?: CorporateIdentityAsset | null;
  stamp?: CorporateIdentityAsset | null;
  signatures: CorporateIdentityAsset[];
  stamps: CorporateIdentityAsset[];
  missing: string[];
  alerts: string[];
  placement: Record<string, unknown>;
}

export interface DocumentFinalizationPreview {
  opportunity_id: string;
  requirement_key: string;
  document_type: string;
  document_title?: string | null;
  company_key: string;
  company_label: string;
  signature?: Record<string, unknown> | null;
  stamp?: Record<string, unknown> | null;
  placement: Record<string, unknown>;
  source_filename?: string | null;
  warnings: string[];
  can_finalize: boolean;
  requires_signature: boolean;
  requires_stamp: boolean;
}

export interface DocumentFinalizationRecord {
  id: string;
  requirement_key: string;
  document_type: string;
  output_filename: string;
  output_storage_uri: string;
  previous_status?: string | null;
  new_status: string;
  signature_filename?: string | null;
  stamp_filename?: string | null;
  company_key: string;
  finalized_at?: string | null;
  download_url?: string | null;
}

export const IDENTITY_STATUS_LABELS: Record<string, string> = {
  disponible: "Disponible",
  faltante: "Faltante",
  invalido: "Inválido",
  requiere_revision: "Requiere revisión",
};
