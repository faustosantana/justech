"use client";

import {
  Building2,
  ChevronDown,
  MessageCircle,
  Paperclip,
  RefreshCw,
  Search,
  Send,
  Settings2,
  Sparkles,
  Star,
  Users,
  X,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { CommunicationsDocumentPicker, m365PayloadFor } from "@/components/comunicaciones/communications-document-picker";
import { WhatsappAiAssistantPanel } from "@/components/comunicaciones/whatsapp-ai-assistant-panel";
import { WhatsappSessionAdminModal } from "@/components/comunicaciones/whatsapp-session-admin-modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api";
import type {
  CommunicationsRepositoryItem,
  ConversationFilter,
  WhatsappChat,
  WhatsappMessage,
  WhatsappSession,
} from "@/lib/communications";
import type { M365DocumentItem } from "@/lib/m365-documents";
import { cn } from "@/lib/utils";

const FILTERS: { id: ConversationFilter; label: string }[] = [
  { id: "all", label: "Todos" },
  { id: "unread", label: "No leídos" },
  { id: "favorites", label: "Favoritos" },
  { id: "groups", label: "Grupos" },
  { id: "clients", label: "Clientes" },
  { id: "suppliers", label: "Proveedores" },
];

function formatPhoneDisplay(phone?: string | null) {
  if (!phone) return "";
  const digits = phone.replace(/\D/g, "");
  if (digits.length === 11 && digits.startsWith("1")) {
    return `+1 ${digits.slice(1, 4)} ${digits.slice(4, 7)} ${digits.slice(7)}`;
  }
  if (digits.length >= 10) {
    return `+${digits.slice(0, digits.length - 10)} ${digits.slice(-10, -7)} ${digits.slice(-7, -4)} ${digits.slice(-4)}`.replace(/\+\s/, "+");
  }
  return phone.startsWith("+") ? phone : `+${phone}`;
}

function formatTime(iso?: string | null) {
  if (!iso) return "";
  const d = new Date(iso);
  const now = new Date();
  if (d.toDateString() === now.toDateString()) {
    return d.toLocaleTimeString("es-DO", { hour: "2-digit", minute: "2-digit" });
  }
  return d.toLocaleDateString("es-DO", { day: "2-digit", month: "short" });
}

function statusDot(status: string) {
  if (status === "connected") return "bg-emerald-500";
  if (status === "qr_pending" || status === "connecting") return "bg-amber-500";
  if (status === "error") return "bg-destructive";
  return "bg-muted-foreground/40";
}

function ConversationSkeleton() {
  return (
    <div className="space-y-3 p-3">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="flex gap-3">
          <div className="h-10 w-10 shrink-0 animate-pulse rounded-full bg-muted" />
          <div className="flex-1 space-y-2">
            <div className="h-3 w-2/3 animate-pulse rounded bg-muted" />
            <div className="h-2 w-full animate-pulse rounded bg-muted" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function WhatsappInbox({
  hideSessionManagement = false,
  variant = "default",
}: {
  hideSessionManagement?: boolean;
  variant?: "default" | "kanban";
} = {}) {
  const router = useRouter();
  const [sessions, setSessions] = useState<WhatsappSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [chats, setChats] = useState<WhatsappChat[]>([]);
  const [activeChat, setActiveChat] = useState<WhatsappChat | null>(null);
  const [messages, setMessages] = useState<WhatsappMessage[]>([]);
  const [search, setSearch] = useState("");
  const [convFilter, setConvFilter] = useState<ConversationFilter>("all");
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [showQr, setShowQr] = useState(false);
  const [showAdmin, setShowAdmin] = useState(false);
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const [showDocPicker, setShowDocPicker] = useState(false);
  const [attaching, setAttaching] = useState(false);
  const [showAiMobile, setShowAiMobile] = useState(false);

  const activeSession = useMemo(
    () => sessions.find((s) => s.id === activeSessionId) || null,
    [sessions, activeSessionId],
  );

  const accountLabel = useMemo(() => {
    if (!activeSession) return "Sin cuenta";
    if (activeSession.phone_number) return formatPhoneDisplay(activeSession.phone_number);
    return activeSession.label;
  }, [activeSession]);

  const loadSessions = useCallback(async () => {
    const res = await apiClient.listWhatsappSessions();
    setSessions(res.items);
    if (!activeSessionId && res.items.length > 0) {
      setActiveSessionId(res.items[0].id);
    }
    return res.items;
  }, [activeSessionId]);

  const refreshSession = useCallback(async (id: string) => {
    const s = await apiClient.getWhatsappSession(id);
    setSessions((prev) => prev.map((x) => (x.id === id ? s : x)));
    if (s.connection_status === "qr_pending" && s.qr_image) setShowQr(true);
    if (s.connection_status === "connected") {
      setShowQr(false);
    }
    return s;
  }, []);

  const loadConversations = useCallback(
    async (sessionId: string, withSync = false) => {
      setSyncError(null);
      if (withSync) {
        setSyncing(true);
        try {
          const syncRes = await apiClient.syncWhatsappSession(sessionId);
          if (syncRes.status === "error") {
            setSyncError(syncRes.message || "Error de sincronización");
          }
        } catch {
          setSyncError("No pudimos sincronizar las conversaciones.");
        } finally {
          setSyncing(false);
        }
      }
      const res = await apiClient.listWhatsappConversations({
        sessionId,
        filter: convFilter,
        q: search.trim() || undefined,
      });
      setChats(res.items);
    },
    [convFilter, search],
  );

  const loadMessages = useCallback(async (chatId: string) => {
    const res = await apiClient.listWhatsappConversationMessages(chatId, true);
    setMessages(res.items);
  }, []);

  useEffect(() => {
    loadSessions().finally(() => setLoading(false));
  }, [loadSessions]);

  useEffect(() => {
    if (!activeSessionId) return;
    loadConversations(activeSessionId, false);
    const poll = setInterval(() => refreshSession(activeSessionId), 5000);
    return () => clearInterval(poll);
  }, [activeSessionId, convFilter, search, loadConversations, refreshSession]);

  useEffect(() => {
    if (activeChat) loadMessages(activeChat.id);
  }, [activeChat, loadMessages]);

  const handleConnect = () => {
    if (hideSessionManagement) {
      router.push("/apps/comunicaciones/canales");
      return;
    }
    setShowAdmin(true);
  };

  const kanbanColumns = useMemo(() => {
    if (variant !== "kanban") return null;
    return [
      { id: "unread", label: "Sin responder", items: chats.filter((c) => c.unread_count > 0) },
      { id: "clients", label: "Clientes", items: chats.filter((c) => c.contact_type === "client" || c.related_company_name) },
      { id: "suppliers", label: "Proveedores", items: chats.filter((c) => c.contact_type === "supplier") },
      { id: "other", label: "Otros", items: chats.filter((c) => !c.unread_count && c.contact_type !== "client" && c.contact_type !== "supplier" && !c.related_company_name) },
    ];
  }, [variant, chats]);

  const handleSend = async () => {
    if (!activeChat || !draft.trim()) return;
    setSending(true);
    try {
      await apiClient.sendWhatsappConversationMessage(activeChat.id, draft.trim());
      setDraft("");
      await loadMessages(activeChat.id);
      if (activeSessionId) await loadConversations(activeSessionId);
    } finally {
      setSending(false);
    }
  };

  const handleAttachDocument = async (item: CommunicationsRepositoryItem, caption: string) => {
    if (!activeSessionId || !activeChat) return;
    setAttaching(true);
    try {
      const res = await apiClient.whatsappAttachDocument(activeSessionId, activeChat.remote_jid, {
        source: item.source,
        item_id: item.id,
        caption: caption.trim() || undefined,
      });
      if (!res.ok) window.alert(res.message);
      else {
        setShowDocPicker(false);
        await loadMessages(activeChat.id);
      }
    } finally {
      setAttaching(false);
    }
  };

  const handleAttachM365 = async (item: M365DocumentItem, caption: string) => {
    if (!activeSessionId || !activeChat) return;
    setAttaching(true);
    try {
      const res = await apiClient.whatsappAttachM365Document(activeSessionId, activeChat.remote_jid, {
        ...m365PayloadFor(item),
        caption: caption.trim() || undefined,
      });
      if (!res.ok) window.alert(res.message);
      else {
        setShowDocPicker(false);
        await loadMessages(activeChat.id);
      }
    } finally {
      setAttaching(false);
    }
  };

  const toggleFavorite = async (chat: WhatsappChat, e: React.MouseEvent) => {
    e.stopPropagation();
    await apiClient.toggleWhatsappFavorite(chat.id, !chat.is_favorite);
    if (activeSessionId) await loadConversations(activeSessionId);
  };

  if (loading) {
    return (
      <div className="flex h-[calc(100vh-10rem)] items-center justify-center rounded-2xl border">
        <p className="text-muted-foreground">Cargando comunicaciones…</p>
      </div>
    );
  }

  if (variant === "kanban" && kanbanColumns) {
    return (
      <div className="grid gap-4 lg:grid-cols-4">
        {kanbanColumns.map((col) => (
          <div key={col.id} className="rounded-xl border bg-muted/20 p-3">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {col.label} ({col.items.length})
            </p>
            <div className="max-h-[65vh] space-y-2 overflow-y-auto">
              {col.items.map((chat) => (
                <div key={chat.id} className="rounded-lg border bg-card p-3 text-sm">
                  <p className="truncate font-medium">{chat.name || chat.phone_number || chat.remote_jid}</p>
                  <p className="mt-1 truncate text-xs text-muted-foreground">{chat.last_message_preview || "—"}</p>
                </div>
              ))}
              {!col.items.length && <p className="text-xs text-muted-foreground">Vacío</p>}
            </div>
          </div>
        ))}
      </div>
    );
  }

  const noAccount = sessions.length === 0 || !activeSession;
  const notConnected = activeSession && activeSession.connection_status !== "connected";

  return (
    <div className="flex h-[calc(100vh-10rem)] overflow-hidden rounded-2xl border bg-background shadow-sm">
      {/* Columna izquierda */}
      <div className="flex w-[min(100%,320px)] shrink-0 flex-col border-r bg-muted/10">
        <div className="space-y-3 border-b p-3">
          <div className="relative">
            <button
              type="button"
              className="flex w-full items-center justify-between rounded-xl border bg-card px-3 py-2 text-left text-sm"
              onClick={() => setAccountMenuOpen((v) => !v)}
            >
              <div className="min-w-0">
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Cuenta activa</p>
                <p className="truncate font-medium">{accountLabel}</p>
              </div>
              <div className="flex items-center gap-2">
                {activeSession && (
                  <span className={cn("h-2 w-2 rounded-full", statusDot(activeSession.connection_status))} />
                )}
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              </div>
            </button>
            {accountMenuOpen && (
              <div className="absolute left-0 right-0 z-20 mt-1 rounded-xl border bg-card py-1 shadow-lg">
                {sessions.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    className="flex w-full px-3 py-2 text-left text-sm hover:bg-muted/50"
                    onClick={() => {
                      setActiveSessionId(s.id);
                      setAccountMenuOpen(false);
                      setActiveChat(null);
                    }}
                  >
                    {s.phone_number ? formatPhoneDisplay(s.phone_number) : s.label}
                  </button>
                ))}
                {!hideSessionManagement && (
                  <>
                    <button
                      type="button"
                      className="w-full border-t px-3 py-2 text-left text-sm text-emerald-700 hover:bg-muted/50"
                      onClick={() => {
                        setAccountMenuOpen(false);
                        setShowAdmin(true);
                      }}
                    >
                      + Agregar cuenta
                    </button>
                    <button
                      type="button"
                      className="w-full px-3 py-2 text-left text-sm hover:bg-muted/50"
                      onClick={() => {
                        setAccountMenuOpen(false);
                        setShowAdmin(true);
                      }}
                    >
                      Administrar sesiones
                    </button>
                  </>
                )}
                {hideSessionManagement && (
                  <Link
                    href="/apps/comunicaciones/canales"
                    className="block w-full border-t px-3 py-2 text-left text-sm text-emerald-700 hover:bg-muted/50"
                    onClick={() => setAccountMenuOpen(false)}
                  >
                    Gestionar canales →
                  </Link>
                )}
              </div>
            )}
          </div>

          {!hideSessionManagement && (
            <Button variant="outline" size="sm" className="w-full text-xs" onClick={() => setShowAdmin(true)}>
              <Settings2 className="mr-2 h-3.5 w-3.5" />
              Administrar sesiones
            </Button>
          )}

          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Buscar conversación…"
              className="h-9 pl-8 text-sm"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && activeSessionId) loadConversations(activeSessionId);
              }}
            />
          </div>

          <div className="flex flex-wrap gap-1">
            {FILTERS.map((f) => (
              <button
                key={f.id}
                type="button"
                onClick={() => setConvFilter(f.id)}
                className={cn(
                  "rounded-full px-2.5 py-1 text-[11px] font-medium transition",
                  convFilter === f.id ? "bg-emerald-600 text-white" : "bg-muted/80 text-muted-foreground hover:bg-muted",
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {noAccount ? (
            <div className="flex flex-col items-center gap-3 px-4 py-16 text-center">
              <MessageCircle className="h-10 w-10 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">Conecta una cuenta de WhatsApp para comenzar.</p>
              <Button className="bg-emerald-600 hover:bg-emerald-700" onClick={handleConnect}>
                Conectar WhatsApp
              </Button>
            </div>
          ) : syncing ? (
            <div className="px-4 py-8 text-center">
              <RefreshCw className="mx-auto mb-2 h-5 w-5 animate-spin text-emerald-600" />
              <p className="text-sm text-muted-foreground">Estamos sincronizando tus conversaciones…</p>
            </div>
          ) : syncError ? (
            <div className="px-4 py-8 text-center text-sm">
              <p className="text-destructive">{syncError}</p>
              <div className="mt-3 flex justify-center gap-2">
                <Button size="sm" variant="outline" onClick={() => activeSessionId && loadConversations(activeSessionId, true)}>
                  Reintentar
                </Button>
              </div>
            </div>
          ) : notConnected ? (
            <div className="px-4 py-12 text-center text-sm text-muted-foreground">
              {activeSession?.connection_status === "qr_pending"
                ? "Escanea el código QR para conectar."
                : "Conecta esta cuenta para ver conversaciones."}
              <Button size="sm" className="mt-3" variant="outline" onClick={() => activeSession && setShowQr(true)}>
                Ver QR
              </Button>
            </div>
          ) : chats.length === 0 ? (
            <ConversationSkeleton />
          ) : (
            chats.map((chat) => (
              <button
                key={chat.id}
                type="button"
                onClick={() => setActiveChat(chat)}
                className={cn(
                  "flex w-full gap-3 border-b border-border/40 px-3 py-3 text-left transition hover:bg-muted/40",
                  activeChat?.id === chat.id && "bg-emerald-500/8",
                )}
              >
                <div className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-emerald-600/15 text-emerald-700">
                  {chat.is_group ? <Users className="h-5 w-5" /> : <MessageCircle className="h-5 w-5" />}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-1">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{chat.name || formatPhoneDisplay(chat.phone_number) || chat.remote_jid.split("@")[0]}</p>
                      {!chat.is_group && chat.name && chat.phone_number && (
                        <p className="truncate text-[11px] text-muted-foreground">{formatPhoneDisplay(chat.phone_number)}</p>
                      )}
                      {chat.is_group && chat.related_company_name && (
                        <p className="truncate text-[11px] text-muted-foreground">Grupo · {chat.related_company_name}</p>
                      )}
                    </div>
                    <span className="shrink-0 text-[10px] text-muted-foreground">{formatTime(chat.last_message_at)}</span>
                  </div>
                  <p className="truncate text-xs text-muted-foreground">{chat.last_message_preview || "—"}</p>
                  <div className="mt-1 flex items-center gap-1">
                    {chat.related_company_name && (
                      <span className="inline-flex items-center gap-0.5 rounded-full bg-sky-500/10 px-1.5 py-0.5 text-[9px] text-sky-700">
                        <Building2 className="h-2.5 w-2.5" />
                        {chat.related_company_name}
                      </span>
                    )}
                    {chat.ai_classification_label && (
                      <span className="rounded-full bg-muted px-1.5 py-0.5 text-[9px]">{chat.ai_classification_label}</span>
                    )}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <button type="button" onClick={(e) => toggleFavorite(chat, e)}>
                    <Star className={cn("h-3.5 w-3.5", chat.is_favorite ? "fill-amber-400 text-amber-500" : "text-muted-foreground/40")} />
                  </button>
                  {chat.unread_count > 0 && (
                    <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-emerald-600 px-1 text-[10px] font-bold text-white">
                      {chat.unread_count}
                    </span>
                  )}
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Columna central — chat */}
      <div className="flex min-w-0 flex-1 flex-col">
        {!activeChat ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-2 text-center text-muted-foreground">
            <MessageCircle className="h-12 w-12 opacity-30" />
            <p className="text-sm">Selecciona una conversación para comenzar.</p>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-3 border-b px-4 py-3">
              <div className="min-w-0 flex-1">
                <p className="truncate font-semibold">{activeChat.name || formatPhoneDisplay(activeChat.phone_number)}</p>
                <p className="truncate text-xs text-muted-foreground">
                  {activeChat.is_group ? "Grupo" : formatPhoneDisplay(activeChat.phone_number)}
                  {activeChat.ai_classification_label ? ` · ${activeChat.ai_classification_label}` : ""}
                </p>
              </div>
              <Button size="icon" variant="ghost" className="lg:hidden" onClick={() => setShowAiMobile(true)}>
                <Sparkles className="h-4 w-4" />
              </Button>
              <Button size="icon" variant="ghost" onClick={() => loadMessages(activeChat.id)}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>

            <div className="flex-1 space-y-2 overflow-y-auto p-4">
              {messages.map((m) => (
                <div key={m.id} className={cn("flex", m.from_me ? "justify-end" : "justify-start")}>
                  <div
                    className={cn(
                      "max-w-[78%] rounded-2xl px-3 py-2 text-sm shadow-sm",
                      m.from_me ? "rounded-br-md bg-emerald-600 text-white" : "rounded-bl-md border bg-card",
                    )}
                  >
                    {m.media_type && !m.body && <span className="text-xs opacity-80">[{m.media_type}]</span>}
                    {m.body}
                    <div className={cn("mt-1 text-[10px]", m.from_me ? "text-emerald-100" : "text-muted-foreground")}>
                      {formatTime(m.created_at)}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="border-t p-3">
              <div className="flex gap-2">
                <Button
                  size="icon"
                  variant="outline"
                  disabled={activeSession?.connection_status !== "connected"}
                  onClick={() => setShowDocPicker(true)}
                >
                  <Paperclip className="h-4 w-4" />
                </Button>
                <Input
                  placeholder="Escribe un mensaje…"
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), handleSend())}
                  disabled={activeSession?.connection_status !== "connected"}
                />
                <Button
                  size="icon"
                  className="bg-emerald-600 hover:bg-emerald-700"
                  disabled={sending || !draft.trim()}
                  onClick={handleSend}
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Columna derecha — CRM + IA (desktop) */}
      <div className="hidden w-[min(100%,340px)] shrink-0 flex-col border-l lg:flex">
        <div className="border-b p-4">
          <h4 className="text-sm font-semibold">Contacto</h4>
          {activeChat ? (
            <div className="mt-2 space-y-1 text-sm">
              <p className="font-medium">{activeChat.name || "Sin nombre"}</p>
              <p className="text-xs text-muted-foreground">{formatPhoneDisplay(activeChat.phone_number)}</p>
              {activeChat.related_company_name && (
                <p className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Building2 className="h-3 w-3" /> {activeChat.related_company_name}
                </p>
              )}
            </div>
          ) : (
            <p className="mt-2 text-xs text-muted-foreground">—</p>
          )}
        </div>
        <div className="flex-1 overflow-hidden">
          <WhatsappAiAssistantPanel
            sessionId={activeSessionId}
            chat={activeChat}
            onUseReply={setDraft}
          />
        </div>
      </div>

      {/* Panel IA móvil */}
      {showAiMobile && (
        <div className="fixed inset-0 z-40 bg-black/40 lg:hidden" onClick={() => setShowAiMobile(false)}>
          <div
            className="absolute bottom-0 left-0 right-0 max-h-[85vh] rounded-t-2xl bg-background"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-end p-2">
              <Button size="icon" variant="ghost" onClick={() => setShowAiMobile(false)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
            <WhatsappAiAssistantPanel sessionId={activeSessionId} chat={activeChat} onUseReply={setDraft} />
          </div>
        </div>
      )}

      {!hideSessionManagement && (
        <WhatsappSessionAdminModal
          open={showAdmin}
          onClose={() => setShowAdmin(false)}
          sessions={sessions}
          onRefresh={async () => {
            await loadSessions();
          }}
          onSelectSession={(id) => setActiveSessionId(id)}
          onShowQr={(s) => {
            setShowQr(true);
            setSessions((prev) => prev.map((x) => (x.id === s.id ? s : x)));
          }}
        />
      )}

      <CommunicationsDocumentPicker
        open={showDocPicker}
        onClose={() => setShowDocPicker(false)}
        onAttach={handleAttachDocument}
        onAttachM365={handleAttachM365}
        attaching={attaching}
      />

      {showQr && activeSession?.qr_image && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-sm rounded-2xl bg-card p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="font-semibold">Vincular WhatsApp Web</h3>
              <Button size="icon" variant="ghost" onClick={() => setShowQr(false)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
            <p className="mb-4 text-sm text-muted-foreground">
              WhatsApp → Dispositivos vinculados → Vincular dispositivo
            </p>
            <img src={activeSession.qr_image} alt="QR WhatsApp" className="mx-auto rounded-lg border" />
            <Button className="mt-4 w-full" variant="outline" onClick={() => activeSessionId && refreshSession(activeSessionId)}>
              <RefreshCw className="mr-2 h-4 w-4" /> Actualizar estado
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
