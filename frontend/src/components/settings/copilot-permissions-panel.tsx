"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw, Shield, Users } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";

export function CopilotPermissionsPanel() {
  const [matrix, setMatrix] = useState<Awaited<ReturnType<typeof apiClient.getCopilotPermissionsMatrix>> | null>(null);
  const [users, setUsers] = useState<Awaited<ReturnType<typeof apiClient.getCopilotUsersPermissions>> | null>(null);
  const [audit, setAudit] = useState<Awaited<ReturnType<typeof apiClient.getCopilotAudit>> | null>(null);
  const [loading, setLoading] = useState(false);
  const [deniedOnly, setDeniedOnly] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editUserId, setEditUserId] = useState("");
  const [editCustomers, setEditCustomers] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [m, u, a] = await Promise.all([
        apiClient.getCopilotPermissionsMatrix(),
        apiClient.getCopilotUsersPermissions(),
        apiClient.getCopilotAudit({ limit: 40, denied_only: deniedOnly }),
      ]);
      setMatrix(m);
      setUsers(u);
      setAudit(a);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al cargar permisos");
    } finally {
      setLoading(false);
    }
  }, [deniedOnly]);

  useEffect(() => {
    void load();
  }, [load]);

  const saveAssignments = async () => {
    if (!editUserId.trim()) return;
    setSaving(true);
    try {
      await apiClient.updateCopilotUserAssignments({
        user_id: editUserId.trim(),
        customers: editCustomers.split(",").map((s) => s.trim()).filter(Boolean),
      });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {error && <p className="text-sm text-destructive">{error}</p>}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <Shield className="h-4 w-4" />
              Matriz de permisos por rol
            </CardTitle>
            <p className="text-xs text-muted-foreground mt-1">
              JAIOS valida permisos en backend antes de ejecutar herramientas. Hermes no puede saltarse estas reglas.
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
            <RefreshCw className={`mr-1 h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Actualizar
          </Button>
        </CardHeader>
        <CardContent className="overflow-auto">
          {matrix && (
            <table className="w-full min-w-[640px] text-xs">
              <thead>
                <tr className="border-b">
                  <th className="py-2 text-left font-medium">Rol</th>
                  <th className="py-2 text-left font-medium">Scopes IA</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(matrix.roles).map(([role, scopes]) => (
                  <tr key={role} className="border-b border-border/60">
                    <td className="py-2 pr-4 font-medium capitalize align-top">{role}</td>
                    <td className="py-2 text-muted-foreground">
                      {scopes.map((s) => matrix.scope_labels[s] ?? s).join(" · ")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Users className="h-4 w-4" />
            Usuarios y clientes asignados
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2 sm:grid-cols-3">
            <input
              className="rounded border border-input px-2 py-1.5 text-sm"
              placeholder="UUID usuario"
              value={editUserId}
              onChange={(e) => setEditUserId(e.target.value)}
            />
            <input
              className="rounded border border-input px-2 py-1.5 text-sm sm:col-span-2"
              placeholder="Clientes asignados (separados por coma)"
              value={editCustomers}
              onChange={(e) => setEditCustomers(e.target.value)}
            />
          </div>
          <Button size="sm" onClick={() => void saveAssignments()} disabled={saving}>
            {saving ? "Guardando…" : "Guardar asignación"}
          </Button>

          {users && (
            <div className="overflow-auto rounded-lg border">
              <table className="w-full text-xs">
                <thead className="bg-muted/60">
                  <tr>
                    <th className="px-2 py-1.5 text-left">Usuario</th>
                    <th className="px-2 py-1.5 text-left">Rol</th>
                    <th className="px-2 py-1.5 text-left">Clientes</th>
                    <th className="px-2 py-1.5 text-left">Scopes</th>
                  </tr>
                </thead>
                <tbody>
                  {users.users.map((u) => (
                    <tr key={u.user_id} className="border-t">
                      <td className="px-2 py-1.5">{u.full_name || u.email}</td>
                      <td className="px-2 py-1.5 capitalize">{u.role}</td>
                      <td className="px-2 py-1.5">{u.assigned_customers.join(", ") || "—"}</td>
                      <td className="px-2 py-1.5 text-muted-foreground">{u.scopes.length} scopes</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Auditoría de consultas IA</CardTitle>
          <label className="flex items-center gap-2 text-xs">
            <input
              type="checkbox"
              checked={deniedOnly}
              onChange={(e) => setDeniedOnly(e.target.checked)}
            />
            Solo denegadas
          </label>
        </CardHeader>
        <CardContent className="overflow-auto">
          {audit && audit.entries.length === 0 && (
            <p className="text-sm text-muted-foreground">Sin registros aún.</p>
          )}
          {audit && audit.entries.length > 0 && (
            <table className="w-full min-w-[720px] text-xs">
              <thead>
                <tr className="border-b">
                  <th className="py-1.5 text-left">Fecha</th>
                  <th className="py-1.5 text-left">Pregunta</th>
                  <th className="py-1.5 text-left">Herramienta</th>
                  <th className="py-1.5 text-left">Permiso</th>
                  <th className="py-1.5 text-left">Modelo</th>
                </tr>
              </thead>
              <tbody>
                {audit.entries.map((e) => (
                  <tr key={e.id} className="border-b border-border/50">
                    <td className="py-1.5 pr-2 whitespace-nowrap">
                      {e.created_at ? new Date(e.created_at).toLocaleString("es-DO") : "—"}
                    </td>
                    <td className="py-1.5 max-w-[200px] truncate" title={e.question}>{e.question}</td>
                    <td className="py-1.5">{e.tool || e.intent || "—"}</td>
                    <td className={`py-1.5 ${e.permission_granted ? "text-emerald-600" : "text-amber-600"}`}>
                      {e.permission_granted ? "Concedido" : e.denial_reason || "Denegado"}
                    </td>
                    <td className="py-1.5 text-muted-foreground">{e.model || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
