import {
  BarChart3,
  Bell,
  Bookmark,
  Brain,
  Building2,
  Calendar,
  ClipboardList,
  Dices,
  FileSearch,
  FileStack,
  FileText,
  FolderOpen,
  Inbox,
  LineChart,
  Mail,
  MessageCircle,
  Package,
  Receipt,
  Settings,
  ShoppingCart,
  Sparkles,
  Star,
  Target,
  TrendingUp,
  UserCircle,
  Users,
  Video,
  Workflow,
  type LucideIcon,
} from "lucide-react";

import type { ModuleDefinition, QuickAction } from "./types";
import type { ModuleActivity, ModuleDashboardData, ModuleKpi } from "./types";
import { moduleBase, moduleSectionHref } from "./types";

function qa(
  id: string,
  label: string,
  icon: LucideIcon,
  href: string,
): QuickAction {
  return { id, label, icon, href };
}

function copilot(
  id: string,
  label: string,
  icon: LucideIcon,
  prompt: string,
): QuickAction {
  return { id, label, icon, onClick: "copilot", copilotPrompt: prompt };
}

export const MODULE_REGISTRY: ModuleDefinition[] = [
  {
    id: "comunicaciones",
    label: "Comunicaciones",
    icon: MessageCircle,
    accent: "bg-emerald-500/12 text-emerald-700",
    routePrefixes: ["/comunicaciones", "/apps/comunicaciones"],
    searchPlaceholder: "Buscar conversaciones, contactos, correos…",
    dashboardSubtitle: "Bandeja unificada y canales conectados",
    copilotSuggestions: [
      "Resumir conversación activa",
      "Sugerir respuesta al cliente",
      "Buscar cotizaciones relacionadas",
      "Crear tarea desde chat",
    ],
    defaultQuickActions: [
      qa("nueva", "Nueva conversación", MessageCircle, moduleSectionHref("comunicaciones", "conversaciones")),
      qa("contacto", "Buscar contacto", Users, moduleSectionHref("comunicaciones", "contactos")),
      qa("canal", "Conectar canal", Settings, moduleSectionHref("comunicaciones", "canales")),
      copilot("ia-resp", "Sugerir respuesta", Sparkles, "Sugiere una respuesta profesional para la conversación activa"),
    ],
    sections: [
      { id: "conversaciones", label: "Conversaciones", icon: Inbox, contentKey: "comunicaciones:conversations", views: ["list", "kanban"] },
      { id: "contactos", label: "Contactos", icon: Users, contentKey: "comunicaciones:contacts", views: ["list"] },
      { id: "canales", label: "Canales", icon: MessageCircle, contentKey: "comunicaciones:channels", views: ["list"] },
      { id: "bandejas", label: "Bandejas", icon: Sparkles, contentKey: "comunicaciones:bandeja", views: ["list"] },
      { id: "plantillas", label: "Plantillas", icon: FileText, contentKey: "comunicaciones:templates", description: "Plantillas de mensajes reutilizables" },
      { id: "automatizaciones", label: "Automatizaciones", icon: Workflow, contentKey: "comunicaciones:automations" },
      { id: "reportes", label: "Reportes", icon: BarChart3, contentKey: "comunicaciones:reports", views: ["reports"] },
      {
        id: "configuracion",
        label: "Configuración",
        icon: Settings,
        contentKey: "comunicaciones:config",
        roles: ["admin", "superadmin", "owner"],
      },
    ],
  },
  {
    id: "empresas-grupo",
    label: "Empresas del Grupo",
    icon: Building2,
    accent: "bg-blue-900/12 text-blue-900 dark:text-blue-200",
    routePrefixes: ["/empresas", "/documentos/empresas", "/apps/empresas-grupo"],
    searchPlaceholder: "Buscar Justech, Just Office, MF Plug, Omni…",
    dashboardSubtitle: "Expedientes legales, fiscales y documentación del grupo",
    copilotSuggestions: [
      "¿Qué documentos faltan por empresa?",
      "¿Cuáles certificaciones vencen pronto?",
      "Resumir perfil de Justech SRL",
    ],
    defaultQuickActions: [
      qa("perfiles", "Ver perfiles", Building2, moduleSectionHref("empresas-grupo", "empresas")),
      qa("pendientes", "Documentos pendientes", FileStack, moduleSectionHref("empresas-grupo", "pendientes")),
      qa("legales", "Documentos legales", FileText, moduleSectionHref("empresas-grupo", "legales")),
    ],
    sections: [
      { id: "empresas", label: "Perfiles", icon: Building2, contentKey: "empresas-grupo:list", entityScope: "internal_company", views: ["list"] },
      { id: "pendientes", label: "Pendientes", icon: Bell, contentKey: "documentos:pendientes", views: ["list"] },
      { id: "legales", label: "Documentos legales", icon: FileText, contentKey: "documentos:legales", views: ["list"] },
      { id: "certificaciones", label: "Certificaciones", icon: FileStack, contentKey: "documentos:pendientes", views: ["list"] },
      { id: "plantillas", label: "Plantillas", icon: FileSearch, contentKey: "documentos:plantillas", views: ["list"] },
      { id: "configuracion", label: "Configuración", icon: Settings, contentKey: "config:empresas", roles: ["admin", "superadmin", "owner"] },
    ],
  },
  {
    id: "crm",
    label: "CRM",
    icon: Users,
    accent: "bg-sky-500/12 text-sky-700",
    routePrefixes: ["/apps/crm"],
    searchPlaceholder: "Buscar clientes, contactos, oportunidades…",
    dashboardSubtitle: "Pipeline comercial y relaciones con clientes",
    copilotSuggestions: [
      "Detectar oportunidades sin movimiento",
      "Sugerir próximo seguimiento",
      "Resumir historial de cliente",
    ],
    defaultQuickActions: [
      qa("lead", "Nuevo lead", Target, moduleSectionHref("crm", "oportunidades")),
      qa("empresa", "Nueva empresa", Building2, moduleSectionHref("crm", "empresas")),
      qa("contacto", "Nuevo contacto", Users, moduleSectionHref("crm", "contactos")),
      qa("actividad", "Nueva actividad", ClipboardList, "/tasks"),
    ],
    sections: [
      { id: "empresas", label: "Cuentas cliente", icon: Building2, contentKey: "odoo:tab", odooTab: "clientes", views: ["list", "kanban"] },
      { id: "contactos", label: "Contactos", icon: Users, contentKey: "comunicaciones:contacts", views: ["list"] },
      { id: "oportunidades", label: "Oportunidades", icon: Target, contentKey: "odoo:tab", odooTab: "oportunidades", views: ["list", "kanban"] },
      { id: "pipeline", label: "Pipeline", icon: TrendingUp, contentKey: "odoo:tab", odooTab: "oportunidades", views: ["kanban"] },
      { id: "actividades", label: "Actividades", icon: ClipboardList, contentKey: "tasks:list", views: ["list", "calendar"] },
      { id: "seguimientos", label: "Seguimientos", icon: Bell, contentKey: "tasks:list", views: ["list"] },
      { id: "reportes", label: "Reportes", icon: BarChart3, contentKey: "reportes:centro", views: ["reports"] },
      { id: "configuracion", label: "Configuración", icon: Settings, contentKey: "config:general" },
    ],
  },
  {
    id: "ventas",
    label: "Ventas",
    icon: TrendingUp,
    accent: "bg-violet-500/12 text-violet-700",
    routePrefixes: ["/odoo", "/apps/ventas"],
    odooTabs: ["ventas", "cotizaciones", "resumen", "clientes"],
    searchPlaceholder: "Buscar ventas, cotizaciones, clientes…",
    dashboardSubtitle: "Cotizaciones, órdenes y desempeño comercial",
    copilotSuggestions: [
      "Interpretar solicitud de cotización",
      "Buscar precios en listas",
      "Recomendar margen comercial",
      "Crear borrador de cotización",
    ],
    defaultQuickActions: [
      qa("cot", "Nueva cotización", FileText, moduleSectionHref("ventas", "cotizaciones")),
      qa("cliente", "Nuevo cliente", UserCircle, moduleSectionHref("ventas", "clientes")),
      qa("producto", "Productos", Package, moduleSectionHref("ventas", "productos")),
      copilot("import", "Importar solicitud", Sparkles, "Interpreta la solicitud de cotización del cliente y extrae productos, cantidades y urgencia"),
    ],
    sections: [
      { id: "cotizaciones", label: "Cotizaciones", icon: FileText, contentKey: "odoo:tab", odooTab: "cotizaciones", views: ["list", "kanban"] },
      { id: "ordenes", label: "Órdenes de venta", icon: TrendingUp, contentKey: "odoo:tab", odooTab: "ventas", views: ["list"] },
      { id: "clientes", label: "Clientes", icon: UserCircle, contentKey: "odoo:tab", odooTab: "clientes", views: ["list"] },
      { id: "productos", label: "Productos", icon: Package, contentKey: "odoo:tab", odooTab: "productos", views: ["list"] },
      { id: "servicios", label: "Servicios", icon: Workflow, contentKey: "odoo:tab", odooTab: "productos", views: ["list"] },
      { id: "facturas", label: "Facturas", icon: Receipt, contentKey: "odoo:tab", odooTab: "facturas", views: ["list"] },
      { id: "reportes", label: "Reportes", icon: BarChart3, contentKey: "odoo:tab", odooTab: "resumen", views: ["reports", "charts"] },
      { id: "configuracion", label: "Configuración", icon: Settings, contentKey: "config:odoo" },
    ],
  },
  {
    id: "compras",
    label: "Compras",
    icon: ShoppingCart,
    accent: "bg-orange-500/12 text-orange-700",
    routePrefixes: ["/apps/compras"],
    odooTabs: ["proveedores"],
    searchPlaceholder: "Buscar proveedores, órdenes de compra…",
    dashboardSubtitle: "Solicitudes, órdenes y recepciones",
    copilotSuggestions: ["Buscar mejor proveedor", "Comparar precios", "Detectar variaciones de precio"],
    defaultQuickActions: [
      qa("oc", "Órdenes de compra", ShoppingCart, moduleSectionHref("compras", "ordenes")),
      qa("prov", "Proveedores", Building2, moduleSectionHref("compras", "proveedores")),
      qa("precios", "Comparar precios", LineChart, moduleSectionHref("precios", "buscador")),
    ],
    sections: [
      { id: "solicitudes", label: "Solicitudes", icon: ClipboardList, contentKey: "placeholder", views: ["list", "kanban"] },
      { id: "cotizaciones", label: "Cotiz. proveedores", icon: FileText, contentKey: "placeholder", views: ["list"] },
      { id: "ordenes", label: "Órdenes de compra", icon: ShoppingCart, contentKey: "placeholder", views: ["list"] },
      { id: "recepciones", label: "Recepciones", icon: Package, contentKey: "placeholder", views: ["list"] },
      { id: "proveedores", label: "Proveedores", icon: Building2, contentKey: "odoo:tab", odooTab: "proveedores", views: ["list"] },
      { id: "contratos", label: "Contratos", icon: FileStack, contentKey: "documentos:hub", views: ["list"] },
      { id: "aprobaciones", label: "Aprobaciones", icon: Target, contentKey: "placeholder", views: ["kanban"] },
      { id: "reportes", label: "Reportes", icon: BarChart3, contentKey: "reportes:centro", views: ["reports"] },
      { id: "configuracion", label: "Configuración", icon: Settings, contentKey: "config:odoo" },
    ],
  },
  {
    id: "inventario",
    label: "Inventario",
    icon: Package,
    accent: "bg-amber-500/12 text-amber-800",
    routePrefixes: ["/apps/inventario"],
    odooTabs: ["productos"],
    searchPlaceholder: "Buscar productos, SKU, almacenes…",
    dashboardSubtitle: "Existencias, movimientos y valoración",
    copilotSuggestions: ["Validar disponibilidad", "Sugerir reposición", "Analizar rotación"],
    defaultQuickActions: [
      qa("prod", "Productos", Package, moduleSectionHref("inventario", "productos")),
      qa("buscar", "Consultar existencia", LineChart, moduleSectionHref("precios", "buscador")),
    ],
    sections: [
      { id: "productos", label: "Productos", icon: Package, contentKey: "odoo:tab", odooTab: "productos", views: ["list", "kanban"] },
      { id: "categorias", label: "Categorías", icon: FolderOpen, contentKey: "placeholder", views: ["list"] },
      { id: "almacenes", label: "Almacenes", icon: Building2, contentKey: "placeholder", views: ["list"] },
      { id: "existencias", label: "Existencias", icon: Package, contentKey: "odoo:tab", odooTab: "productos", views: ["list"] },
      { id: "movimientos", label: "Movimientos", icon: TrendingUp, contentKey: "placeholder", views: ["list"] },
      { id: "transferencias", label: "Transferencias", icon: Workflow, contentKey: "placeholder", views: ["list"] },
      { id: "ajustes", label: "Ajustes", icon: Settings, contentKey: "placeholder", views: ["list"] },
      { id: "reportes", label: "Reportes", icon: BarChart3, contentKey: "reportes:centro", views: ["reports"] },
      { id: "configuracion", label: "Configuración", icon: Settings, contentKey: "config:odoo" },
    ],
  },
  {
    id: "facturacion",
    label: "Facturación",
    icon: Receipt,
    accent: "bg-rose-500/12 text-rose-700",
    routePrefixes: ["/apps/facturacion"],
    odooTabs: ["facturas"],
    searchPlaceholder: "Buscar facturas, CxC, pagos…",
    dashboardSubtitle: "Facturación, cobros y cuentas por pagar",
    copilotSuggestions: ["Resumir deuda de cliente", "Detectar facturas críticas", "Sugerir acciones de cobro"],
    defaultQuickActions: [
      qa("factura", "Facturas", Receipt, moduleSectionHref("facturacion", "facturas")),
      qa("cxc", "Cuentas por cobrar", TrendingUp, moduleSectionHref("facturacion", "cuentas-cobrar")),
    ],
    sections: [
      { id: "facturas", label: "Facturas", icon: Receipt, contentKey: "odoo:tab", odooTab: "facturas", views: ["list", "calendar"] },
      { id: "cuentas-cobrar", label: "Cuentas por cobrar", icon: TrendingUp, contentKey: "odoo:tab", odooTab: "facturas", views: ["list"] },
      { id: "cuentas-pagar", label: "Cuentas por pagar", icon: ShoppingCart, contentKey: "placeholder", views: ["list"] },
      { id: "pagos", label: "Pagos", icon: Receipt, contentKey: "placeholder", views: ["list"] },
      { id: "notas-credito", label: "Notas de crédito", icon: FileText, contentKey: "placeholder", views: ["list"] },
      { id: "clientes", label: "Clientes", icon: UserCircle, contentKey: "odoo:tab", odooTab: "clientes", views: ["list"] },
      { id: "reportes", label: "Reportes", icon: BarChart3, contentKey: "odoo:tab", odooTab: "resumen", views: ["reports", "charts"] },
      { id: "configuracion", label: "Configuración", icon: Settings, contentKey: "config:odoo" },
    ],
  },
  {
    id: "documentos",
    label: "Documentos",
    icon: FileStack,
    accent: "bg-indigo-500/12 text-indigo-700",
    routePrefixes: ["/documentos", "/documents", "/apps/documentos"],
    searchPlaceholder: "Buscar documentos, contratos, expedientes…",
    dashboardSubtitle: "Repositorio documental y expedientes",
    copilotSuggestions: ["Buscar dentro de documentos", "Resumir contrato", "Detectar vencimientos"],
    defaultQuickActions: [
      qa("repo", "Repositorio", FolderOpen, moduleSectionHref("documentos", "repositorio")),
      qa("subir", "Subir documento", FileStack, moduleSectionHref("documentos", "repositorio")),
      copilot("analizar", "Analizar con IA", Sparkles, "Analiza el documento seleccionado y extrae datos clave"),
    ],
    sections: [
      { id: "repositorio", label: "Repositorio", icon: FolderOpen, contentKey: "documentos:hub", views: ["list", "kanban"] },
      { id: "clientes", label: "Empresas del grupo", icon: Building2, contentKey: "empresas-grupo:list", views: ["list"] },
      { id: "proveedores", label: "Docs. proveedores", icon: Building2, contentKey: "suppliers:directory", views: ["list"], description: "Directorio de suplidores externos" },
      { id: "licitaciones", label: "Licitaciones", icon: FileSearch, contentKey: "documentos:salidas", views: ["list"] },
      { id: "contratos", label: "Contratos", icon: FileText, contentKey: "documentos:legales", views: ["list"] },
      { id: "plantillas", label: "Plantillas", icon: FileSearch, contentKey: "documentos:plantillas", views: ["list"] },
      { id: "certificaciones", label: "Certificaciones", icon: FileStack, contentKey: "documentos:pendientes", views: ["list"] },
      { id: "busqueda", label: "Por entidad", icon: FileSearch, contentKey: "documentos:entities", views: ["list"] },
      { id: "busqueda-avanzada", label: "Búsqueda avanzada", icon: FileSearch, contentKey: "search:global", views: ["list"] },
      { id: "reportes", label: "Reportes", icon: BarChart3, contentKey: "reportes:centro", views: ["reports"] },
      { id: "configuracion", label: "Configuración", icon: Settings, contentKey: "config:general" },
    ],
  },
  {
    id: "licitaciones",
    label: "Licitaciones",
    icon: FileSearch,
    accent: "bg-cyan-500/12 text-cyan-800",
    routePrefixes: ["/dgcp", "/oportunidades", "/apps/licitaciones"],
    searchPlaceholder: "Buscar procesos, expedientes DGCP…",
    dashboardSubtitle: "Procesos públicos, expedientes y análisis IA",
    copilotSuggestions: [
      "Analizar pliego",
      "Detectar documentos requeridos",
      "Recomendar participar o descartar",
      "Buscar adjudicaciones similares",
    ],
    defaultQuickActions: [
      qa("procesos", "Procesos DGCP", FileSearch, moduleSectionHref("licitaciones", "procesos")),
      qa("exp", "Expedientes", FolderOpen, moduleSectionHref("licitaciones", "expedientes")),
      copilot("analizar", "Analizar proceso", Sparkles, "Analiza el proceso de licitación seleccionado y detecta riesgos"),
    ],
    sections: [
      { id: "procesos", label: "Procesos", icon: FileSearch, contentKey: "licitaciones:procesos", views: ["list", "kanban", "calendar"] },
      { id: "expedientes", label: "Expedientes", icon: FolderOpen, contentKey: "licitaciones:expedientes", views: ["list"] },
      { id: "formularios", label: "Formularios", icon: FileText, contentKey: "documentos:plantillas", views: ["list"] },
      { id: "documentos", label: "Documentos", icon: FileStack, contentKey: "documentos:hub", views: ["list"] },
      { id: "analisis", label: "Análisis IA", icon: Sparkles, contentKey: "licitaciones:analisis", views: ["charts"] },
      { id: "adjudicaciones", label: "Adjudicaciones", icon: Target, contentKey: "licitaciones:procesos", views: ["list"] },
      { id: "competidores", label: "Competidores", icon: Users, contentKey: "licitaciones:competidores", views: ["list"] },
      { id: "calendario", label: "Calendario", icon: Calendar, contentKey: "licitaciones:procesos", views: ["calendar"] },
      { id: "reportes", label: "Reportes", icon: BarChart3, contentKey: "reportes:centro", views: ["reports"] },
      { id: "configuracion", label: "Configuración", icon: Settings, contentKey: "config:dgcp" },
    ],
  },
  {
    id: "precios",
    label: "Inteligencia de Precios",
    icon: LineChart,
    accent: "bg-teal-500/12 text-teal-700",
    routePrefixes: ["/prices", "/apps/precios"],
    searchPlaceholder: "Buscar productos, precios, proveedores…",
    dashboardSubtitle: "Comparación, histórico y alertas de precio",
    copilotSuggestions: ["Normalizar productos", "Comparar proveedores", "Detectar equivalentes"],
    defaultQuickActions: [
      qa("buscar", "Buscar producto", LineChart, moduleSectionHref("precios", "buscador")),
      qa("listas", "Listas de precios", FileStack, moduleSectionHref("precios", "listas")),
      qa("comparar", "Comparar", TrendingUp, moduleSectionHref("precios", "comparaciones")),
    ],
    sections: [
      { id: "resumen", label: "Resumen", icon: BarChart3, contentKey: "precios:overview", views: ["dashboard"] },
      { id: "buscador", label: "Buscador", icon: LineChart, contentKey: "prices:search", views: ["list"] },
      { id: "productos", label: "Productos", icon: Package, contentKey: "prices:search", views: ["list"] },
      { id: "listas", label: "Listas de precios", icon: FileStack, contentKey: "documentos:precios", views: ["list"] },
      { id: "proveedores", label: "Por proveedor", icon: Building2, contentKey: "suppliers:directory", views: ["list"], description: "Suplidores con listas indexadas" },
      { id: "comparaciones", label: "Comparaciones", icon: TrendingUp, contentKey: "prices:search", views: ["charts"] },
      { id: "historico", label: "Histórico", icon: BarChart3, contentKey: "prices:search", views: ["charts"] },
      { id: "alertas", label: "Alertas", icon: Bell, contentKey: "precios:alertas", views: ["list"] },
      { id: "reportes", label: "Reportes", icon: BarChart3, contentKey: "reportes:centro", views: ["reports"] },
      { id: "configuracion", label: "Configuración", icon: Settings, contentKey: "config:integraciones" },
    ],
  },
  {
    id: "lottery",
    label: "Resultados de Loterías",
    icon: Dices,
    accent: "bg-amber-500/12 text-amber-800",
    routePrefixes: ["/lottery", "/apps/lottery"],
    searchPlaceholder: "Buscar lotería, fecha, sorteo…",
    dashboardSubtitle: "Histórico validado, comparación, estadísticas y Lotería IA",
    copilotSuggestions: [
      "Resultado Real 15 marzo 2022",
      "Comparar Leidsa y Loteka",
      "Frecuencias Nacional Noche",
    ],
    defaultQuickActions: [
      qa("inicio", "Resumen", Dices, "/lottery"),
      qa("buscar", "Consulta histórica", FileSearch, "/lottery/search"),
      qa("chat", "Lotería IA", Sparkles, "/lottery/chat"),
      qa("comparar", "Comparar", TrendingUp, "/lottery/compare"),
    ],
    sections: [
      {
        id: "inicio",
        label: "Resumen",
        icon: BarChart3,
        contentKey: "lottery:dashboard",
        views: ["dashboard"],
        legacyHref: "/lottery",
        group: "Inicio",
        shortDescription: "KPIs, resultados de hoy y estado del worker",
      },
      {
        id: "catalogo",
        label: "Catálogo",
        icon: Dices,
        contentKey: "lottery:lotteries",
        views: ["list"],
        legacyHref: "/lottery/lotteries",
        group: "Inicio",
        shortDescription: "Loterías visibles y ficha de cada una",
      },
      {
        id: "consulta",
        label: "Consulta histórica",
        icon: FileSearch,
        contentKey: "lottery:search",
        views: ["list"],
        legacyHref: "/lottery/search",
        group: "Análisis",
        shortDescription: "Buscar por lotería, fecha o número",
      },
      {
        id: "comparar",
        label: "Comparar",
        icon: TrendingUp,
        contentKey: "lottery:compare",
        views: ["charts"],
        legacyHref: "/lottery/compare",
        group: "Análisis",
        shortDescription: "Frecuencias y coincidencias entre loterías",
      },
      {
        id: "estadisticas",
        label: "Estadísticas",
        icon: LineChart,
        contentKey: "lottery:statistics",
        views: ["charts"],
        legacyHref: "/lottery/statistics",
        group: "Análisis",
        shortDescription: "Calientes, fríos, cobertura y calidad",
      },
      {
        id: "chat",
        label: "Lotería IA",
        icon: Sparkles,
        contentKey: "lottery:chat",
        views: ["list"],
        legacyHref: "/lottery/chat",
        group: "Análisis",
        shortDescription: "Preguntas con tools y análisis histórico",
      },
      {
        id: "favoritos",
        label: "Favoritos",
        icon: Star,
        contentKey: "lottery:favorites",
        views: ["list"],
        legacyHref: "/lottery/favorites",
        group: "Mi espacio",
        shortDescription: "Loterías marcadas por el usuario",
      },
      {
        id: "guardadas",
        label: "Consultas guardadas",
        icon: Bookmark,
        contentKey: "lottery:saved",
        views: ["list"],
        legacyHref: "/lottery/saved",
        group: "Mi espacio",
        shortDescription: "Consultas reutilizables del usuario",
      },
      {
        id: "admin-lotteries",
        label: "Loterías",
        icon: Settings,
        contentKey: "lottery:admin-lotteries",
        views: ["list"],
        legacyHref: "/lottery/admin/lotteries",
        group: "Administración",
        roles: ["owner", "admin", "superadmin"],
        shortDescription: "Visibilidad, sync y auto-write por lotería",
      },
      {
        id: "admin-sync",
        label: "Sincronización",
        icon: Settings,
        contentKey: "lottery:admin-sync",
        views: ["list"],
        legacyHref: "/lottery/admin/sync",
        group: "Administración",
        roles: ["owner", "admin", "superadmin"],
        shortDescription: "Runs, backup gate y escritura controlada",
      },
      {
        id: "admin-scheduler",
        label: "Scheduler y fuentes",
        icon: Settings,
        contentKey: "lottery:admin-scheduler",
        views: ["list"],
        legacyHref: "/lottery/admin/scheduler",
        group: "Administración",
        roles: ["owner", "admin", "superadmin"],
        shortDescription: "Worker, ventanas, locks y circuit breaker",
      },
      {
        id: "admin-ai",
        label: "Centro de IA",
        icon: Brain,
        contentKey: "lottery:admin-ai",
        views: ["list"],
        legacyHref: "/lottery/admin/ai",
        group: "Administración",
        roles: ["owner", "admin", "superadmin"],
        shortDescription: "Agente, prompts, modelos, memoria y herramientas IA",
      },
      {
        id: "admin-control-center",
        label: "Lottery IA Control Center",
        icon: Brain,
        contentKey: "lottery:admin-control-center",
        views: ["list"],
        legacyHref: "/lottery/admin/control-center",
        group: "Administración",
        roles: ["owner", "admin", "superadmin"],
        shortDescription: "Motor Matemático, Predicciones y Prompt Studio administrable",
      },
      {
        id: "admin-numeric-relations",
        label: "Relaciones numéricas",
        icon: Brain,
        contentKey: "lottery:admin-numeric-relations",
        views: ["list"],
        legacyHref: "/lottery/admin/numeric-relations",
        group: "Administración",
        roles: ["owner", "admin", "superadmin"],
        shortDescription: "Auditoría del Motor de Relaciones Numéricas (Tablas 1/2 y análisis)",
      },
    ],
  },
  {
    id: "clientes",
    label: "Clientes",
    icon: UserCircle,
    accent: "bg-blue-500/12 text-blue-700",
    routePrefixes: ["/apps/clientes"],
    odooTabs: ["clientes"],
    searchPlaceholder: "Buscar clientes…",
    dashboardSubtitle: "Directorio de clientes e historial comercial",
    copilotSuggestions: ["Resumir cliente", "Detectar deudas", "Recomendar seguimiento"],
    defaultQuickActions: [
      qa("nuevo", "Nuevo cliente", UserCircle, moduleSectionHref("clientes", "empresas")),
      qa("cot", "Crear cotización", FileText, moduleSectionHref("ventas", "cotizaciones")),
    ],
    sections: [
      { id: "empresas", label: "Empresas", icon: Building2, contentKey: "odoo:tab", odooTab: "clientes", entityScope: "customer", views: ["list"] },
      { id: "contactos", label: "Contactos", icon: Users, contentKey: "comunicaciones:contacts", views: ["list"] },
      { id: "historial", label: "Historial", icon: FileText, contentKey: "odoo:tab", odooTab: "ventas", views: ["list"] },
      { id: "ventas", label: "Ventas", icon: TrendingUp, contentKey: "odoo:tab", odooTab: "ventas", views: ["list", "charts"] },
      { id: "facturas", label: "Facturas", icon: Receipt, contentKey: "odoo:tab", odooTab: "facturas", views: ["list"] },
      { id: "documentos", label: "Documentos", icon: FileStack, contentKey: "documentos:hub", views: ["list"] },
      { id: "actividades", label: "Actividades", icon: ClipboardList, contentKey: "tasks:list", views: ["list", "calendar"] },
      { id: "reportes", label: "Reportes", icon: BarChart3, contentKey: "reportes:centro", views: ["reports"] },
      { id: "configuracion", label: "Configuración", icon: Settings, contentKey: "config:general" },
    ],
  },
  {
    id: "proveedores",
    label: "Proveedores",
    icon: Building2,
    accent: "bg-slate-500/12 text-slate-700",
    routePrefixes: ["/apps/proveedores"],
    searchPlaceholder: "Buscar proveedores…",
    dashboardSubtitle: "Directorio, evaluaciones y listas de precio",
    copilotSuggestions: ["Buscar proveedor por producto", "Recomendar proveedor", "Mostrar historial de compras"],
    defaultQuickActions: [
      qa("dir", "Directorio", Building2, moduleSectionHref("proveedores", "directorio")),
      qa("lista", "Subir lista", FileStack, moduleSectionHref("precios", "listas")),
    ],
    sections: [
      { id: "directorio", label: "Directorio", icon: Building2, contentKey: "suppliers:directory", entityScope: "supplier", views: ["list"] },
      { id: "categorias", label: "Categorías", icon: FolderOpen, contentKey: "placeholder", views: ["list"] },
      { id: "productos", label: "Productos", icon: Package, contentKey: "prices:search", views: ["list"] },
      { id: "listas", label: "Listas de precios", icon: LineChart, contentKey: "documentos:precios", views: ["list"] },
      { id: "ordenes", label: "Órdenes de compra", icon: ShoppingCart, contentKey: "placeholder", views: ["list"], description: "Conexión con Odoo compras — próxima iteración" },
      { id: "historial", label: "Historial", icon: FileText, contentKey: "placeholder", views: ["list"] },
      { id: "evaluaciones", label: "Evaluaciones", icon: Target, contentKey: "placeholder", views: ["list"] },
      { id: "reportes", label: "Reportes", icon: BarChart3, contentKey: "reportes:centro", views: ["reports"] },
      { id: "configuracion", label: "Configuración", icon: Settings, contentKey: "config:integraciones" },
    ],
  },
  {
    id: "tareas",
    label: "Tareas",
    icon: ClipboardList,
    accent: "bg-fuchsia-500/12 text-fuchsia-700",
    routePrefixes: ["/tasks", "/work", "/notifications", "/apps/tareas"],
    searchPlaceholder: "Buscar tareas, asignaciones…",
    dashboardSubtitle: "Gestión de tareas, proyectos y seguimiento",
    copilotSuggestions: ["Priorizar tareas", "Detectar retrasos", "Crear tareas desde correos"],
    defaultQuickActions: [
      qa("nueva", "Nueva tarea", ClipboardList, moduleSectionHref("tareas", "mis-tareas")),
      qa("cal", "Calendario", Calendar, moduleSectionHref("tareas", "calendario")),
    ],
    sections: [
      { id: "mis-tareas", label: "Mis tareas", icon: ClipboardList, contentKey: "tasks:list", views: ["list", "kanban"] },
      { id: "equipo", label: "Equipo", icon: Users, contentKey: "tasks:list", views: ["list"] },
      { id: "vencidas", label: "Vencidas", icon: Bell, contentKey: "tasks:list", views: ["list"] },
      { id: "hoy", label: "Hoy", icon: Calendar, contentKey: "tasks:list", views: ["list", "calendar"] },
      { id: "calendario", label: "Calendario", icon: Calendar, contentKey: "tasks:list", views: ["calendar"] },
      { id: "proyectos", label: "Proyectos", icon: FolderOpen, contentKey: "work:centro", views: ["kanban"] },
      { id: "reportes", label: "Reportes", icon: BarChart3, contentKey: "reportes:centro", views: ["reports"] },
      { id: "configuracion", label: "Configuración", icon: Settings, contentKey: "config:general" },
    ],
  },
  {
    id: "calendario",
    label: "Calendario",
    icon: Calendar,
    accent: "bg-red-500/12 text-red-700",
    routePrefixes: ["/m365", "/apps/calendario"],
    searchPlaceholder: "Buscar eventos, reuniones…",
    dashboardSubtitle: "Agenda operativa y reuniones del equipo",
    copilotSuggestions: ["Agendar reunión", "Buscar disponibilidad", "Crear recordatorio"],
    defaultQuickActions: [
      qa("reunion", "Nueva reunión", Calendar, moduleSectionHref("calendario", "reuniones")),
      qa("m365", "M365 Operativo", Mail, moduleSectionHref("calendario", "mi-calendario")),
    ],
    sections: [
      { id: "mi-calendario", label: "Mi calendario", icon: Calendar, contentKey: "m365:operativo", views: ["calendar"] },
      { id: "equipo", label: "Equipo", icon: Users, contentKey: "m365:operativo", views: ["calendar"] },
      { id: "reuniones", label: "Reuniones", icon: Video, contentKey: "m365:operativo", views: ["calendar", "list"] },
      { id: "recordatorios", label: "Recordatorios", icon: Bell, contentKey: "tasks:list", views: ["list"] },
      { id: "eventos", label: "Eventos", icon: Calendar, contentKey: "m365:operativo", views: ["calendar"] },
      { id: "configuracion", label: "Configuración", icon: Settings, contentKey: "config:m365" },
    ],
  },
  {
    id: "reportes",
    label: "Reportes",
    icon: BarChart3,
    accent: "bg-primary/10 text-primary",
    routePrefixes: ["/dashboard/centro-de-mando", "/apps/reportes"],
    searchPlaceholder: "Buscar en reportes y KPIs…",
    dashboardSubtitle: "Centro de mando y reportes ejecutivos",
    copilotSuggestions: ["Interpretar indicadores", "Detectar anomalías", "Generar reporte"],
    defaultQuickActions: [
      qa("centro", "Centro de mando", BarChart3, moduleSectionHref("reportes", "centro-mando")),
      qa("buscar", "Búsqueda global", FileSearch, "/search"),
    ],
    sections: [
      { id: "centro-mando", label: "Centro de mando", icon: BarChart3, contentKey: "reportes:centro", views: ["dashboard", "charts"] },
      { id: "ventas", label: "Ventas", icon: TrendingUp, contentKey: "odoo:tab", odooTab: "resumen", views: ["reports"] },
      { id: "compras", label: "Compras", icon: ShoppingCart, contentKey: "placeholder", views: ["reports"] },
      { id: "facturacion", label: "Facturación", icon: Receipt, contentKey: "odoo:tab", odooTab: "facturas", views: ["reports"] },
      { id: "licitaciones", label: "Licitaciones", icon: FileSearch, contentKey: "licitaciones:procesos", views: ["reports"] },
      { id: "inventario", label: "Inventario", icon: Package, contentKey: "odoo:tab", odooTab: "productos", views: ["reports"] },
      { id: "actividad", label: "Actividad", icon: Workflow, contentKey: "reportes:centro", views: ["reports"] },
      { id: "personalizados", label: "Personalizados", icon: FileStack, contentKey: "placeholder", views: ["reports"] },
      { id: "configuracion", label: "Configuración", icon: Settings, contentKey: "config:general" },
    ],
  },
  {
    id: "agentes-ia",
    label: "Agentes IA",
    icon: Brain,
    accent: "bg-purple-500/12 text-purple-700",
    routePrefixes: ["/inteligencia", "/apps/agentes-ia"],
    searchPlaceholder: "Buscar observaciones, agentes…",
    dashboardSubtitle: "Agentes, automatizaciones y fuentes IA",
    copilotSuggestions: ["Revisar prompts", "Detectar errores", "Proponer automatizaciones"],
    defaultQuickActions: [
      qa("bandeja", "Bandeja inteligente", Inbox, moduleSectionHref("agentes-ia", "agentes")),
      qa("hermes", "Config. Hermes", Settings, "/configuracion/ia/hermes"),
    ],
    sections: [
      { id: "agentes", label: "Agentes", icon: Brain, contentKey: "inteligencia:bandeja", views: ["list"] },
      { id: "busqueda-comercial", label: "Búsqueda comercial", icon: FileSearch, contentKey: "inteligencia:busqueda", views: ["list"] },
      { id: "centro-hermes", label: "Centro Hermes", icon: Sparkles, contentKey: "inteligencia:centro", views: ["list"] },
      { id: "herramientas", label: "Herramientas", icon: Workflow, contentKey: "inteligencia:comercial", views: ["list"] },
      { id: "fuentes", label: "Fuentes", icon: FolderOpen, contentKey: "config:integraciones" },
      { id: "prompts", label: "Prompts", icon: FileText, contentKey: "config:prompts", roles: ["admin", "superadmin", "owner"] },
      { id: "automatizaciones", label: "Automatizaciones", icon: Sparkles, contentKey: "inteligencia:bandeja", views: ["list"] },
      { id: "logs", label: "Logs", icon: FileText, contentKey: "placeholder", views: ["list"] },
      { id: "metricas", label: "Métricas", icon: BarChart3, contentKey: "reportes:centro", views: ["charts"] },
      { id: "configuracion", label: "Configuración", icon: Settings, contentKey: "config:ia" },
    ],
  },
  {
    id: "configuracion",
    label: "Configuración",
    icon: Settings,
    accent: "bg-neutral-500/12 text-neutral-700",
    routePrefixes: ["/configuracion", "/admin", "/apps/configuracion"],
    searchPlaceholder: "Buscar en configuración…",
    adminOnly: true,
    dashboardSubtitle: "Administración del tenant y preferencias",
    copilotSuggestions: ["Configurar integraciones", "Revisar permisos", "Optimizar prompts IA"],
    defaultQuickActions: [
      qa("general", "General", Settings, moduleSectionHref("configuracion", "general")),
      qa("usuarios", "Usuarios", Users, moduleSectionHref("configuracion", "usuarios")),
      qa("apariencia", "Apariencia", Sparkles, "/configuracion/apariencia"),
    ],
    sections: [
      { id: "general", label: "General", icon: Settings, contentKey: "config:general" },
      { id: "empresas", label: "Empresa activa (tenant)", icon: Building2, contentKey: "config:empresas" },
      { id: "usuarios", label: "Usuarios", icon: Users, contentKey: "config:usuarios" },
      { id: "permisos", label: "Roles y permisos", icon: Target, contentKey: "config:permisos" },
      { id: "apariencia", label: "Apariencia", icon: Sparkles, contentKey: "config:apariencia" },
      { id: "integraciones", label: "Integraciones", icon: Workflow, contentKey: "config:integraciones" },
      { id: "odoo", label: "Odoo", icon: TrendingUp, contentKey: "config:odoo" },
      { id: "whatsapp", label: "WhatsApp", icon: MessageCircle, contentKey: "config:whatsapp" },
      { id: "outlook", label: "Outlook", icon: Mail, contentKey: "config:m365" },
      { id: "ia", label: "IA", icon: Brain, contentKey: "config:ia" },
      { id: "seguridad", label: "Seguridad", icon: Settings, contentKey: "config:seguridad" },
      { id: "auditoria", label: "Auditoría", icon: FileText, contentKey: "config:auditoria" },
    ],
  },
];

export const MODULE_BY_ID = Object.fromEntries(MODULE_REGISTRY.map((m) => [m.id, m])) as Record<string, ModuleDefinition>;

/** Secciones visibles en sidebar, breadcrumbs y dashboards (PR-1.5). */
export function isSectionNavVisible(section: ModuleDefinition["sections"][number]): boolean {
  if (section.navHidden) return false;
  if (section.contentKey === "placeholder") return false;
  return true;
}

export function parseModuleSectionHref(href: string): { appId: string; sectionId?: string } | null {
  const path = href.split("?")[0];
  if (!path.startsWith("/apps/")) return null;
  const parts = path.split("/").filter(Boolean);
  if (parts.length < 2 || parts[0] !== "apps") return null;
  return { appId: parts[1], sectionId: parts[2] };
}

/** Enlaces /apps/{mod}/{sec} solo si la sección es navegable (no placeholder). */
export function isModuleHrefNavVisible(href: string): boolean {
  const parsed = parseModuleSectionHref(href);
  if (!parsed) return true;
  if (!parsed.sectionId) return true;
  const section = getModuleSection(parsed.appId, parsed.sectionId);
  if (!section) return false;
  return isSectionNavVisible(section);
}

export function sanitizeModuleHref(href?: string): string | undefined {
  if (!href) return undefined;
  return isModuleHrefNavVisible(href) ? href : undefined;
}

export function filterModuleKpis(kpis: ModuleKpi[]): ModuleKpi[] {
  return kpis.map((k) => ({ ...k, href: sanitizeModuleHref(k.href) }));
}

export function filterModuleActivities(items: ModuleActivity[]): ModuleActivity[] {
  return items.filter((item) => !item.href || isModuleHrefNavVisible(item.href));
}

export function filterModuleDashboardData(data: ModuleDashboardData): ModuleDashboardData {
  return {
    kpis: filterModuleKpis(data.kpis),
    activity: filterModuleActivities(data.activity),
    alerts: data.alerts ? filterModuleActivities(data.alerts) : undefined,
  };
}

export function buildVisibleSectionActivity(module: ModuleDefinition, limit = 6): ModuleActivity[] {
  return module.sections
    .filter(isSectionNavVisible)
    .slice(0, limit)
    .map((s) => ({
      id: s.id,
      title: s.label,
      subtitle: s.shortDescription || "Abrir sección",
      href: s.legacyHref ?? moduleSectionHref(module.id, s.id),
    }));
}

export function moduleToNav(module: ModuleDefinition) {
  return module.sections.filter(isSectionNavVisible).map((s) => ({
    id: s.id,
    label: s.label,
    href: s.legacyHref ?? moduleSectionHref(module.id, s.id),
    icon: s.icon,
    roles: s.roles,
    moduleKey: s.moduleKey,
    group: s.group,
    title: s.shortDescription,
  }));
}

/** Mapa canónico menú Lottery → ruta App Router (pruebas de integridad). */
export const LOTTERY_NAV_INTEGRITY: { contentKey: string; href: string; group: string }[] = [
  { contentKey: "lottery:dashboard", href: "/lottery", group: "Inicio" },
  { contentKey: "lottery:lotteries", href: "/lottery/lotteries", group: "Inicio" },
  { contentKey: "lottery:search", href: "/lottery/search", group: "Análisis" },
  { contentKey: "lottery:compare", href: "/lottery/compare", group: "Análisis" },
  { contentKey: "lottery:statistics", href: "/lottery/statistics", group: "Análisis" },
  { contentKey: "lottery:chat", href: "/lottery/chat", group: "Análisis" },
  { contentKey: "lottery:favorites", href: "/lottery/favorites", group: "Mi espacio" },
  { contentKey: "lottery:saved", href: "/lottery/saved", group: "Mi espacio" },
  { contentKey: "lottery:admin-lotteries", href: "/lottery/admin/lotteries", group: "Administración" },
  { contentKey: "lottery:admin-sync", href: "/lottery/admin/sync", group: "Administración" },
  { contentKey: "lottery:admin-scheduler", href: "/lottery/admin/scheduler", group: "Administración" },
  { contentKey: "lottery:admin-ai", href: "/lottery/admin/ai", group: "Administración" },
  {
    contentKey: "lottery:admin-control-center",
    href: "/lottery/admin/control-center",
    group: "Administración",
  },
  {
    contentKey: "lottery:admin-numeric-relations",
    href: "/lottery/admin/numeric-relations",
    group: "Administración",
  },
];

export function assertLotteryNavIntegrity(module: ModuleDefinition = MODULE_BY_ID.lottery): string[] {
  const errors: string[] = [];
  if (!module) {
    return ["lottery module missing from MODULE_REGISTRY"];
  }
  const byKey = new Map(module.sections.map((s) => [s.contentKey, s]));
  for (const expected of LOTTERY_NAV_INTEGRITY) {
    const section = byKey.get(expected.contentKey);
    if (!section) {
      errors.push(`missing section ${expected.contentKey}`);
      continue;
    }
    if (section.legacyHref !== expected.href) {
      errors.push(`${expected.contentKey}: legacyHref=${section.legacyHref} expected ${expected.href}`);
    }
    if ((section.group || "") !== expected.group) {
      errors.push(`${expected.contentKey}: group=${section.group} expected ${expected.group}`);
    }
  }
  for (const section of module.sections) {
    if (!section.legacyHref?.startsWith("/lottery")) {
      errors.push(`${section.contentKey}: missing /lottery legacyHref`);
    }
  }
  return errors;
}

export function filterModuleQuickActions(module: ModuleDefinition): QuickAction[] {
  const visibleIds = new Set(module.sections.filter(isSectionNavVisible).map((s) => s.id));
  return module.defaultQuickActions.filter((qa) => {
    if (!qa.href?.startsWith(`/apps/${module.id}/`)) return true;
    const sectionId = qa.href.split("/")[3]?.split("?")[0];
    return sectionId ? visibleIds.has(sectionId) : true;
  });
}

export function getModuleSection(moduleId: string, sectionId: string) {
  const mod = MODULE_BY_ID[moduleId];
  if (!mod) return null;
  return mod.sections.find((s) => s.id === sectionId) ?? null;
}
