"use client";

import { Pencil, Plus, QrCode, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api";
import type { WhatsappSession, WhatsappSessionLimits } from "@/lib/communications";
import { cn } from "@/lib/utils";

type Props = {
  open: boolean;
  onClose: () => void;
  sessions: WhatsappSession[];
  onRefresh: () => Promise<void>;
  onSelectSession: (id: string) => void;
  onShowQr: (session: WhatsappSession) => void;
};

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

export function WhatsappSessionAdminModal({
  open,
  onClose,
  sessions,
  onRefresh,
  onSelectSession,
  onShowQr,
}: Props) {
  const [limits, setLimits] = useState<WhatsappSessionLimits | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editLabel, setEditLabel] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    apiClient.getWhatsappSessionLimits().then(setLimits).catch(() => {});
  }, [open]);

  const handleCreate = useCallback(async () => {
    setError(null);
    setBusy(true);
    try {
      const limitsNow = await apiClient.getWhatsappSessionLimits();
      if (!limitsNow.can_create) {
        setError("Has alcanzado el límite de sesiones WhatsApp para tu plan actual.");
        return;
      }
      const s = await apiClient.createWhatsappSession({ label: "WhatsApp", account_type: "personal" });
      await onRefresh();
      onSelectSession(s.id);
      if (s.qr_image) onShowQr(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo crear la sesión.");
    } finally {
      setBusy(false);
    }
  }, [onRefresh, onSelectSession, onShowQr]);

  const handleRename = async (id: string) => {
    if (!editLabel.trim()) return;
    setBusy(true);
    try {
      await apiClient.updateWhatsappSession(id, editLabel.trim());
      setEditingId(null);
      await onRefresh();
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("¿Eliminar esta sesión de WhatsApp?")) return;
    setBusy(true);
    try {
      await apiClient.deleteWhatsappSession(id);
      await onRefresh();
    } finally {
      setBusy(false);
    }
  };

  const handleDisconnect = async (id: string) => {
    setBusy(true);
    try {
      await apiClient.disconnectWhatsappSession(id);
      await onRefresh();
    } finally {
      setBusy(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="flex max-h-[90vh] w-full max-w-lg flex-col rounded-2xl bg-card shadow-xl">
        <div className="flex items-center justify-between border-b px-5 py-4">
          <div>
            <h3 className="font-semibold">Administrar sesiones WhatsApp</h3>
            {limits && (
              <p className="text-xs text-muted-foreground">
                Plan {limits.plan}: {limits.active_count}/{limits.limit} sesiones activas
              </p>
            )}
          </div>
          <Button size="icon" variant="ghost" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {error && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              {error}
            </div>
          )}

          {sessions.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No hay sesiones registradas. Agrega una cuenta para comenzar.
            </p>
          ) : (
            sessions.map((s) => (
              <div key={s.id} className="rounded-xl border p-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    {editingId === s.id ? (
                      <div className="flex gap-2">
                        <Input
                          value={editLabel}
                          onChange={(e) => setEditLabel(e.target.value)}
                          className="h-8 text-sm"
                        />
                        <Button size="sm" disabled={busy} onClick={() => handleRename(s.id)}>
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
                    {s.connected_at && (
                      <p className="mt-1 text-[10px] text-muted-foreground">
                        Última conexión: {new Date(s.connected_at).toLocaleString("es-DO")}
                      </p>
                    )}
                    {s.last_error && s.connection_status === "error" && (
                      <p className="mt-1 text-[10px] text-destructive">{s.last_error}</p>
                    )}
                  </div>
                  <div className="flex shrink-0 gap-1">
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
                      <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => onShowQr(s)}>
                        <QrCode className="h-3.5 w-3.5" />
                      </Button>
                    )}
                    {s.connection_status === "connected" && (
                      <Button size="sm" variant="outline" className="h-8 text-xs" onClick={() => handleDisconnect(s.id)}>
                        Desconectar
                      </Button>
                    )}
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-8 w-8 text-destructive"
                      onClick={() => handleDelete(s.id)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="border-t p-4">
          <Button
            className="w-full bg-emerald-600 hover:bg-emerald-700"
            disabled={busy || (limits != null && !limits.can_create)}
            onClick={handleCreate}
          >
            <Plus className="mr-2 h-4 w-4" />
            Agregar sesión (QR)
          </Button>
        </div>
      </div>
    </div>
  );
}
