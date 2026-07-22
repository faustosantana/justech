"use client";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function SeguridadPage() {
  return (
    <div>
      <AdminPageHeader
        title="Seguridad"
        description="Políticas de acceso, cifrado de credenciales y auditoría"
      />
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-base">Permisos del Copiloto IA</CardTitle></CardHeader>
          <CardContent className="text-sm text-muted-foreground space-y-2">
            <p>Control de acceso por rol, scope y clasificación de datos sensibles.</p>
            <p>Las consultas comerciales y financieras se validan en backend antes de ejecutar herramientas.</p>
            <a href="/configuracion/seguridad/permisos-ia" className="text-primary underline text-sm">
              Configurar Permisos IA →
            </a>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Vault de credenciales</CardTitle></CardHeader>
          <CardContent className="text-sm text-muted-foreground space-y-2">
            <p>Las API keys y secretos se cifran con Fernet en el backend.</p>
            <p>El frontend solo recibe valores enmascarados (••••••••1234).</p>
            <p>Rotación y auditoría registradas por integración.</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Acceso administrativo</CardTitle></CardHeader>
          <CardContent className="text-sm text-muted-foreground space-y-2">
            <p>Solo usuarios con rol administrador pueden modificar integraciones.</p>
            <p>Las pruebas de conexión y cambios quedan en Logs / Auditoría.</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
