"use client";

import { CommercialSearchSection } from "@/components/modules/agentes-ia/commercial-search-section";
import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { AppShell } from "@/components/layout/app-shell";

export default function BusquedaComercialPage() {
  return (
    <AppShell hideHeaderTitle>
      <AdminPageHeader
        title="Búsqueda comercial"
        description="Historial de ventas, cotizaciones y facturas indexados desde Odoo · Solo lectura"
      />
      <CommercialSearchSection />
    </AppShell>
  );
}
