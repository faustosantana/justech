"use client";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { CompanySelector } from "@/components/layout/company-selector";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function EmpresasAdminPage() {
  return (
    <div>
      <AdminPageHeader
        title="Empresa activa (tenant)"
        description="Contexto multi-empresa y configuración del tenant activo"
      />
      <Card>
        <CardHeader><CardTitle className="text-base">Empresa activa</CardTitle></CardHeader>
        <CardContent>
          <CompanySelector />
        </CardContent>
      </Card>
    </div>
  );
}
