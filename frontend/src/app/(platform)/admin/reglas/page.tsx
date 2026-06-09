"use client";

import { useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { AdminNav } from "@/components/admin/admin-nav";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import type { RoutingRuleAdmin } from "@/lib/admin";

export default function AdminReglasPage() {
  const [rules, setRules] = useState<RoutingRuleAdmin[]>([]);
  const [canMutate, setCanMutate] = useState(false);

  const load = useCallback(async () => {
    const [access, res] = await Promise.all([
      apiClient.getAdminAccess(),
      apiClient.getAdminRoutingRules(),
    ]);
    setCanMutate(access.can_mutate);
    setRules(res.items);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const toggle = async (rule: RoutingRuleAdmin) => {
    if (!canMutate) return;
    await apiClient.updateAdminRoutingRule(rule.id, { is_active: !rule.is_active });
    load();
  };

  return (
    <AppShell title="Reglas de asignación" description="Motor de routing operacional Justech">
      <AdminNav />
      <Card>
        <CardContent className="pt-6 space-y-3">
          {rules.map((r) => (
            <div key={r.id} className="rounded-lg border p-4 space-y-2">
              <div className="flex justify-between items-start gap-4">
                <div>
                  <p className="font-medium">{r.name}</p>
                  <p className="text-xs text-muted-foreground">{r.event_type} · {r.department}</p>
                </div>
                {canMutate && (
                  <Button size="sm" variant="outline" onClick={() => toggle(r)}>
                    {r.is_active ? "Desactivar" : "Activar"}
                  </Button>
                )}
              </div>
              <div className="grid sm:grid-cols-3 gap-2 text-sm">
                <div><span className="text-muted-foreground">Responsable:</span> {r.default_assignee_name ?? "—"}</div>
                <div><span className="text-muted-foreground">Supervisor:</span> {r.default_supervisor_name ?? "—"}</div>
                <div><span className="text-muted-foreground">Prioridad:</span> {r.default_priority}</div>
                <div><span className="text-muted-foreground">SLA:</span> {r.due_hours ? `${r.due_hours}h` : "—"}</div>
                <div><span className="text-muted-foreground">Estado:</span> {r.is_active ? "Activa" : "Inactiva"}</div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </AppShell>
  );
}
