"use client";

import {
  Archive,
  Calendar,
  ChevronLeft,
  ChevronRight,
  File,
  Folder,
  Inbox,
  Mail,
  Paperclip,
  Plus,
  RefreshCw,
  Search,
  Send,
  Trash2,
  Users,
  X,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { DocumentViewLink } from "@/components/documents/document-view-button";
import { M365AttachmentPicker, type PickedAttachment } from "@/components/m365/m365-attachment-picker";
import { M365CalendarEventModal } from "@/components/m365/m365-calendar-event-modal";
import { M365MailAiPanel } from "@/components/m365/m365-mail-ai-panel";
import { M365RepositoriesPanel } from "@/components/m365/m365-repositories-panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api";
import type { M365ConnectionState, M365MailDetail, M365MailMessage } from "@/lib/m365-mail";
import {
  M365_APPS,
  M365_MAIL_FOLDERS,
  type CalendarViewMode,
  type ComposeState,
  type M365AppId,
  type M365DriveItem,
  type M365MailFolder,
  formatBytes,
  formatDate,
  startOfWeek,
  weekDays,
  dayHours,
} from "@/lib/m365-workspace";
import { cn } from "@/lib/utils";

function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-md bg-muted/60", className)} />;
}

function ErrorBanner({ message, hint, onRetry }: { message: string; hint?: string | null; onRetry?: () => void }) {
  return (
    <div className="m-4 rounded-xl border border-destructive/20 bg-destructive/5 p-4 text-sm">
      <p className="font-medium text-destructive">{message}</p>
      {hint && <p className="mt-1 text-muted-foreground">{hint}</p>}
      {onRetry && (
        <Button size="sm" variant="outline" className="mt-3" onClick={onRetry}>
          Reintentar
        </Button>
      )}
    </div>
  );
}

function EmptyState({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-center text-muted-foreground">
      <p className="text-base font-medium text-foreground">{title}</p>
      {subtitle && <p className="max-w-sm text-sm">{subtitle}</p>}
    </div>
  );
}

// ─── Compose modal ───────────────────────────────────────────────────────────

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      resolve(result.split(",")[1] ?? "");
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function ComposeModal({
  open,
  state,
  onChange,
  onClose,
  onSend,
  onSaveDraft,
  sending,
  readOnly,
  files,
  onFilesChange,
  onPickCloud,
  cloudCount,
}: {
  open: boolean;
  state: ComposeState;
  onChange: (s: ComposeState) => void;
  onClose: () => void;
  onSend: () => void;
  onSaveDraft?: () => void;
  sending: boolean;
  readOnly?: boolean;
  files: File[];
  onFilesChange: (f: File[]) => void;
  onPickCloud?: () => void;
  cloudCount?: number;
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center">
      <div className="w-full max-w-2xl rounded-2xl border border-border bg-background shadow-2xl">
        <div className="flex items-center justify-between border-b px-4 py-3">
          <p className="font-semibold">
            {state.mode === "new" ? "Nuevo correo" : state.mode === "forward" ? "Reenviar" : "Responder"}
          </p>
          <button type="button" onClick={onClose} className="rounded-lg p-1 hover:bg-muted">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="space-y-3 p-4">
          <Input placeholder="Para (emails separados por coma)" value={state.to} onChange={(e) => onChange({ ...state, to: e.target.value })} />
          <Input placeholder="CC" value={state.cc} onChange={(e) => onChange({ ...state, cc: e.target.value })} />
          <Input placeholder="Asunto" value={state.subject} onChange={(e) => onChange({ ...state, subject: e.target.value })} />
          <textarea
            className="min-h-[160px] w-full rounded-lg border border-border bg-background p-3 text-sm"
            placeholder="Escriba su mensaje…"
            value={state.body}
            onChange={(e) => onChange({ ...state, body: e.target.value })}
          />
          <div className="flex items-center gap-2">
            <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm hover:bg-muted">
              <Paperclip className="h-4 w-4" />
              Adjuntar archivo
              <input
                type="file"
                multiple
                className="hidden"
                onChange={(e) => onFilesChange(Array.from(e.target.files ?? []))}
              />
            </label>
            {onPickCloud && (
              <Button type="button" size="sm" variant="outline" onClick={onPickCloud}>
                OneDrive
              </Button>
            )}
            {(files.length > 0 || (cloudCount ?? 0) > 0) && (
              <span className="text-xs text-muted-foreground">
                {files.length} local · {cloudCount ?? 0} nube
              </span>
            )}
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t px-4 py-3">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          {state.mode === "new" && onSaveDraft && !readOnly && (
            <Button variant="outline" onClick={onSaveDraft} disabled={sending}>
              Guardar borrador
            </Button>
          )}
          <Button onClick={onSend} disabled={sending || readOnly}>
            <Send className="mr-2 h-4 w-4" />
            {sending ? "Enviando…" : readOnly ? "Solo lectura" : "Enviar"}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ─── Main workspace ────────────────────────────────────────────────────────────

export function M365Workspace({
  initialApp = "outlook",
  embedded = false,
}: {
  initialApp?: M365AppId;
  embedded?: boolean;
} = {}) {
  const [app, setApp] = useState<M365AppId>(initialApp);
  const [connection, setConnection] = useState<M365ConnectionState | null>(null);
  const [accountId, setAccountId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [permissionHint, setPermissionHint] = useState<string | null>(null);

  // Outlook state
  const [folder, setFolder] = useState<M365MailFolder>("inbox");
  const [mailSearch, setMailSearch] = useState("");
  const [messages, setMessages] = useState<M365MailMessage[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<M365MailDetail | null>(null);
  const [compose, setCompose] = useState<ComposeState | null>(null);
  const [sending, setSending] = useState(false);
  const [composeFiles, setComposeFiles] = useState<File[]>([]);
  const [cloudAttachments, setCloudAttachments] = useState<PickedAttachment[]>([]);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [calendarModalOpen, setCalendarModalOpen] = useState(false);
  const [calendarEditEvent, setCalendarEditEvent] = useState<Record<string, unknown> | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // Calendar
  const [calView, setCalView] = useState<CalendarViewMode>("month");
  const [calMonth, setCalMonth] = useState(() => new Date());
  const [calFocus, setCalFocus] = useState(() => new Date());
  const [events, setEvents] = useState<Record<string, unknown>[]>([]);
  const [calLoading, setCalLoading] = useState(false);

  // Teams
  const [teams, setTeams] = useState<Record<string, unknown>[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<string | null>(null);
  const [channels, setChannels] = useState<Record<string, unknown>[]>([]);
  const [selectedChannel, setSelectedChannel] = useState<string | null>(null);
  const [teamMessages, setTeamMessages] = useState<Record<string, unknown>[]>([]);
  const [teamsLoading, setTeamsLoading] = useState(false);

  // Files
  const [driveItems, setDriveItems] = useState<M365DriveItem[]>([]);
  const [folderStack, setFolderStack] = useState<{ id: string; name: string }[]>([{ id: "root", name: "OneDrive" }]);
  const [fileSearch, setFileSearch] = useState("");
  const [filesLoading, setFilesLoading] = useState(false);
  const [documentItems, setDocumentItems] = useState<M365DriveItem[]>([]);
  const [spSites, setSpSites] = useState<Record<string, unknown>[]>([]);
  const [spDriveId, setSpDriveId] = useState<string | null>(null);
  const [spDriveItems, setSpDriveItems] = useState<M365DriveItem[]>([]);
  const [spFolderStack, setSpFolderStack] = useState<{ id: string; name: string }[]>([]);
  const [spSiteName, setSpSiteName] = useState<string | null>(null);

  // Search
  const [searchQ, setSearchQ] = useState("");
  const [searchGroups, setSearchGroups] = useState<Record<string, Record<string, unknown>[]>>({});

  const connected = connection?.account_connected ?? false;
  const readOnly = connection?.read_only ?? true;
  const canWrite = connected && !readOnly;
  const accounts = connection?.connected_accounts ?? [];

  useEffect(() => {
    setApp(initialApp);
  }, [initialApp]);

  const loadConnection = useCallback(async () => {
    setLoading(true);
    try {
      const conn = await apiClient.getM365Connection();
      setConnection(conn);
      if (!accountId && conn.active_account?.id) setAccountId(conn.active_account.id);
    } finally {
      setLoading(false);
    }
  }, [accountId]);

  useEffect(() => {
    void loadConnection();
  }, [loadConnection]);

  const clearError = () => {
    setError(null);
    setPermissionHint(null);
  };

  const loadMail = useCallback(async () => {
    if (!connected) return;
    clearError();
    setLoading(true);
    try {
      const res = await apiClient.getM365MailMessages({
        folder,
        search: mailSearch.trim() || undefined,
        account_id: accountId ?? undefined,
        limit: 50,
      });
      setMessages(res.items);
      if (res.error) {
        setError(res.message);
        setPermissionHint(res.permission_hint ?? null);
      }
    } finally {
      setLoading(false);
    }
  }, [connected, folder, mailSearch, accountId]);

  const loadDetail = useCallback(
    async (id: string) => {
      const d = await apiClient.getM365MailMessage(id, accountId ?? undefined);
      setDetail(d);
      if (!d.is_read && canWrite) {
        await apiClient.patchM365MailMessage(id, { is_read: true }, accountId ?? undefined);
      }
    },
    [accountId, canWrite],
  );

  useEffect(() => {
    if (app === "outlook" && connected) void loadMail();
  }, [app, connected, loadMail]);

  useEffect(() => {
    if (selectedId) void loadDetail(selectedId);
    else setDetail(null);
  }, [selectedId, loadDetail]);

  const loadCalendar = useCallback(async () => {
    if (!connected) return;
    clearError();
    setCalLoading(true);
    let start: Date;
    let end: Date;
    if (calView === "week" || calView === "day") {
      if (calView === "day") {
        start = new Date(calFocus);
        start.setHours(0, 0, 0, 0);
        end = new Date(calFocus);
        end.setHours(23, 59, 59, 999);
      } else {
        start = startOfWeek(calFocus);
        end = new Date(start);
        end.setDate(start.getDate() + 6);
        end.setHours(23, 59, 59, 999);
      }
    } else {
      start = new Date(calMonth.getFullYear(), calMonth.getMonth(), 1);
      end = new Date(calMonth.getFullYear(), calMonth.getMonth() + 1, 0, 23, 59, 59);
    }
    try {
      const res = await apiClient.getM365CalendarEvents({
        start: start.toISOString(),
        end: end.toISOString(),
        account_id: accountId ?? undefined,
        limit: 200,
      });
      setEvents(res.items as Record<string, unknown>[]);
      if (res.error) {
        setError(res.message);
        setPermissionHint(res.permission_hint ?? null);
      }
    } finally {
      setCalLoading(false);
    }
  }, [connected, calMonth, calFocus, calView, accountId]);

  useEffect(() => {
    if (app === "calendar" && connected) void loadCalendar();
  }, [app, connected, loadCalendar]);

  const loadTeams = useCallback(async () => {
    if (!connected) return;
    clearError();
    setTeamsLoading(true);
    try {
      const res = await apiClient.getM365Teams(50, accountId ?? undefined);
      setTeams(res.items as Record<string, unknown>[]);
      if (res.error) {
        setError(res.message);
        setPermissionHint(res.permission_hint ?? null);
      }
    } finally {
      setTeamsLoading(false);
    }
  }, [connected, accountId]);

  useEffect(() => {
    if (app === "teams" && connected) void loadTeams();
  }, [app, connected, loadTeams]);

  useEffect(() => {
    if (!selectedTeam) return;
    apiClient.getM365TeamChannels(selectedTeam, accountId ?? undefined).then((r) => {
      setChannels(r.items as Record<string, unknown>[]);
      if (r.error) {
        setError(r.message);
        setPermissionHint(r.permission_hint ?? null);
      }
    });
  }, [selectedTeam, accountId]);

  useEffect(() => {
    if (!selectedTeam || !selectedChannel) return;
    apiClient.getM365TeamMessages(selectedTeam, selectedChannel, accountId ?? undefined).then((r) => {
      setTeamMessages(r.items as Record<string, unknown>[]);
    });
  }, [selectedTeam, selectedChannel, accountId]);

  const loadOneDrive = useCallback(async () => {
    if (!connected) return;
    clearError();
    setFilesLoading(true);
    const current = folderStack[folderStack.length - 1];
    try {
      const res = await apiClient.getM365OneDriveFiles({
        folder_id: current.id === "root" ? undefined : current.id,
        search: fileSearch.trim() || undefined,
        account_id: accountId ?? undefined,
      });
      setDriveItems(res.items as M365DriveItem[]);
      if (res.error) {
        setError(res.message);
        setPermissionHint(res.permission_hint ?? null);
      }
    } finally {
      setFilesLoading(false);
    }
  }, [connected, folderStack, fileSearch, accountId]);

  const loadDocuments = useCallback(async () => {
    if (!connected) return;
    clearError();
    setFilesLoading(true);
    try {
      const res = await apiClient.getM365Documents(fileSearch.trim(), 80, accountId ?? undefined);
      setDocumentItems(res.items as M365DriveItem[]);
      if (res.error) {
        setError(res.message);
        setPermissionHint(res.permission_hint ?? null);
      }
    } finally {
      setFilesLoading(false);
    }
  }, [connected, fileSearch, accountId]);

  useEffect(() => {
    if (app === "onedrive" && connected) void loadOneDrive();
    if (app === "documents" && connected) void loadDocuments();
  }, [app, connected, loadOneDrive, loadDocuments]);

  useEffect(() => {
    if (app === "sharepoint" && connected) {
      apiClient.getM365SharePointSites("", 50, accountId ?? undefined).then((r) => {
        setSpSites(r.items as Record<string, unknown>[]);
      });
    }
  }, [app, connected, accountId]);

  const runSearch = useCallback(async () => {
    if (!searchQ.trim() || !connected) return;
    clearError();
    const res = await apiClient.getM365Search(searchQ.trim(), 40, accountId ?? undefined);
    const groups = { ...(res.groups ?? {}) } as Record<string, Record<string, unknown>[]>;
    const semantic = await apiClient.getM365SemanticSearch(searchQ.trim(), 15);
    if (semantic.hits.length > 0) {
      groups.semantic = semantic.hits as Record<string, unknown>[];
    }
    setSearchGroups(groups);
    if (res.error) {
      setError(res.message);
      setPermissionHint(res.permission_hint ?? null);
    }
  }, [searchQ, connected, accountId]);

  async function handleUploadOneDrive(file: File) {
    const folder = folderStack[folderStack.length - 1];
    const folderId = folder.id === "root" ? undefined : folder.id;
    const res = await apiClient.uploadM365OneDrive(file, folderId, accountId ?? undefined);
    setActionMessage(res.ok ? res.message : res.message);
    await loadOneDrive();
  }

  async function handleUploadSharePoint(file: File) {
    if (!spDriveId) return;
    const folder = spFolderStack[spFolderStack.length - 1];
    const folderId = folder?.id === "root" ? undefined : folder?.id;
    const res = await apiClient.uploadM365SharePoint(spDriveId, file, folderId, accountId ?? undefined);
    setActionMessage(res.ok ? res.message : res.message);
  }

  const monthGrid = useMemo(() => {
    const y = calMonth.getFullYear();
    const m = calMonth.getMonth();
    const first = new Date(y, m, 1);
    const startPad = (first.getDay() + 6) % 7;
    const days: Date[] = [];
    for (let i = 0; i < startPad; i++) days.push(new Date(y, m, -startPad + i + 1));
    for (let d = 1; d <= new Date(y, m + 1, 0).getDate(); d++) days.push(new Date(y, m, d));
    return days;
  }, [calMonth]);

  const eventsByDay = useMemo(() => {
    const map: Record<string, Record<string, unknown>[]> = {};
    for (const ev of events) {
      const start = ev.start as string | undefined;
      if (!start) continue;
      const key = new Date(start).toDateString();
      map[key] = map[key] ?? [];
      map[key].push(ev);
    }
    return map;
  }, [events]);

  async function handleSendMail(saveDraft = false) {
    if (!compose || readOnly) return;
    setSending(true);
    setActionMessage(null);
    try {
      const to = compose.to.split(",").map((s) => s.trim()).filter(Boolean);
      const cc = compose.cc.split(",").map((s) => s.trim()).filter(Boolean);
      const fileAttachments = await Promise.all(
        composeFiles.map(async (f) => ({
          name: f.name,
          content_type: f.type || "application/octet-stream",
          content_base64: await fileToBase64(f),
        })),
      );
      const cloudAtts = (compose?.cloudAttachments ?? cloudAttachments).map((a) => ({
        name: a.name,
        onedrive_item_id: a.onedrive_item_id,
        source_url: a.source_url,
      }));
      const attachments = [...fileAttachments, ...cloudAtts];
      let result: { ok: boolean; message: string };
      if (compose.mode === "forward" && compose.messageId) {
        result = await apiClient.forwardM365Mail(compose.messageId, compose.body, to, accountId ?? undefined);
      } else if (compose.messageId && (compose.mode === "reply" || compose.mode === "replyAll")) {
        result = await apiClient.replyM365Mail(
          compose.messageId,
          compose.body,
          accountId ?? undefined,
          compose.mode === "replyAll",
        );
      } else {
        result = await apiClient.sendM365Mail(
          { subject: compose.subject, body: compose.body, to, cc, attachments, save_draft: saveDraft },
          accountId ?? undefined,
        );
      }
      if (!result.ok) {
        setActionMessage(result.message);
        return;
      }
      setCompose(null);
      setComposeFiles([]);
      setCloudAttachments([]);
      setActionMessage(saveDraft ? "Borrador guardado" : "Correo enviado");
      await loadMail();
    } catch (e) {
      setActionMessage(e instanceof Error ? e.message : "Error al enviar");
    } finally {
      setSending(false);
    }
  }

  async function downloadAttachment(messageId: string, attachmentId: string, fallbackName: string) {
    try {
      const { blob, filename } = await apiClient.downloadM365MailAttachment(
        messageId,
        attachmentId,
        accountId ?? undefined,
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename || fallbackName;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setActionMessage(e instanceof Error ? e.message : "No se pudo descargar");
    }
  }

  async function moveMessage(folderId: M365MailFolder) {
    if (!detail || readOnly) return;
    const result = await apiClient.patchM365MailMessage(
      detail.id,
      { move_to_folder: folderId },
      accountId ?? undefined,
    );
    if (!result.ok) {
      setActionMessage(result.message);
      return;
    }
    setSelectedId(null);
    setDetail(null);
    await loadMail();
  }

  function openCompose(mode: ComposeState["mode"], base?: M365MailDetail) {
    setCloudAttachments([]);
    setComposeFiles([]);
    setCompose({
      mode,
      messageId: base?.id,
      subject: mode === "forward" ? `Fwd: ${base?.subject ?? ""}` : mode === "new" ? "" : `Re: ${base?.subject ?? ""}`,
      to: mode === "forward" ? "" : base?.sender ?? "",
      cc: "",
      body: "",
      cloudAttachments: [],
    });
  }

  if (loading && !connection) {
    return (
      <div className="space-y-4 p-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-[480px] w-full" />
      </div>
    );
  }

  if (!connected) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 p-8 text-center">
        <Mail className="h-14 w-14 text-primary/40" />
        <h2 className="text-xl font-semibold">Conecte su cuenta Microsoft 365</h2>
        <p className="max-w-md text-muted-foreground">
          Acceda a correo, calendario, Teams y archivos en un solo lugar.
        </p>
        <Button asChild>
          <Link href={embedded ? "/apps/comunicaciones/canales" : "/m365/cuentas"}>Conectar cuenta</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="flex min-h-[calc(100vh-8rem)] flex-col overflow-hidden rounded-2xl border border-border bg-background shadow-sm">
      {/* App bar */}
      <header className="flex flex-wrap items-center gap-3 border-b bg-gradient-to-r from-[#0078D4]/5 to-transparent px-4 py-3">
        {!embedded && (
          <div className="flex gap-1 overflow-x-auto">
            {M365_APPS.map((a) => (
              <button
                key={a.id}
                type="button"
                onClick={() => {
                  setApp(a.id);
                  clearError();
                }}
                className={cn(
                  "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                  app === a.id ? `${a.color} text-white shadow` : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                {a.label}
              </button>
            ))}
          </div>
        )}
        {embedded && (
          <p className="text-sm font-medium text-foreground">
            {M365_APPS.find((a) => a.id === app)?.label ?? "Microsoft 365"}
          </p>
        )}
        <div className="ml-auto flex items-center gap-2">
          {accounts.length > 1 && (
            <select
              className="rounded-lg border border-border bg-background px-2 py-1.5 text-sm"
              value={accountId ?? ""}
              onChange={(e) => setAccountId(e.target.value || null)}
            >
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.email ?? a.display_name}
                </option>
              ))}
            </select>
          )}
          <span className="hidden text-sm text-muted-foreground sm:inline">
            {connection?.active_account?.email}
          </span>
          <Button size="icon" variant="ghost" onClick={() => void loadConnection()}>
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Link href="/m365/cuentas" className="text-xs text-muted-foreground hover:text-primary">
            Cuentas
          </Link>
        </div>
      </header>

      {readOnly && connected && (
        <div className="border-b bg-amber-500/10 px-4 py-2 text-sm text-amber-900 dark:text-amber-200">
          Modo solo lectura activo. Puede consultar correo y archivos; el envío y la gestión están deshabilitados.
        </div>
      )}
      {actionMessage && (
        <div className="border-b bg-primary/5 px-4 py-2 text-sm text-foreground">{actionMessage}</div>
      )}
      {error && <ErrorBanner message={error} hint={permissionHint} onRetry={clearError} />}

      {/* Outlook */}
      {app === "outlook" && (
        <div className="grid flex-1 min-h-0 lg:grid-cols-[200px_320px_1fr]">
          <aside className="border-b border-r bg-muted/20 p-3 lg:border-b-0">
            <Button className="mb-3 w-full" size="sm" onClick={() => openCompose("new")} disabled={!canWrite}>
              <Plus className="mr-2 h-4 w-4" /> Nuevo
            </Button>
            {M365_MAIL_FOLDERS.map((f) => (
              <button
                key={f.id}
                type="button"
                onClick={() => {
                  setFolder(f.id);
                  setSelectedId(null);
                }}
                className={cn(
                  "mb-0.5 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm",
                  folder === f.id ? "bg-primary/10 font-medium text-primary" : "hover:bg-muted",
                )}
              >
                {f.id === "sent" ? <Send className="h-4 w-4" /> : f.id === "archive" ? <Archive className="h-4 w-4" /> : f.id === "deleted" ? <Trash2 className="h-4 w-4" /> : <Inbox className="h-4 w-4" />}
                {f.label}
              </button>
            ))}
          </aside>
          <div className="flex min-h-0 flex-col border-b border-r lg:border-b-0">
            <div className="flex gap-2 border-b p-2">
              <Input
                placeholder="Buscar correos…"
                value={mailSearch}
                onChange={(e) => setMailSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void loadMail()}
                className="h-9"
              />
              <Button size="icon" variant="secondary" onClick={() => void loadMail()}>
                <Search className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex-1 overflow-y-auto">
              {loading && <div className="space-y-2 p-3">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-16 w-full" />)}</div>}
              {!loading && messages.length === 0 && <EmptyState title="Sin correos" subtitle="Esta carpeta está vacía." />}
              {messages.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => setSelectedId(m.id)}
                  className={cn(
                    "block w-full border-b px-3 py-3 text-left hover:bg-muted/50",
                    selectedId === m.id && "bg-primary/5",
                    !m.is_read && "font-semibold",
                  )}
                >
                  <p className="truncate text-xs text-muted-foreground">{m.sender_name || m.sender}</p>
                  <p className="truncate text-sm">{m.subject || "(sin asunto)"}</p>
                  <p className="truncate text-xs text-muted-foreground">{m.preview}</p>
                </button>
              ))}
            </div>
          </div>
          <div className="min-h-0 overflow-y-auto">
            {!detail && <EmptyState title="Seleccione un correo" />}
            {detail && (
              <div className="p-4">
                <h2 className="text-lg font-semibold">{detail.subject}</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  De: {detail.sender_name || detail.sender} · {formatDate(detail.received_at)}
                </p>
                {detail.to_recipients.length > 0 && (
                  <p className="text-xs text-muted-foreground">Para: {detail.to_recipients.join(", ")}</p>
                )}
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button size="sm" variant="secondary" disabled={!canWrite} onClick={() => openCompose("reply", detail)}>
                    Responder
                  </Button>
                  <Button size="sm" variant="secondary" disabled={!canWrite} onClick={() => openCompose("replyAll", detail)}>
                    Responder a todos
                  </Button>
                  <Button size="sm" variant="outline" disabled={!canWrite} onClick={() => openCompose("forward", detail)}>
                    Reenviar
                  </Button>
                  <Button size="sm" variant="ghost" disabled={!canWrite} onClick={() => void moveMessage("archive")}>
                    Archivar
                  </Button>
                  <Button size="sm" variant="ghost" disabled={!canWrite} onClick={() => void moveMessage("deleted")}>
                    Eliminar
                  </Button>
                </div>
                {detail.attachments && detail.attachments.length > 0 && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {detail.attachments.map((a) => (
                      <button
                        key={a.id ?? a.name}
                        type="button"
                        className="inline-flex items-center gap-1 rounded-full bg-muted px-3 py-1 text-xs hover:bg-muted/80"
                        onClick={() => a.id && void downloadAttachment(detail.id, a.id, a.name)}
                      >
                        <Paperclip className="h-3 w-3" />
                        {a.name} {a.size_bytes ? `(${formatBytes(a.size_bytes)})` : ""}
                      </button>
                    ))}
                  </div>
                )}
                <div
                  className="prose prose-sm mt-4 max-w-none dark:prose-invert"
                  dangerouslySetInnerHTML={{
                    __html: detail.body_html || `<p>${detail.body_text || detail.preview}</p>`,
                  }}
                />
                <M365MailAiPanel
                  messageId={detail.id}
                  accountId={accountId}
                  onAction={(id) => {
                    if (id === "search_related") {
                      setApp("search");
                      setSearchQ(detail.subject ?? "");
                    }
                  }}
                />
              </div>
            )}
          </div>
        </div>
      )}

      {/* Calendar */}
      {app === "calendar" && (
        <div className="flex flex-1 flex-col p-4">
          <div className="mb-4 flex flex-wrap items-center gap-2">
            {(["month", "week", "day", "agenda"] as CalendarViewMode[]).map((v) => (
              <Button key={v} size="sm" variant={calView === v ? "default" : "outline"} onClick={() => setCalView(v)}>
                {v === "month" ? "Mes" : v === "week" ? "Semana" : v === "day" ? "Día" : "Agenda"}
              </Button>
            ))}
            <Button size="sm" disabled={!canWrite} onClick={() => { setCalendarEditEvent(null); setCalendarModalOpen(true); }}>
              <Plus className="mr-1 h-4 w-4" /> Nuevo evento
            </Button>
            <div className="ml-auto flex items-center gap-2">
              <Button size="icon" variant="ghost" onClick={() => setCalMonth(new Date(calMonth.getFullYear(), calMonth.getMonth() - 1, 1))}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="text-sm font-medium capitalize">
                {calMonth.toLocaleDateString("es-DO", { month: "long", year: "numeric" })}
              </span>
              <Button size="icon" variant="ghost" onClick={() => setCalMonth(new Date(calMonth.getFullYear(), calMonth.getMonth() + 1, 1))}>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
          {calView === "month" && (
            <div className="grid flex-1 grid-cols-7 gap-px rounded-xl border bg-border text-sm">
              {["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"].map((d) => (
                <div key={d} className="bg-muted/40 p-2 text-center text-xs font-medium text-muted-foreground">
                  {d}
                </div>
              ))}
              {monthGrid.map((day, i) => {
                const key = day.toDateString();
                const dayEvents = eventsByDay[key] ?? [];
                const inMonth = day.getMonth() === calMonth.getMonth();
                return (
                  <div
                    key={`${key}-${i}`}
                    className={cn("min-h-[80px] bg-background p-1.5", !inMonth && "bg-muted/10 text-muted-foreground")}
                  >
                    <span className="text-xs font-medium">{day.getDate()}</span>
                    {dayEvents.slice(0, 2).map((ev, j) => (
                      <button
                        key={j}
                        type="button"
                        className="mt-0.5 block w-full truncate rounded bg-[#107C10]/15 px-1 text-left text-[10px] text-[#107C10] hover:bg-[#107C10]/25"
                        onClick={() => {
                          setCalendarEditEvent(ev);
                          setCalendarModalOpen(true);
                        }}
                      >
                        {String(ev.subject ?? "Evento")}
                      </button>
                    ))}
                  </div>
                );
              })}
            </div>
          )}
          {calLoading && <div className="space-y-2">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-12 w-full" />)}</div>}
          {calView === "week" && !calLoading && (
            <div className="grid flex-1 grid-cols-7 gap-px rounded-xl border bg-border text-sm">
              {weekDays(calFocus).map((day) => {
                const key = day.toDateString();
                const dayEvents = eventsByDay[key] ?? [];
                return (
                  <div key={key} className="min-h-[200px] bg-background p-2">
                    <p className="text-xs font-semibold text-muted-foreground">
                      {day.toLocaleDateString("es-DO", { weekday: "short", day: "numeric" })}
                    </p>
                    {dayEvents.map((ev, j) => (
                      <div key={j} className="mt-1 rounded bg-[#107C10]/15 px-1.5 py-1 text-[11px]">
                        <p className="font-medium truncate">{String(ev.subject ?? "Evento")}</p>
                        <p className="text-muted-foreground">{formatDate(ev.start as string)}</p>
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>
          )}
          {calView === "day" && !calLoading && (
            <div className="rounded-xl border">
              <p className="border-b px-4 py-2 font-medium capitalize">
                {calFocus.toLocaleDateString("es-DO", { weekday: "long", day: "numeric", month: "long" })}
              </p>
              <div className="divide-y">
                {dayHours().map((hour) => {
                  const slotEvents = events.filter((ev) => {
                    const start = ev.start as string | undefined;
                    if (!start) return false;
                    const d = new Date(start);
                    return d.toDateString() === calFocus.toDateString() && d.getHours() === hour;
                  });
                  return (
                    <div key={hour} className="flex min-h-[48px] gap-3 px-4 py-2 text-sm">
                      <span className="w-12 shrink-0 text-xs text-muted-foreground">{hour}:00</span>
                      <div className="flex-1 space-y-1">
                        {slotEvents.map((ev, j) => (
                          <div key={j} className="rounded-lg bg-[#107C10]/10 px-2 py-1">
                            {String(ev.subject ?? "Evento")}
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
          {calView === "agenda" && !calLoading && (
            <div className="divide-y rounded-xl border">
              {events.length === 0 && <EmptyState title="Sin eventos" />}
              {events.map((ev, i) => (
                <div key={String(ev.id ?? i)} className="flex gap-4 p-4">
                  <Calendar className="mt-0.5 h-5 w-5 shrink-0 text-[#107C10]" />
                  <div>
                    <p className="font-medium">{String(ev.subject ?? "Evento")}</p>
                    <p className="text-sm text-muted-foreground">
                      {formatDate(ev.start as string)}
                      {ev.location ? ` · ${String(ev.location)}` : ""}
                    </p>
                    {ev.online_meeting_url != null ? (
                      <a href={String(ev.online_meeting_url)} target="_blank" rel="noreferrer" className="text-xs text-primary">
                        Unirse a Teams
                      </a>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Teams */}
      {app === "teams" && (
        <div className="grid flex-1 min-h-0 lg:grid-cols-[200px_200px_1fr]">
          <div className="border-r overflow-y-auto">
            {teamsLoading && [1, 2, 3].map((i) => <Skeleton key={i} className="m-2 h-12" />)}
            {teams.map((t) => (
              <button
                key={String(t.id)}
                type="button"
                onClick={() => {
                  setSelectedTeam(String(t.id));
                  setSelectedChannel(null);
                }}
                className={cn(
                  "block w-full border-b px-3 py-3 text-left text-sm hover:bg-muted/50",
                  selectedTeam === t.id && "bg-primary/5 font-medium",
                )}
              >
                <Users className="mb-1 h-4 w-4 text-[#6264A7]" />
                {String(t.display_name ?? t.name ?? "Equipo")}
              </button>
            ))}
          </div>
          <div className="border-r overflow-y-auto">
            {channels.map((c) => (
              <button
                key={String(c.id)}
                type="button"
                onClick={() => setSelectedChannel(String(c.id))}
                className={cn(
                  "block w-full border-b px-3 py-2 text-left text-sm hover:bg-muted/50",
                  selectedChannel === c.id && "bg-primary/5",
                )}
              >
                {String(c.display_name ?? "Canal")}
              </button>
            ))}
          </div>
          <div className="overflow-y-auto p-4">
            {teamMessages.length === 0 && <EmptyState title="Seleccione un canal" subtitle="Los mensajes aparecerán aquí." />}
            {teamMessages.map((m, i) => (
              <div key={String(m.id ?? i)} className="mb-4 rounded-xl border p-3">
                <p className="text-xs font-medium">{String(m.from ?? "Usuario")}</p>
                <p className="mt-1 text-sm" dangerouslySetInnerHTML={{ __html: String(m.preview ?? "") }} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* OneDrive */}
      {app === "onedrive" && (
        <div className="flex flex-1 flex-col p-4">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            {folderStack.map((f, i) => (
              <button
                key={f.id}
                type="button"
                className="text-sm text-primary hover:underline"
                onClick={() => setFolderStack(folderStack.slice(0, i + 1))}
              >
                {f.name}
                {i < folderStack.length - 1 && " /"}
              </button>
            ))}
            <Input
              className="ml-auto max-w-xs"
              placeholder="Buscar archivos…"
              value={fileSearch}
              onChange={(e) => setFileSearch(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void loadOneDrive()}
            />
            {canWrite && (
              <label className="cursor-pointer rounded-lg border px-3 py-1.5 text-sm hover:bg-muted">
                Subir
                <input
                  type="file"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) void handleUploadOneDrive(f);
                  }}
                />
              </label>
            )}
          </div>
          <div className="divide-y rounded-xl border">
            {filesLoading && [1, 2, 3].map((i) => <Skeleton key={i} className="m-2 h-12" />)}
            {!filesLoading && driveItems.length === 0 && <EmptyState title="Carpeta vacía" />}
            {driveItems.map((item) => (
              <div key={item.id} className="flex items-center gap-3 px-4 py-3 hover:bg-muted/30">
                {item.is_folder ? (
                  <Folder className="h-5 w-5 text-amber-500" />
                ) : (
                  <File className="h-5 w-5 text-primary" />
                )}
                <button
                  type="button"
                  className="flex-1 text-left"
                  onClick={() => {
                    if (item.is_folder && item.id) {
                      setFolderStack([...folderStack, { id: item.id, name: item.name ?? "Carpeta" }]);
                    }
                  }}
                >
                  <p className="font-medium">{item.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatDate(item.modified_at)} · {formatBytes(item.size_bytes)}
                    {item.owner_name ? ` · ${item.owner_name}` : ""}
                  </p>
                </button>
                {!item.is_folder && (
                  <DocumentViewLink
                    graphItemId={item.id}
                    webUrl={item.web_url ?? item.download_url}
                    label="Ver documento"
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Documentos unificados */}
      {app === "documents" && (
        <div className="flex flex-1 flex-col p-4">
          <div className="mb-3 flex gap-2">
            <Input
              className="max-w-md"
              placeholder="Buscar documentos en OneDrive y SharePoint…"
              value={fileSearch}
              onChange={(e) => setFileSearch(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void loadDocuments()}
            />
            <Button variant="secondary" onClick={() => void loadDocuments()}>
              <Search className="h-4 w-4" />
            </Button>
          </div>
          <div className="divide-y rounded-xl border">
            {filesLoading && [1, 2, 3].map((i) => <Skeleton key={i} className="m-2 h-12" />)}
            {!filesLoading && documentItems.length === 0 && <EmptyState title="Sin documentos" subtitle="Busque por nombre o extensión." />}
            {documentItems.map((item) => (
              <div key={item.id} className="flex items-center gap-3 px-4 py-3 hover:bg-muted/30">
                <File className="h-5 w-5 text-[#8764B8]" />
                <div className="flex-1">
                  <p className="font-medium">{item.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {item.source ?? "Microsoft 365"} · {formatDate(item.modified_at)}
                  </p>
                </div>
                {(item.download_url || item.web_url) && (
                  <DocumentViewLink graphItemId={item.id} webUrl={item.web_url ?? item.download_url} label="Ver documento" />
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SharePoint */}
      {app === "sharepoint" && (
        <div className="grid flex-1 lg:grid-cols-[280px_1fr] gap-4 p-4 min-h-0">
          <div className="rounded-xl border overflow-y-auto">
            <p className="border-b px-4 py-2 font-medium">Sitios</p>
            {spSites.map((s) => (
              <button
                key={String(s.id)}
                type="button"
                className={cn(
                  "block w-full border-b px-4 py-3 text-left text-sm hover:bg-muted/30",
                  spSiteName === String(s.name ?? s.display_name) && "bg-primary/5 font-medium",
                )}
                onClick={() => {
                  const name = String(s.name ?? s.display_name ?? "Sitio");
                  setSpSiteName(name);
                  setSpFolderStack([{ id: "root", name }]);
                  apiClient.getM365SharePointDrives(String(s.id), accountId ?? undefined).then((r) => {
                    const drive = r.items[0] as { id?: string; name?: string } | undefined;
                    if (drive?.id) {
                      setSpDriveId(String(drive.id));
                      apiClient
                        .getM365SharePointItems(String(drive.id), { account_id: accountId ?? undefined })
                        .then((items) => setSpDriveItems(items.items as M365DriveItem[]));
                    }
                  });
                }}
              >
                {String(s.name ?? s.display_name ?? "Sitio")}
              </button>
            ))}
          </div>
          <div className="flex flex-col rounded-xl border min-h-0">
            <div className="flex items-center gap-2 border-b px-4 py-2">
              {spFolderStack.map((f, i) => (
                <button
                  key={f.id}
                  type="button"
                  className="text-sm text-primary hover:underline"
                  onClick={() => {
                    setSpFolderStack(spFolderStack.slice(0, i + 1));
                    if (spDriveId && f.id !== "root") {
                      apiClient
                        .getM365SharePointItems(spDriveId, { folder_id: f.id, account_id: accountId ?? undefined })
                        .then((r) => setSpDriveItems(r.items as M365DriveItem[]));
                    } else if (spDriveId) {
                      apiClient
                        .getM365SharePointItems(spDriveId, { account_id: accountId ?? undefined })
                        .then((r) => setSpDriveItems(r.items as M365DriveItem[]));
                    }
                  }}
                >
                  {f.name}
                  {i < spFolderStack.length - 1 && " / "}
                </button>
              ))}
              {canWrite && spDriveId && (
                <label className="ml-auto cursor-pointer rounded-lg border px-2 py-1 text-xs hover:bg-muted">
                  Subir
                  <input
                    type="file"
                    className="hidden"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) void handleUploadSharePoint(f);
                    }}
                  />
                </label>
              )}
            </div>
            <div className="flex-1 overflow-y-auto divide-y">
              {!spDriveId && <EmptyState title="Seleccione un sitio" />}
              {spDriveItems.map((item) => (
                <div key={item.id} className="flex items-center gap-3 px-4 py-3 hover:bg-muted/30">
                  {item.is_folder ? <Folder className="h-5 w-5 text-[#038387]" /> : <File className="h-5 w-5" />}
                  <button
                    type="button"
                    className="flex-1 text-left"
                    onClick={() => {
                      if (item.is_folder && item.id && spDriveId) {
                        setSpFolderStack([...spFolderStack, { id: item.id, name: item.name ?? "Carpeta" }]);
                        apiClient
                          .getM365SharePointItems(spDriveId, { folder_id: item.id, account_id: accountId ?? undefined })
                          .then((r) => setSpDriveItems(r.items as M365DriveItem[]));
                      }
                    }}
                  >
                    <p className="font-medium">{item.name}</p>
                  </button>
                  {!item.is_folder && (
                    <DocumentViewLink
                      graphItemId={item.id}
                      webUrl={item.web_url ?? item.download_url}
                      label="Ver documento"
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Repositorios empresariales */}
      {app === "repositories" && (
        <M365RepositoriesPanel accountId={accountId} connected={connected} />
      )}

      {/* Search */}
      {app === "search" && (
        <div className="flex flex-1 flex-col p-4">
          <div className="mb-4 flex gap-2">
            <Input
              placeholder="Buscar en correo, archivos, contactos, Teams…"
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void runSearch()}
              className="max-w-xl"
            />
            <Button onClick={() => void runSearch()}>
              <Search className="mr-2 h-4 w-4" /> Buscar
            </Button>
          </div>
          {Object.entries(searchGroups).map(([group, items]) => (
            <div key={group} className="mb-6">
              <h3 className="mb-2 text-sm font-semibold capitalize text-primary">{group}</h3>
              <div className="space-y-2">
                {items.map((item, i) => (
                  <div key={i} className="rounded-lg border px-4 py-3 text-sm">
                    {"error" in item ? (
                      <p className="text-destructive">{String(item.error)}</p>
                    ) : (
                      <>
                        <p className="font-medium">
                          {String(item.subject ?? item.display_name ?? item.name ?? item.title ?? "—")}
                        </p>
                        {item.match_reason && (
                          <p className="text-xs text-muted-foreground">{String(item.match_reason)}</p>
                        )}
                      </>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {compose && (
        <ComposeModal
          open
          state={compose}
          onChange={setCompose}
          onClose={() => {
            setCompose(null);
            setComposeFiles([]);
            setCloudAttachments([]);
          }}
          onSend={() => void handleSendMail(false)}
          onSaveDraft={() => void handleSendMail(true)}
          sending={sending}
          readOnly={readOnly}
          files={composeFiles}
          onFilesChange={setComposeFiles}
          onPickCloud={() => setPickerOpen(true)}
          cloudCount={(compose.cloudAttachments ?? cloudAttachments).length}
        />
      )}
      <M365AttachmentPicker
        open={pickerOpen}
        onClose={() => setPickerOpen(false)}
        accountId={accountId}
        onPick={(item) => {
          const next = [...cloudAttachments, item];
          setCloudAttachments(next);
          if (compose) setCompose({ ...compose, cloudAttachments: next.map((a) => ({ name: a.name, onedrive_item_id: a.onedrive_item_id, source_url: a.source_url })) });
        }}
      />
      <M365CalendarEventModal
        open={calendarModalOpen}
        onClose={() => setCalendarModalOpen(false)}
        accountId={accountId}
        readOnly={readOnly}
        initial={
          calendarEditEvent
            ? {
                id: String(calendarEditEvent.id ?? ""),
                subject: String(calendarEditEvent.subject ?? ""),
                start: String(calendarEditEvent.start ?? ""),
                end: String(calendarEditEvent.end ?? ""),
                location: String(calendarEditEvent.location ?? ""),
              }
            : null
        }
        onSaved={() => void loadCalendar()}
      />
    </div>
  );
}
