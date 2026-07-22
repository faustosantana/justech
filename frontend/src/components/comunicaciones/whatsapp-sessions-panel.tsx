"use client";

import { Pencil, Plus, QrCode, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api";
import type { WhatsappSession, WhatsappSessionLimits } from "@/lib/communications";
import { cn } from "@/lib/utils";

function statusLabel(status: string) {
  const map: Record<string, string> = {
    connected: "Conectada",
    qr_pending: "Requiere QR",
    connecting: "Conectando",
    disconnected: "Desconectada",
    reconnecting: "Reconectando",
    error: "Error",
  };
  return map[status] || status;
}

function statusClass(status: string) {
  const map: Record<string, string> = {
    connected: "bg-emerald-500/15 text-emerald-700",
    qr_pending: "bg-amber-500/15 text-amber-800",
    error: "bg-destructive/15 text-destructive",
    disconnected: "bg-muted text-muted-foreground",
  };
  return map[status] || map.disconnected;
}

type Props = {
  onSelectSession?: (id: string) => void;
  onShowQr?: (session: WhatsappSession) => void;
  compact?: boolean;
};

export function WhatsappSessionsPanel({ onSelectSession, onShowQr, compact = false }: Props) {
  const [sessions, setSessions] = useState<WhatsappSession[]>([]);
  const [limits, setLimits] = useState<WhatsappSessionLimits | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editLabel, setEditLabel] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [sess, lim] = await Promise.all([
        apiClient.listWhatsappSessions(),
        apiClient.getWhatsappSessionLimits(),
      ]);
      setSessions(sess.items);
      setLimits(lim);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleCreate = async () => {
    setError(null);
    setBusy(true);
    try {
      const limitsNow = await apiClient.getWhatsappSessionLimits();
      if (!limitsNow.can_create) {
        setError("Has alcanzado el límite de sesiones WhatsApp para tu plan actual.");
        return;
      }
      const s = await apiClient.createWhatsappSession({ label: "WhatsApp", account_type: "personal" });
      await refresh();
      onSelectSession?.(s.id);
      if (s.qr_image) onShowQr?.(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo crear la sesión.");
    } finally {
      setBusy(false);
    }
  };

  const handleRename = async (id: string) => {
    if (!editLabel.trim()) return;
    setBusy(true);
    try {
      await apiClient.updateWhatsappSession(id, editLabel.trim());
      setEditingId(null);
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("¿Eliminar esta sesión de WhatsApp?")) return;
    setBusy(true);
    try {
      await apiClient.deleteWhatsappSession(id);
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const handleDisconnect = async (id: string) => {
    setBusy(true);
    try {
      await apiClient.disconnectWhatsappSession(id);
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const handleSync = async (id: string) => {
    setBusy(true);
    try {
      await apiClient.syncWhatsappSession(id);
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={cn("space-y-4", compact && "space-y-3")}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-sm font-medium">Sesiones WhatsApp Web</p>
          {limits && (
            <p className="text-xs text-muted-foreground">
              Plan {limits.plan}: {limits.active_count}/{limits.limit} sesiones activas
            </p>
          )}
        </div>
        <Button
          size="sm"
          className="bg-emerald-600 hover:bg-emerald-700"
          disabled={busy || loading || (limits != null && !limits.can_create)}
          onClick={() => void handleCreate()}
        >
          <Plus className="mr-2 h-4 w-4" />
          Conectar sesión
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-muted-foreground">Cargando sesiones…</p>
      ) : sessions.length === 0 ? (
        <p className="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground">
          No hay sesiones registradas. Conecta una cuenta para sincronizar contactos y conversaciones.
        </p>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {sessions.map((s) => (
            <div key={s.id} className="rounded-xl border border-border/60 bg-card p-4">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  {editingId === s.id ? (
                    <div className="flex gap-2">
                      <Input
                        value={editLabel}
                        onChange={(e) => setEditLabel(e.target.value)}
                        className="h-8 text-sm"
                      />
                      <Button size="sm" disabled={busy} onClick={() => void handleRename(s.id)}>
                        Guardar
                      </Button>
                    </div>
                  ) : (
                    <p className="font-medium truncate">{s.label}</p>
                  )}
                  <p className="text-xs text-muted-foreground">
                    {s.phone_number || "Sin número"} · {s.push_name || "—"}
                  </p>
                  <span className={cn("mt-1 inline-block rounded-full px-2 py-0.5 text-[10px] font-medium", statusClass(s.connection_status))}>
                    {statusLabel(s.connection_status)}
                  </span>
                  {s.last_error && s.connection_status === "error" && (
                    <p className="mt-1 text-[10px] text-destructive">{s.last_error}</p>
                  )}
                </div>
                <div className="flex shrink-0 flex-wrap gap-1">
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8"
                    title="Renombrar"
                    onClick={() => {
                      setEditingId(s.id);
                      setEditLabel(s.label);
                    }}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  {s.connection_status === "qr_pending" && (
                    <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => onShowQr?.(s)}>
                      <QrCode className="h-3.5 w-3.5" />
                    </Button>
                  )}
                  {s.connection_status === "connected" && (
                    <>
                      <Button size="sm" variant="outline" className="h-8 text-xs" onClick={() => void handleSync(s.id)}>
                        Sincronizar
                      </Button>
                      <Button size="sm" variant="outline" className="h-8 text-xs" onClick={() => void handleDisconnect(s.id)}>
                        Desconectar
                      </Button>
                    </>
                  )}
                  <Button size="icon" variant="ghost" className="h-8 w-8 text-destructive" onClick={() => void handleDelete(s.id)}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
