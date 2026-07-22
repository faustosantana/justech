"use client";

import { useEffect, useState } from "react";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { IntegrationLogs } from "@/components/settings/integration-logs";
import { Card, CardContent } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import type { SettingsAuditEntry } from "@/lib/settings";

export default function AuditoriaPage() {
  const [items, setItems] = useState<SettingsAuditEntry[]>([]);

  useEffect(() => {
    apiClient.getSettingsAuditLog(100).then((r) => setItems(r.items)).catch(() => {});
  }, []);

  return (
    <div>
      <AdminPageHeader title="Logs / Auditoría" description="Cambios de configuración, pruebas y rotación de credenciales" />
      <Card>
        <CardContent className="py-4">
          <IntegrationLogs logs={items} />
        </CardContent>
      </Card>
    </div>
  );
}
