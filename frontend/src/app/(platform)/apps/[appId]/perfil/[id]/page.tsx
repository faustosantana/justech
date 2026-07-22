"use client";

import { notFound, useParams } from "next/navigation";

import { CompanyExpedienteView } from "@/components/modules/empresas-grupo/company-expediente-view";
import { SupplierDetailView } from "@/components/modules/proveedores/supplier-detail-view";
import { MODULE_BY_ID } from "@/lib/modules/registry";

export default function EntityProfilePage() {
  const params = useParams();
  const appId = params.appId as string;
  const id = params.id as string;

  if (!MODULE_BY_ID[appId]) notFound();

  if (appId === "empresas-grupo") {
    return (
      <CompanyExpedienteView
        companyId={id}
        backHref="/apps/empresas-grupo/empresas"
        backLabel="← Empresas del grupo"
      />
    );
  }

  if (appId === "proveedores") {
    return (
      <SupplierDetailView
        supplierId={id}
        backHref="/apps/proveedores/directorio"
        backLabel="← Directorio de proveedores"
      />
    );
  }

  notFound();
}
