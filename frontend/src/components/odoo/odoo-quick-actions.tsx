"use client";

import { useState } from "react";
import { FileText, ListTodo, Plus, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api";
import type { OdooPermissionsSummary } from "@/lib/odoo";

type Props = {
  permissions: OdooPermissionsSummary | null | undefined;
  readOnly: boolean;
  connected: boolean;
  onSuccess?: (msg: string) => void;
};

export function OdooQuickActions({ permissions, readOnly, connected, onSuccess }: Props) {
  const [partnerId, setPartnerId] = useState("");
  const [productId, setProductId] = useState("");
  const [qty, setQty] = useState("1");
  const [price, setPrice] = useState("0");
  const [taskName, setTaskName] = useState("");
  const [projectId, setProjectId] = useState("");
  const [loading, setLoading] = useState<"quote" | "task" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canQuote = connected && !readOnly && permissions?.can_create_quotation;
  const canTask = connected && !readOnly && permissions?.can_create_task;

  async function handleCreateQuotation() {
    const pid = Number(partnerId);
    if (!pid) {
      setError("Indique el ID del cliente Odoo.");
      return;
    }
    setLoading("quote");
    setError(null);
    try {
      const res = await apiClient.createOdooQuotation({
        partner_id: pid,
        lines: [
          {
            product_id: productId ? Number(productId) : undefined,
            quantity: Number(qty) || 1,
            unit_price: Number(price) || 0,
            description: productId ? undefined : "Línea manual JAIOS",
          },
        ],
        source: "jaios_ui",
      });
      onSuccess?.(`Cotización ${res.name} creada en Odoo.`);
      if (res.odoo_url) window.open(res.odoo_url, "_blank");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la cotización.");
    } finally {
      setLoading(null);
    }
  }

  async function handleCreateTask() {
    if (!taskName.trim()) {
      setError("Indique el nombre de la tarea.");
      return;
    }
    setLoading("task");
    setError(null);
    try {
      const res = await apiClient.createOdooTask({
        name: taskName.trim(),
        project_id: projectId ? Number(projectId) : undefined,
        partner_id: partnerId ? Number(partnerId) : undefined,
        source: "jaios_ui",
      });
      onSuccess?.(`Tarea «${res.name}» creada en Odoo.`);
      if (res.odoo_url) window.open(res.odoo_url, "_blank");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la tarea.");
    } finally {
      setLoading(null);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Acciones rápidas</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <p className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
            {error}
          </p>
        )}
        {!permissions?.linked && (
          <p className="text-sm text-muted-foreground">Vincule su usuario Odoo para habilitar acciones.</p>
        )}
        {readOnly && connected && (
          <p className="text-sm text-amber-700">
            Modo solo lectura activo. El administrador puede habilitar escritura en Configuración → Integraciones → Odoo.
          </p>
        )}

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-2 rounded-lg border p-3">
            <p className="flex items-center gap-2 text-sm font-medium">
              <FileText className="h-4 w-4" />
              Solicitud de cotización
            </p>
            <input
              className="w-full rounded border px-2 py-1.5 text-sm"
              placeholder="ID cliente Odoo"
              value={partnerId}
              onChange={(e) => setPartnerId(e.target.value)}
            />
            <div className="grid grid-cols-3 gap-2">
              <input className="rounded border px-2 py-1.5 text-sm" placeholder="ID producto" value={productId} onChange={(e) => setProductId(e.target.value)} />
              <input className="rounded border px-2 py-1.5 text-sm" placeholder="Cant." value={qty} onChange={(e) => setQty(e.target.value)} />
              <input className="rounded border px-2 py-1.5 text-sm" placeholder="Precio" value={price} onChange={(e) => setPrice(e.target.value)} />
            </div>
            {canQuote ? (
              <Button size="sm" onClick={handleCreateQuotation} disabled={loading === "quote"}>
                <Plus className="mr-1 h-3.5 w-3.5" />
                {loading === "quote" ? "Creando…" : "Crear borrador"}
              </Button>
            ) : (
              <p className="text-xs text-muted-foreground">
                Su perfil Odoo no tiene permisos para crear cotizaciones.
              </p>
            )}
          </div>

          <div className="space-y-2 rounded-lg border p-3">
            <p className="flex items-center gap-2 text-sm font-medium">
              <ListTodo className="h-4 w-4" />
              Tarea en Odoo
            </p>
            <input
              className="w-full rounded border px-2 py-1.5 text-sm"
              placeholder="Nombre de la tarea"
              value={taskName}
              onChange={(e) => setTaskName(e.target.value)}
            />
            <input
              className="w-full rounded border px-2 py-1.5 text-sm"
              placeholder="ID proyecto (opcional)"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
            />
            {canTask ? (
              <Button size="sm" onClick={handleCreateTask} disabled={loading === "task"}>
                <Plus className="mr-1 h-3.5 w-3.5" />
                {loading === "task" ? "Creando…" : "Crear tarea"}
              </Button>
            ) : (
              <p className="text-xs text-muted-foreground">
                Su perfil Odoo no tiene permisos de proyecto/tareas.
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function OdooPermissionsSyncButton({ onSynced }: { onSynced?: () => void }) {
  const [loading, setLoading] = useState(false);
  return (
    <Button
      variant="outline"
      size="sm"
      disabled={loading}
      onClick={async () => {
        setLoading(true);
        try {
          await apiClient.syncOdooPermissions();
          onSynced?.();
        } finally {
          setLoading(false);
        }
      }}
    >
      <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
      Sincronizar permisos Odoo
    </Button>
  );
}
