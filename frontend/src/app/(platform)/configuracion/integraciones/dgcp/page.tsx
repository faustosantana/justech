"use client";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { IntegrationForm } from "@/components/settings/integration-form";

export default function DgcpIntegracionPage() {
  return (
    <div>
      <AdminPageHeader
        title="DGCP Licitaciones"
        description="Fuente de datos, API endpoint y sincronización de procesos"
      />
      <IntegrationForm provider="dgcp" showCompanies={false} />
    </div>
  );
}
