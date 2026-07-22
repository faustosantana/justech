import type { M365DocumentItem } from "@/lib/m365-documents";

/** Detecta si el texto parece ruta de carpeta, no búsqueda semántica. */
export function isPathLikeM365Query(query: string): boolean {
  const q = (query || "").trim();
  if (!q) return false;
  if (q.includes("/") || q.includes("\\")) return true;
  if (/^justech-ai/i.test(q)) return true;
  if (/^0[01]_/i.test(q)) return true;
  if (q.split("_").length >= 3 && q.length > 12) return true;
  return false;
}

export type M365PickerMode = "link" | "import" | "both";

/** Carpeta OneDrive corporativa por empresa del grupo (licitaciones / DGCP). */
const DGCP_COMPANY_FOLDER: Record<string, string> = {
  justech: "JUSTECH",
  just_office: "JUST OFFICE",
  mf_plug_safe: "MF PLUG SAFE",
  omni_solutions: "OMNI SOLUTIONS",
};

export function dgcpCompanyM365Folder(companyKey: string): string {
  const folder = DGCP_COMPANY_FOLDER[companyKey] || companyKey.toUpperCase().replace(/_/g, " ");
  return `Justech-AI/01_DOCUMENTOS_LEGALES/${folder}`;
}

export type M365DgcpChecklistTarget = {
  opportunityId: string;
  itemId: string;
};

export type M365RepositoryTarget = {
  bindingId: string;
  bindingLabel?: string;
};

export type M365DocumentPickerProps = {
  open: boolean;
  onClose: () => void;
  entityType?: string;
  entityId: string;
  companyId?: string;
  requirementId?: string;
  fieldKey?: string;
  fieldLabel?: string;
  representativeId?: string;
  dgcpChecklist?: M365DgcpChecklistTarget;
  repositoryTarget?: M365RepositoryTarget;
  allowedFileTypes?: string[];
  mode?: M365PickerMode;
  initialQuery?: string;
  initialTab?: "search" | "browse" | "recent" | "linked";
  title?: string;
  onSelected?: (item: M365DocumentItem) => void;
  onLinked?: (message: string) => void;
  onImported?: (message: string) => void;
  onDgcpAssociated?: (result: {
    checklist: import("@/lib/dgcp").DGCPChecklist;
    bid_package: import("@/lib/dgcp").DGCPBidPackage;
    expediente_status: string;
  }) => void;
  attachMode?: {
    label?: string;
    attaching?: boolean;
    onAttach: (item: M365DocumentItem) => void | Promise<void>;
  };
};
