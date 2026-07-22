"use client";

import { AppShell } from "@/components/layout/app-shell";
import { M365Workspace } from "@/components/m365/m365-workspace";

export default function M365OperativoPage() {
  return (
    <AppShell
      title="Microsoft 365 Enterprise"
      description="Correo, calendario, Teams, archivos y búsqueda empresarial"
    >
      <M365Workspace />
    </AppShell>
  );
}
