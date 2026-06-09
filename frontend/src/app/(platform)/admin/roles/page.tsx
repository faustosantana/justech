"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { AdminNav } from "@/components/admin/admin-nav";
import { Card, CardContent } from "@/components/ui/card";
import { apiClient } from "@/lib/api";

export default function AdminRolesPage() {
  const [roles, setRoles] = useState<{ key: string; label: string; permissions: string[] }[]>([]);

  useEffect(() => {
    apiClient.getAdminRoles().then((r) => setRoles(r.items));
  }, []);

  return (
    <AppShell title="Roles y permisos" description="Matriz de roles operativos del tenant">
      <AdminNav />
      <div className="grid gap-4 md:grid-cols-2">
        {roles.map((r) => (
          <Card key={r.key}>
            <CardContent className="pt-6">
              <p className="font-medium">{r.label}</p>
              <p className="text-xs text-muted-foreground mb-2">{r.key}</p>
              <ul className="text-xs space-y-1 text-muted-foreground">
                {r.permissions.map((p) => <li key={p}>· {p}</li>)}
              </ul>
            </CardContent>
          </Card>
        ))}
      </div>
    </AppShell>
  );
}
