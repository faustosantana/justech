/** Microsoft 365 Operativo — tipos workspace premium */

export type M365AppId =
  | "outlook"
  | "calendar"
  | "teams"
  | "onedrive"
  | "sharepoint"
  | "documents"
  | "repositories"
  | "search";

export type M365MailFolder =
  | "inbox"
  | "sent"
  | "drafts"
  | "archive"
  | "deleted"
  | "junk";

export const M365_MAIL_FOLDERS: { id: M365MailFolder; label: string }[] = [
  { id: "inbox", label: "Bandeja de entrada" },
  { id: "sent", label: "Enviados" },
  { id: "drafts", label: "Borradores" },
  { id: "archive", label: "Archivo" },
  { id: "deleted", label: "Eliminados" },
  { id: "junk", label: "Correo no deseado" },
];

export const M365_APPS: { id: M365AppId; label: string; color: string }[] = [
  { id: "outlook", label: "Correo", color: "bg-[#0078D4]" },
  { id: "calendar", label: "Calendario", color: "bg-[#107C10]" },
  { id: "teams", label: "Teams", color: "bg-[#6264A7]" },
  { id: "onedrive", label: "OneDrive", color: "bg-[#0078D4]" },
  { id: "sharepoint", label: "SharePoint", color: "bg-[#038387]" },
  { id: "documents", label: "Documentos", color: "bg-[#8764B8]" },
  { id: "repositories", label: "Repositorios", color: "bg-[#5C2D91]" },
  { id: "search", label: "Búsqueda", color: "bg-[#0078D4]" },
];

export type CalendarViewMode = "month" | "week" | "day" | "agenda";

export interface M365DriveItem {
  id?: string;
  name?: string;
  is_folder?: boolean;
  web_url?: string;
  download_url?: string;
  mime_type?: string;
  size_bytes?: number;
  modified_at?: string;
  owner_name?: string;
  source?: string;
}

export interface ComposeAttachment {
  name: string;
  content_type?: string;
  content_base64?: string;
  onedrive_item_id?: string;
  source_url?: string;
}

export interface ComposeState {
  mode: "new" | "reply" | "replyAll" | "forward";
  messageId?: string;
  subject: string;
  to: string;
  cc: string;
  body: string;
  cloudAttachments?: ComposeAttachment[];
}

export function formatBytes(n?: number | null): string {
  if (!n) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDate(iso?: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString("es-DO", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function startOfWeek(date: Date): Date {
  const d = new Date(date);
  const day = (d.getDay() + 6) % 7;
  d.setDate(d.getDate() - day);
  d.setHours(0, 0, 0, 0);
  return d;
}

export function weekDays(date: Date): Date[] {
  const start = startOfWeek(date);
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    return d;
  });
}

export function dayHours(): number[] {
  return Array.from({ length: 14 }, (_, i) => i + 7);
}
