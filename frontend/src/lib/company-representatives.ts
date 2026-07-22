export type RepresentativeDocument = {
  id: string;
  document_type: string;
  document_label: string;
  filename?: string | null;
  status: string;
  badge: string;
  validation_status: string;
  validation_badge: string;
  validation_method?: string | null;
  validation_notes?: string | null;
  validated_at?: string | null;
  validated_by_name?: string | null;
  expiration_date?: string | null;
  knowledge_asset_id?: string | null;
  m365_web_url?: string | null;
  m365_item_id?: string | null;
  link_mode?: string | null;
  requires_validation: boolean;
};

export type CompanyRepresentative = {
  id: string;
  full_name: string;
  identification_type: string;
  identification_number?: string | null;
  position?: string | null;
  relation_type: string;
  relation_label: string;
  roles?: string[];
  role_labels?: string[];
  email?: string | null;
  phone?: string | null;
  can_sign: boolean;
  is_legal_representative: boolean;
  can_participate_in_bids: boolean;
  ownership_percentage?: number | null;
  start_date?: string | null;
  end_date?: string | null;
  is_active: boolean;
  documents: RepresentativeDocument[];
  documents_loaded: number;
  documents_pending_validation: number;
  documents_missing: number;
  status_summary: string;
};

export type RepresentativesSummary = {
  company_id: string;
  company_key: string;
  representatives: CompanyRepresentative[];
  total_representatives: number;
  validation_pending_count: number;
  documents_missing_count: number;
  all_validated: boolean;
};

export type RepresentativeCreatePayload = {
  full_name: string;
  identification_type?: string;
  identification_number?: string;
  position?: string;
  relation_type?: string;
  email?: string;
  phone?: string;
  can_sign?: boolean;
  is_legal_representative?: boolean;
  can_participate_in_bids?: boolean;
  ownership_percentage?: number;
  is_active?: boolean;
};

export const RELATION_TYPES = [
  { value: "representante_legal", label: "Representante legal" },
  { value: "responsable_legal", label: "Responsable legal" },
  { value: "responsable_financiero", label: "Responsable financiero" },
  { value: "gerente_general", label: "Gerente general" },
  { value: "presidente", label: "Presidente" },
  { value: "socio_administrador", label: "Socio administrador" },
  { value: "accionista", label: "Accionista" },
  { value: "apoderado", label: "Apoderado" },
  { value: "firmante_autorizado", label: "Firmante autorizado" },
  { value: "miembro_consejo", label: "Miembro del consejo" },
  { value: "contacto_administrativo", label: "Contacto administrativo" },
];

export function validationBadgeClass(status: string): string {
  if (status === "validated") return "bg-emerald-100 text-emerald-800 border-emerald-200";
  if (status === "rejected") return "bg-red-100 text-red-800 border-red-200";
  if (status === "needs_correction") return "bg-orange-100 text-orange-800 border-orange-200";
  return "bg-amber-100 text-amber-800 border-amber-200";
}

export function documentBadgeClass(status: string, validationStatus: string): string {
  if (status === "missing") return "bg-red-100 text-red-800";
  if (validationStatus === "validated") return "bg-emerald-100 text-emerald-800";
  if (validationStatus === "pending") return "bg-amber-100 text-amber-800";
  if (validationStatus === "rejected") return "bg-red-100 text-red-800";
  return "bg-sky-100 text-sky-800";
}
