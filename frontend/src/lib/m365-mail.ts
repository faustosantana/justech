/** Microsoft 365 — correo operativo (Outlook) */

export type M365MailFolder = "inbox" | "sent" | "drafts" | "archive";

export interface M365AccountSummary {
  id: string;
  email: string | null;
  display_name: string | null;
  connection_mode: string;
  connection_status: string;
  microsoft_user_id?: string | null;
  token_expires_at?: string | null;
  last_sync_at?: string | null;
  is_active: boolean;
  jaios_user_id?: string | null;
  token_status?: string | null;
  last_graph_error?: string | null;
}

export interface M365ConnectionState {
  connected: boolean;
  account_connected: boolean;
  azure_configured: boolean;
  oauth_ready: boolean;
  read_only: boolean;
  message: string;
  tenant_id: string | null;
  client_id: string | null;
  redirect_uri: string;
  webhook_url: string | null;
  connected_accounts: M365AccountSummary[];
  active_account: M365AccountSummary | null;
}

export interface M365MailAttachment {
  id?: string | null;
  name: string;
  size_bytes?: number | null;
  content_type?: string | null;
  is_inline?: boolean;
}

export interface M365MailMessage {
  id: string;
  subject: string;
  sender: string;
  sender_name?: string | null;
  to_recipients: string[];
  cc_recipients?: string[];
  received_at: string | null;
  sent_at?: string | null;
  preview: string;
  body_html?: string | null;
  body_text?: string | null;
  is_read: boolean;
  has_attachments: boolean;
  attachments?: M365MailAttachment[];
  web_link?: string | null;
  folder: string;
  account_id?: string | null;
  account_email?: string | null;
}

export interface M365MailListResponse {
  items: M365MailMessage[];
  total: number;
  folder: string;
  account_id?: string | null;
  account_email?: string | null;
  connected: boolean;
  read_only: boolean;
  message: string;
  error?: string;
  permission_hint?: string;
}

export interface M365MailDetail extends M365MailMessage {
  connected: boolean;
  read_only: boolean;
  can_reply: boolean;
  can_forward: boolean;
}

export const M365_MAIL_FOLDERS: { id: M365MailFolder; label: string }[] = [
  { id: "inbox", label: "Bandeja de entrada" },
  { id: "sent", label: "Enviados" },
  { id: "drafts", label: "Borradores" },
  { id: "archive", label: "Archivo" },
];

export const M365_GRAPH_PERMISSIONS = [
  { scope: "User.Read", description: "Perfil del usuario", adminConsent: false },
  { scope: "offline_access", description: "Refresh token", adminConsent: false },
  { scope: "Mail.Read", description: "Leer correos", adminConsent: false },
  { scope: "Mail.ReadWrite", description: "Marcar leído, archivar", adminConsent: false },
  { scope: "Mail.Send", description: "Enviar, responder, reenviar", adminConsent: false },
  { scope: "Calendars.Read", description: "Leer calendario", adminConsent: false },
  { scope: "Calendars.ReadWrite", description: "Crear/editar eventos", adminConsent: false },
  { scope: "Contacts.Read", description: "Leer contactos", adminConsent: false },
  { scope: "Contacts.ReadWrite", description: "Crear/editar contactos", adminConsent: false },
  { scope: "Files.Read", description: "Leer OneDrive", adminConsent: false },
  { scope: "Files.ReadWrite", description: "Subir archivos OneDrive", adminConsent: true },
  { scope: "Sites.Read.All", description: "Leer SharePoint", adminConsent: true },
  { scope: "Sites.ReadWrite.All", description: "Escribir SharePoint", adminConsent: true },
  { scope: "Team.ReadBasic.All", description: "Listar Teams", adminConsent: false },
  { scope: "Channel.ReadBasic.All", description: "Canales Teams", adminConsent: false },
  { scope: "ChannelMessage.Read.All", description: "Leer mensajes Teams", adminConsent: true },
  { scope: "Chat.Read", description: "Leer chats", adminConsent: true },
  { scope: "Chat.ReadWrite", description: "Enviar chats", adminConsent: true },
  { scope: "Group.Read.All", description: "Grupos Microsoft 365", adminConsent: true },
];
