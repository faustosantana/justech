"use client";

import { useState } from "react";
import { Calendar, Trash2, Video, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api";

export function M365CalendarEventModal({
  open,
  onClose,
  onSaved,
  accountId,
  readOnly,
  initial,
}: {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
  accountId?: string | null;
  readOnly?: boolean;
  initial?: {
    id?: string;
    subject?: string;
    start?: string;
    end?: string;
    location?: string;
    body?: string;
  } | null;
}) {
  const isEdit = Boolean(initial?.id);
  const [subject, setSubject] = useState(initial?.subject ?? "");
  const [start, setStart] = useState(initial?.start?.slice(0, 16) ?? "");
  const [end, setEnd] = useState(initial?.end?.slice(0, 16) ?? "");
  const [location, setLocation] = useState(initial?.location ?? "");
  const [body, setBody] = useState(initial?.body ?? "");
  const [isOnline, setIsOnline] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  async function handleSave() {
    if (readOnly) return;
    setSaving(true);
    setError(null);
    try {
      const payload = {
        subject,
        start: new Date(start).toISOString(),
        end: new Date(end).toISOString(),
        location,
        body,
        is_online: isOnline,
      };
      const result = isEdit && initial?.id
        ? await apiClient.updateM365CalendarEvent(initial.id, payload, accountId ?? undefined)
        : await apiClient.createM365CalendarEvent({ ...payload, attendees: [] }, accountId ?? undefined);
      if (!result.ok) {
        setError(result.message);
        return;
      }
      onSaved();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!initial?.id || readOnly) return;
    const result = await apiClient.deleteM365CalendarEvent(initial.id, accountId ?? undefined);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    onSaved();
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-2xl border bg-background shadow-2xl">
        <div className="flex items-center justify-between border-b px-4 py-3">
          <p className="font-semibold flex items-center gap-2">
            <Calendar className="h-5 w-5 text-[#107C10]" />
            {isEdit ? "Editar evento" : "Nuevo evento"}
          </p>
          <button type="button" onClick={onClose} className="rounded-lg p-1 hover:bg-muted">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="space-y-3 p-4">
          <Input placeholder="Asunto" value={subject} onChange={(e) => setSubject(e.target.value)} />
          <Input type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} />
          <Input type="datetime-local" value={end} onChange={(e) => setEnd(e.target.value)} />
          <Input placeholder="Ubicación" value={location} onChange={(e) => setLocation(e.target.value)} />
          <textarea
            className="min-h-[80px] w-full rounded-lg border p-2 text-sm"
            placeholder="Descripción"
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={isOnline} onChange={(e) => setIsOnline(e.target.checked)} />
            <Video className="h-4 w-4" />
            Reunión de Teams
          </label>
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>
        <div className="flex justify-between border-t px-4 py-3">
          {isEdit && (
            <Button variant="destructive" size="sm" onClick={() => void handleDelete()} disabled={readOnly}>
              <Trash2 className="mr-1 h-4 w-4" />
              Eliminar
            </Button>
          )}
          <div className="ml-auto flex gap-2">
            <Button variant="ghost" onClick={onClose}>
              Cancelar
            </Button>
            <Button onClick={() => void handleSave()} disabled={saving || readOnly}>
              {saving ? "Guardando…" : "Guardar"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
