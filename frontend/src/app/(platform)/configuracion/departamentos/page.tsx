"use client";

import { useEffect, useState } from "react";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { Card, CardContent } from "@/components/ui/card";
import { apiClient } from "@/lib/api";

export default function AdminDepartamentosPage() {
  const [items, setItems] = useState<{ id: string; key: string; name: string; is_active: boolean }[]>([]);

  useEffect(() => {
    apiClient.getAdminDepartments().then((r) => setItems(r.items));
  }, []);

  return (
    <div>
      <AdminPageHeader title="Departamentos" description="Estructura organizacional" />
      <Card>
        <CardContent className="pt-6 space-y-2">
          {items.map((d) => (
            <div key={d.id} className="flex justify-between rounded-lg border p-3 text-sm">
              <span className="font-medium">{d.name}</span>
              <span className="text-muted-foreground">{d.key} · {d.is_active ? "Activo" : "Inactivo"}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
