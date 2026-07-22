"use client";

import dynamic from "next/dynamic";

import { ModuleEmptyState } from "@/components/module/module-dashboard";
import { LoadingState } from "@/components/brand/loading-state";
import type { ModuleSection } from "@/lib/modules/types";

const CommunicationsConversationsSection = dynamic(
  () => import("@/components/comunicaciones/communications-conversations-section").then((m) => m.CommunicationsConversationsSection),
  { loading: () => <LoadingState message="Cargando conversaciones…" /> },
);
const CommunicationsChannelsPanel = dynamic(
  () => import("@/components/comunicaciones/communications-channels-panel").then((m) => m.CommunicationsChannelsPanel),
  { loading: () => <LoadingState message="Cargando canales…" /> },
);
const CommunicationsInboxIntelligence = dynamic(
  () => import("@/components/comunicaciones/communications-inbox-intelligence").then((m) => m.CommunicationsInboxIntelligence),
  { loading: () => <LoadingState message="Cargando bandeja…" /> },
);
const CommunicationsTemplatesSection = dynamic(
  () => import("@/components/comunicaciones/communications-templates-section").then((m) => m.CommunicationsTemplatesSection),
  { loading: () => <LoadingState message="Cargando plantillas…" /> },
);
const CommunicationsAutomationsSection = dynamic(
  () => import("@/components/comunicaciones/communications-automations-section").then((m) => m.CommunicationsAutomationsSection),
  { loading: () => <LoadingState message="Cargando automatizaciones…" /> },
);
const CommunicationsReportsSection = dynamic(
  () => import("@/components/comunicaciones/communications-reports-section").then((m) => m.CommunicationsReportsSection),
  { loading: () => <LoadingState message="Cargando reportes…" /> },
);
const CommunicationsConfigSection = dynamic(
  () => import("@/components/comunicaciones/communications-config-section").then((m) => m.CommunicationsConfigSection),
  { loading: () => <LoadingState message="Cargando configuración…" /> },
);
const WhatsappInbox = dynamic(
  () => import("@/components/comunicaciones/whatsapp-inbox").then((m) => m.WhatsappInbox),
  { loading: () => <LoadingState message="Cargando conversaciones…" /> },
);
const Contacts360Panel = dynamic(
  () => import("@/components/comunicaciones/contacts-360-panel").then((m) => m.Contacts360Panel),
  { loading: () => <LoadingState message="Cargando contactos…" /> },
);
const M365Workspace = dynamic(
  () => import("@/components/m365/m365-workspace").then((m) => m.M365Workspace),
  { loading: () => <LoadingState message="Cargando Microsoft 365…" /> },
);
const OdooSectionView = dynamic(
  () => import("@/components/odoo/odoo-section-view").then((m) => m.OdooSectionView),
  { loading: () => <LoadingState message="Cargando ERP…" /> },
);
const LicitacionesProcesosSection = dynamic(
  () => import("@/components/modules/licitaciones/licitaciones-sections").then((m) => m.LicitacionesProcesosSection),
  { loading: () => <LoadingState message="Cargando procesos…" /> },
);
const LicitacionesExpedientesSection = dynamic(
  () => import("@/components/modules/licitaciones/licitaciones-sections").then((m) => m.LicitacionesExpedientesSection),
  { loading: () => <LoadingState message="Cargando expedientes…" /> },
);
const LicitacionesAnalisisSection = dynamic(
  () => import("@/components/modules/licitaciones/licitaciones-sections").then((m) => m.LicitacionesAnalisisSection),
  { loading: () => <LoadingState message="Cargando análisis…" /> },
);
const LicitacionesCompetidoresSection = dynamic(
  () => import("@/components/modules/licitaciones/licitaciones-sections").then((m) => m.LicitacionesCompetidoresSection),
  { loading: () => <LoadingState message="Cargando competidores…" /> },
);
const SuppliersDirectorySection = dynamic(
  () => import("@/components/modules/proveedores/suppliers-directory-section").then((m) => m.SuppliersDirectorySection),
  { loading: () => <LoadingState message="Cargando proveedores…" /> },
);
const TenantCompaniesSection = dynamic(
  () => import("@/components/modules/empresas-grupo/tenant-companies-section").then((m) => m.TenantCompaniesSection),
  { loading: () => <LoadingState message="Cargando empresas del grupo…" /> },
);
const PriceIntelligenceOverview = dynamic(
  () => import("@/components/modules/precios/price-intelligence-overview").then((m) => m.PriceIntelligenceOverview),
  { loading: () => <LoadingState message="Cargando inteligencia de precios…" /> },
);
const DocumentosPlantillasSection = dynamic(
  () => import("@/components/modules/documentos/documentos-sections").then((m) => m.DocumentosPlantillasSection),
  { loading: () => <LoadingState message="Cargando plantillas…" /> },
);
const DocumentosPendientesSection = dynamic(
  () => import("@/components/modules/documentos/documentos-sections").then((m) => m.DocumentosPendientesSection),
  { loading: () => <LoadingState message="Cargando pendientes…" /> },
);
const DocumentosRepositoriosSection = dynamic(
  () => import("@/components/modules/documentos/documentos-sections").then((m) => m.DocumentosRepositoriosSection),
  { loading: () => <LoadingState message="Cargando repositorios…" /> },
);
const DocumentosLegalesSection = dynamic(
  () => import("@/components/modules/documentos/documentos-sections").then((m) => m.DocumentosLegalesSection),
  { loading: () => <LoadingState message="Cargando legales…" /> },
);
const DocumentosSalidasSection = dynamic(
  () => import("@/components/modules/documentos/documentos-sections").then((m) => m.DocumentosSalidasSection),
  { loading: () => <LoadingState message="Cargando salidas…" /> },
);
const PreciosAlertasSection = dynamic(
  () => import("@/components/modules/precios/precios-alertas-section").then((m) => m.PreciosAlertasSection),
  { loading: () => <LoadingState message="Cargando alertas…" /> },
);
const DocumentsEntityBrowser = dynamic(
  () => import("@/components/modules/documentos/documents-entity-browser").then((m) => m.DocumentsEntityBrowser),
  { loading: () => <LoadingState message="Cargando documentos…" /> },
);
const PreciosBuscadorSection = dynamic(
  () => import("@/components/modules/precios/precios-sections").then((m) => m.PreciosBuscadorSection),
  { loading: () => <LoadingState message="Cargando buscador…" /> },
);
const PreciosListasSection = dynamic(
  () => import("@/components/modules/precios/precios-sections").then((m) => m.PreciosListasSection),
  { loading: () => <LoadingState message="Cargando listas…" /> },
);
const PreciosDraftsSection = dynamic(
  () => import("@/components/modules/precios/precios-sections").then((m) => m.PreciosDraftsSection),
  { loading: () => <LoadingState message="Cargando borradores…" /> },
);
const TareasListSection = dynamic(
  () => import("@/components/modules/tareas/tareas-sections").then((m) => m.TareasListSection),
  { loading: () => <LoadingState message="Cargando tareas…" /> },
);
const TareasWorkHubSection = dynamic(
  () => import("@/components/modules/tareas/tareas-sections").then((m) => m.TareasWorkHubSection),
  { loading: () => <LoadingState message="Cargando proyectos…" /> },
);
const GlobalSearchSection = dynamic(
  () => import("@/components/modules/search/global-search-section").then((m) => m.GlobalSearchSection),
  { loading: () => <LoadingState message="Cargando búsqueda…" /> },
);
const HermesIntelligenceCenterSection = dynamic(
  () => import("@/components/modules/agentes-ia/hermes-intelligence-center").then((m) => m.HermesIntelligenceCenterSection),
  { loading: () => <LoadingState message="Cargando centro Hermes…" /> },
);
const CommercialSearchSection = dynamic(
  () => import("@/components/modules/agentes-ia/commercial-search-section").then((m) => m.CommercialSearchSection),
  { loading: () => <LoadingState message="Cargando búsqueda comercial…" /> },
);
const InteligenciaComercialSection = dynamic(
  () => import("@/components/modules/agentes-ia/inteligencia-comercial-section").then((m) => m.InteligenciaComercialSection),
  { loading: () => <LoadingState message="Cargando inteligencia…" /> },
);
const ModuleReportsSection = dynamic(
  () => import("@/components/modules/shared/module-reports").then((m) => m.ModuleReportsSection),
  { loading: () => <LoadingState message="Cargando reportes…" /> },
);
const ModuleConfigEmbed = dynamic(
  () => import("@/components/modules/shared/module-config").then((m) => m.ModuleConfigEmbed),
  { loading: () => <LoadingState message="Cargando configuración…" /> },
);
const ModuleDocumentsHub = dynamic(
  () => import("@/components/module/sections/embed-sections").then((m) => m.DocumentsHubSection),
  { loading: () => <LoadingState message="Cargando documentos…" /> },
);
const ModuleExecutiveReport = dynamic(
  () => import("@/components/module/sections/embed-sections").then((m) => m.ExecutiveReportSection),
  { loading: () => <LoadingState message="Cargando reportes…" /> },
);
const ModuleInteligenciaBandeja = dynamic(
  () => import("@/components/module/sections/embed-sections").then((m) => m.InteligenciaBandejaSection),
  { loading: () => <LoadingState message="Cargando bandeja…" /> },
);

type LicitacionesMode = "list" | "kanban" | "calendar" | "won";

function licitacionesMode(section: ModuleSection, activeView: string): LicitacionesMode {
  if (section.id === "adjudicaciones") return "won";
  if (activeView === "kanban") return "kanban";
  if (activeView === "calendar") return "calendar";
  return "list";
}

function preciosSearchMode(sectionId: string): "search" | "compare" | "history" {
  if (sectionId === "comparaciones") return "compare";
  if (sectionId === "historico") return "history";
  return "search";
}

type ConfigKey =
  | "general"
  | "integraciones"
  | "odoo"
  | "whatsapp"
  | "m365"
  | "dgcp"
  | "ia"
  | "prompts"
  | "apariencia"
  | "permisos"
  | "seguridad"
  | "auditoria"
  | "empresas"
  | "usuarios";

export function renderSectionContent(
  section: ModuleSection,
  appId: string,
  activeView = "list",
) {
  const key = section.contentKey;

  if (key === "comunicaciones:conversations") return <CommunicationsConversationsSection activeView={activeView} />;
  if (key === "comunicaciones:inbox") return <WhatsappInbox hideSessionManagement />;
  if (key === "comunicaciones:contacts") return <Contacts360Panel />;
  if (key === "comunicaciones:channels") return <CommunicationsChannelsPanel />;
  if (key === "comunicaciones:bandeja") return <CommunicationsInboxIntelligence />;
  if (key === "comunicaciones:templates") return <CommunicationsTemplatesSection />;
  if (key === "comunicaciones:automations") return <CommunicationsAutomationsSection />;
  if (key === "comunicaciones:reports") return <CommunicationsReportsSection />;
  if (key === "comunicaciones:config") return <CommunicationsConfigSection />;

  if (key === "m365:operativo") {
    return (
      <div className="-mx-2">
        <M365Workspace />
      </div>
    );
  }

  if (key === "odoo:tab" && section.odooTab) return <OdooSectionView tab={section.odooTab} />;

  if (key === "licitaciones:procesos" || key === "dgcp:procesos") {
    return <LicitacionesProcesosSection mode={licitacionesMode(section, activeView)} />;
  }
  if (key === "licitaciones:expedientes" || key === "dgcp:expedientes") {
    return <LicitacionesExpedientesSection />;
  }
  if (key === "licitaciones:analisis") return <LicitacionesAnalisisSection />;
  if (key === "licitaciones:competidores") return <LicitacionesCompetidoresSection />;

  if (key === "documentos:hub") return <ModuleDocumentsHub />;
  if (key === "documentos:empresas") return <TenantCompaniesSection />;
  if (key === "documentos:plantillas") return <DocumentosPlantillasSection />;
  if (key === "documentos:pendientes") return <DocumentosPendientesSection />;
  if (key === "documentos:repositorios") return <DocumentosRepositoriosSection />;
  if (key === "documentos:legales") return <DocumentosLegalesSection />;
  if (key === "documentos:salidas") return <DocumentosSalidasSection />;
  if (key === "documentos:precios") return <PreciosListasSection />;
  if (key === "documentos:entities") return <DocumentsEntityBrowser />;
  if (key === "precios:alertas") return <PreciosAlertasSection />;

  if (key === "prices:search") {
    return <PreciosBuscadorSection mode={preciosSearchMode(section.id)} />;
  }
  if (key === "prices:drafts") return <PreciosDraftsSection />;

  if (key === "tasks:list") return <TareasListSection sectionId={section.id} />;
  if (key === "work:centro") return <TareasWorkHubSection />;

  if (key === "search:global") return <GlobalSearchSection />;

  if (key === "empresas:list") return <TenantCompaniesSection />;
  if (key === "empresas-grupo:list") return <TenantCompaniesSection />;
  if (key === "suppliers:directory") return <SuppliersDirectorySection />;
  if (key === "precios:overview") return <PriceIntelligenceOverview />;

  if (key === "reportes:centro") {
    if (appId === "reportes" && section.id === "centro-mando") {
      return <ModuleExecutiveReport />;
    }
    return <ModuleReportsSection moduleId={appId} />;
  }

  if (key === "inteligencia:bandeja") return <ModuleInteligenciaBandeja />;
  if (key === "inteligencia:comercial") return <InteligenciaComercialSection />;
  if (key === "inteligencia:busqueda") return <CommercialSearchSection />;
  if (key === "inteligencia:centro") return <HermesIntelligenceCenterSection />;

  if (key.startsWith("config:")) {
    const configKey = key.replace("config:", "") as ConfigKey;
    return <ModuleConfigEmbed configKey={configKey} />;
  }

  if (key === "placeholder") {
    return (
      <ModuleEmptyState
        title={`${section.label} — en construcción`}
        description="La estructura del módulo está lista. Esta vista operativa se conectará en la siguiente iteración."
      />
    );
  }

  return <ModuleEmptyState title="Sección no disponible" description={`Clave: ${key}`} />;
}
