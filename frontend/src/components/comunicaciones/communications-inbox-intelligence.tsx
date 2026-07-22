"use client";

import {
  CheckCircle2,
  ClipboardList,
  FileText,
  Mail,
  MessageCircle,
  RefreshCw,
  Trash2,
  UserPlus,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import { cn } from "@/lib/utils";

type Observation = Awaited<ReturnType<typeof apiClient.listObservations>>["items"][number];

const STATUS_LABELS: Record<string, string> = {
  detected: "Detectado",
  pending_review: "Pendiente revisión",
  validated: "Validado",
  discarded: "Descartado",
  converted_task: "→ Tarea",
  converted_supplier: "→ Proveedor",
  converted_draft: "→ Borrador",
};

const TYPE_LABELS: Record<string, string> = {
  rfq_request: "Solicitud cotización",
  supplier_mention: "Proveedor mencionado",
  customer_followup: "Seguimiento cliente",
  general: "General",
  unknown: "Sin clasificar",
};

export function CommunicationsInboxIntelligence() {
  const [items, setItems] = useState<Observation[]>([]);
  const [total, setTotal] = useState(0);
  const [selected, setSelected] = useState<Observation | null>(null);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState("");
  const [filterChannel, setFilterChannel] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.listObservations({
        status: filterStatus || undefined,
        channel: filterChannel || undefined,
        limit: 100,
      });
      setItems(res.items);
      setTotal(res.total);
      setSelected((prev) => prev ?? res.items[0] ?? null);
    } finally {
      setLoading(false);
    }
  }, [filterStatus, filterChannel]);

  useEffect(() => {
    void load();
  }, [load]);

  const runAction = async (id: string, action: string) => {
    setActing(`${id}:${action}`);
    try {
      const updated = await apiClient.observationAction(id, action);
      setSelected(updated);
      await load();
    } finally {
      setActing(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <select
          className="rounded-lg border border-input bg-background px-2 py-1.5 text-sm"
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
        >
          <option value="">Todos los estados</option>
          {Object.entries(STATUS_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <select
          className="rounded-lg border border-input bg-background px-2 py-1.5 text-sm"
          value={filterChannel}
          onChange={(e) => setFilterChannel(e.target.value)}
        >
          <option value="">Todos los canales</option>
          <option value="email">Correo</option>
          <option value="whatsapp">WhatsApp</option>
          <option value="outlook">Outlook</option>
        </select>
        <span className="text-sm text-muted-foreground">{total} detecciones</span>
        <Button variant="outline" size="sm" className="ml-auto" onClick={() => void load()} disabled={loading}>
          <RefreshCw className={cn("mr-1 h-3.5 w-3.5", loading && "animate-spin")} />
          Actualizar
        </Button>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <Card>
          <CardContent className="overflow-auto p-0">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-muted/80 text-xs">
                <tr>
                  <th className="px-3 py-2 text-left">Fecha</th>
                  <th className="px-3 py-2 text-left">Canal</th>
                  <th className="px-3 py-2 text-left">Contacto</th>
                  <th className="px-3 py-2 text-left">Tipo</th>
                  <th className="px-3 py-2 text-left">Resumen</th>
                  <th className="px-3 py-2 text-left">Estado</th>
                </tr>
              </thead>
              <tbody>
                {items.map((row) => (
                  <tr
                    key={row.id}
                    className={cn(
                      "cursor-pointer border-t border-border hover:bg-muted/40",
                      selected?.id === row.id && "bg-primary/10",
                    )}
                    onClick={() => setSelected(row)}
                  >
                    <td className="whitespace-nowrap px-3 py-2 text-xs text-muted-foreground">
                      {row.received_at ? new Date(row.received_at).toLocaleString("es-DO") : "—"}
                    </td>
                    <td className="px-3 py-2">
                      {row.channel === "whatsapp" ? (
                        <MessageCircle className="h-4 w-4 text-emerald-600" />
                      ) : (
                        <Mail className="h-4 w-4 text-blue-600" />
                      )}
                    </td>
                    <td className="max-w-[120px] truncate px-3 py-2">{row.customer?.name || row.raw_from || "—"}</td>
                    <td className="px-3 py-2 text-xs">{TYPE_LABELS[row.detected_type] ?? row.detected_type}</td>
                    <td className="max-w-[200px] truncate px-3 py-2" title={row.summary}>{row.summary}</td>
                    <td className="px-3 py-2 text-xs">{STATUS_LABELS[row.status] ?? row.status}</td>
                  </tr>
                ))}
                {!loading && items.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-3 py-8 text-center text-muted-foreground">
                      Sin detecciones. Conecta canales para alimentar la bandeja.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </CardContent>
        </Card>

        {selected && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Detalle</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <p className="text-xs text-muted-foreground">{selected.summary}</p>
              {selected.draft_response && (
                <div className="rounded-lg bg-muted/40 p-2 text-xs">
                  <p className="mb-1 font-medium">Borrador respuesta</p>
                  <p>{selected.draft_response}</p>
                </div>
              )}
              <div className="flex flex-wrap gap-1 pt-2">
                <ActionBtn icon={ClipboardList} label="Tarea" loading={acting} id={selected.id} action="create_task" onRun={runAction} />
                <ActionBtn icon={UserPlus} label="Proveedor" loading={acting} id={selected.id} action="create_supplier" onRun={runAction} />
                <ActionBtn icon={FileText} label="Borrador" loading={acting} id={selected.id} action="create_draft" onRun={runAction} />
                <ActionBtn icon={CheckCircle2} label="Validar" loading={acting} id={selected.id} action="validate" onRun={runAction} />
                <ActionBtn icon={Trash2} label="Descartar" loading={acting} id={selected.id} action="discard" onRun={runAction} variant="outline" />
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

function ActionBtn({
  icon: Icon,
  label,
  loading,
  id,
  action,
  onRun,
  variant = "default",
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  loading: string | null;
  id: string;
  action: string;
  onRun: (id: string, action: string) => void;
  variant?: "default" | "outline";
}) {
  return (
    <Button size="sm" variant={variant} disabled={!!loading} onClick={() => void onRun(id, action)} className="h-7 text-xs">
      <Icon className="mr-1 h-3 w-3" />
      {label}
    </Button>
  );
}
