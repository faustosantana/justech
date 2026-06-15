import { apiClient } from "@/lib/api";
import { buildVisibleSectionActivity, isSectionNavVisible } from "./registry";
import type { ModuleDashboardData, ModuleDefinition } from "./types";
import { moduleSectionHref } from "./types";

function fmt(n: number | string | undefined | null): string {
  if (n === undefined || n === null) return "—";
  if (typeof n === "string") return n;
  return n.toLocaleString("es-DO");
}

function emptyDashboard(): ModuleDashboardData {
  return { kpis: [], activity: [], alerts: [] };
}

export async function loadModuleDashboard(module: ModuleDefinition): Promise<ModuleDashboardData> {
  const base = `/apps/${module.id}`;

  try {
    switch (module.id) {
      case "comunicaciones": {
        const [conversations, sessions] = await Promise.allSettled([
          apiClient.listWhatsappConversations(),
          apiClient.listWhatsappSessions(),
        ]);
        const items = conversations.status === "fulfilled" ? conversations.value.items : [];
        const sessionCount = sessions.status === "fulfilled" ? sessions.value.items.length : 0;
        const open = items.filter((c) => c.unread_count > 0).length;
        const urgent = items.filter((c) => (c.ai_priority ?? 0) >= 80).length;
        return {
          kpis: [
            { id: "open", label: "Conversaciones abiertas", value: fmt(items.length), tone: "primary", href: moduleSectionHref("comunicaciones", "conversaciones") },
            { id: "unread", label: "Sin responder", value: fmt(open), tone: open > 0 ? "warning" : "default", href: moduleSectionHref("comunicaciones", "conversaciones") },
            { id: "urgent", label: "Urgentes", value: fmt(urgent), tone: urgent > 0 ? "danger" : "default" },
            { id: "channels", label: "Canales conectados", value: fmt(sessionCount), tone: "success" },
          ],
          activity: items.slice(0, 8).map((c) => ({
            id: c.id,
            title: c.name || c.phone_number || c.remote_jid,
            subtitle: c.last_message_preview || "Sin mensajes",
            href: moduleSectionHref("comunicaciones", "conversaciones"),
          })),
          alerts: open > 5 ? [{ id: "a1", title: `${open} conversaciones requieren respuesta`, subtitle: "Revisa la bandeja unificada" }] : [],
        };
      }

      case "ventas":
      case "facturacion":
      case "inventario": {
        const summary = await apiClient.getOdooSummary();
        const connected = summary.connected;
        return {
          kpis: [
            { id: "cot", label: "Cotizaciones", value: fmt(summary.quotations), href: moduleSectionHref("ventas", "cotizaciones") },
            { id: "ventas", label: "Oportunidades", value: fmt(summary.opportunities), href: moduleSectionHref("crm", "oportunidades") },
            { id: "clientes", label: "Clientes", value: fmt(summary.customers), href: moduleSectionHref("clientes", "empresas") },
            { id: "facturas", label: "Facturas abiertas", value: fmt(summary.open_invoices), tone: summary.overdue_invoices > 0 ? "warning" : "default", href: moduleSectionHref("facturacion", "facturas") },
            { id: "erp", label: "Estado ERP", value: connected ? "Conectado" : "Desconectado", tone: connected ? "success" : "danger" },
          ],
          activity: [],
          alerts: summary.overdue_invoices > 0
            ? [{ id: "ovd", title: `${summary.overdue_invoices} facturas vencidas`, subtitle: "Revisar cuentas por cobrar", href: moduleSectionHref("facturacion", "facturas") }]
            : [],
        };
      }

      case "clientes": {
        const summary = await apiClient.getOdooSummary();
        return {
          kpis: [
            { id: "total", label: "Total clientes", value: fmt(summary.customers), href: moduleSectionHref("clientes", "empresas") },
            { id: "cot", label: "Cotizaciones", value: fmt(summary.quotations), href: moduleSectionHref("clientes", "historial") },
            { id: "opp", label: "Oportunidades", value: fmt(summary.opportunities), href: moduleSectionHref("crm", "oportunidades") },
            { id: "facturas", label: "Facturas abiertas", value: fmt(summary.open_invoices), tone: summary.overdue_invoices > 0 ? "warning" : "default", href: moduleSectionHref("clientes", "facturas") },
            { id: "venc", label: "Facturas vencidas", value: fmt(summary.overdue_invoices), tone: summary.overdue_invoices > 0 ? "danger" : "default", href: moduleSectionHref("clientes", "facturas") },
          ],
          activity: [],
          alerts: [],
        };
      }

      case "crm": {
        const summary = await apiClient.getOdooSummary();
        const connected = summary.connected;
        return {
          kpis: [
            { id: "cot", label: "Cotizaciones", value: fmt(summary.quotations), href: moduleSectionHref("ventas", "cotizaciones") },
            { id: "ventas", label: "Oportunidades", value: fmt(summary.opportunities), href: moduleSectionHref("crm", "oportunidades") },
            { id: "clientes", label: "Clientes", value: fmt(summary.customers), href: moduleSectionHref("clientes", "empresas") },
            { id: "facturas", label: "Facturas abiertas", value: fmt(summary.open_invoices), tone: summary.overdue_invoices > 0 ? "warning" : "default", href: moduleSectionHref("facturacion", "facturas") },
            { id: "erp", label: "Estado ERP", value: connected ? "Conectado" : "Desconectado", tone: connected ? "success" : "danger" },
          ],
          activity: [],
          alerts: summary.overdue_invoices > 0
            ? [{ id: "ovd", title: `${summary.overdue_invoices} facturas vencidas`, subtitle: "Revisar cuentas por cobrar", href: moduleSectionHref("facturacion", "facturas") }]
            : [],
        };
      }

      case "licitaciones": {
        const summary = await apiClient.getDGCPDashboard();
        return {
          kpis: [
            { id: "activos", label: "Procesos activos", value: fmt(summary.total_opportunities), href: moduleSectionHref("licitaciones", "procesos") },
            { id: "potencial", label: "Monto potencial", value: summary.total_potential_amount ?? "—", tone: "primary" },
            { id: "bid", label: "Por licitar", value: fmt(summary.to_bid), tone: "warning" },
            { id: "won", label: "Ganados", value: fmt(summary.won), tone: "success" },
            { id: "lost", label: "Perdidos", value: fmt(summary.lost) },
          ],
          activity: [],
          alerts: summary.to_bid > 0
            ? [{ id: "bid", title: `${summary.to_bid} procesos listos para licitar`, href: moduleSectionHref("licitaciones", "procesos") }]
            : [],
        };
      }

      case "tareas": {
        const res = await apiClient.getTasks({ limit: 100 });
        const pending = res.items.filter((t) => t.status === "pendiente" || t.status === "en_proceso").length;
        const overdue = res.items.filter((t) => t.status === "vencida").length;
        return {
          kpis: [
            { id: "pend", label: "Pendientes", value: fmt(pending), href: moduleSectionHref("tareas", "mis-tareas") },
            { id: "venc", label: "Vencidas", value: fmt(overdue), tone: overdue > 0 ? "danger" : "default", href: moduleSectionHref("tareas", "vencidas") },
            { id: "total", label: "Total", value: fmt(res.total) },
          ],
          activity: res.items.slice(0, 8).map((t) => ({
            id: t.id,
            title: t.title,
            subtitle: t.status,
            href: `/tasks/${t.id}`,
          })),
        };
      }

      case "reportes":
      case "agentes-ia": {
        const data = await apiClient.getExecutiveDashboard();
        return {
          kpis: data.kpis.slice(0, 8).map((k) => ({
            id: k.id,
            label: k.label,
            value: k.value,
            delta: k.delta ?? undefined,
            href: k.href ?? undefined,
            tone: (k.tone as ModuleDashboardData["kpis"][0]["tone"]) ?? "default",
          })),
          activity: data.activity.slice(0, 8).map((a) => ({
            id: a.id,
            title: a.title,
            subtitle: a.subtitle,
            href: a.href ?? undefined,
          })),
          alerts: data.alerts.slice(0, 5).map((a) => ({
            id: a.id,
            title: a.title,
            subtitle: a.source,
            href: a.href,
          })),
        };
      }

      case "precios": {
        const data = await apiClient.getLicitadorPriceIntelligence();
        return {
          kpis: [
            { id: "prod", label: "Productos indexados", value: fmt(data.total_products), tone: "primary", href: moduleSectionHref("precios", "productos") },
            { id: "sup", label: "Proveedores con listas", value: fmt(data.total_suppliers), href: moduleSectionHref("precios", "proveedores") },
            { id: "today", label: "Listas hoy", value: fmt(data.lists_today), tone: data.lists_today > 0 ? "success" : "default", href: moduleSectionHref("precios", "listas") },
            { id: "pend", label: "Pendientes", value: fmt(data.pending_files.length), tone: data.pending_files.length > 0 ? "warning" : "default", href: moduleSectionHref("precios", "listas") },
          ],
          activity: data.processed_files.slice(0, 6).map((f) => ({
            id: f.id,
            title: f.name,
            subtitle: `${f.supplier || "—"} · ${f.records} productos`,
            href: moduleSectionHref("precios", "listas"),
          })),
          alerts: data.recent_errors.slice(0, 3).map((e, i) => ({
            id: `err-${i}`,
            title: e.slice(0, 80),
            subtitle: "Error de indexación",
          })),
        };
      }

      case "proveedores": {
        const [dash, prices] = await Promise.all([
          apiClient.getSupplierDashboard(),
          apiClient.getLicitadorPriceIntelligence(),
        ]);
        return {
          kpis: [
            { id: "total", label: "Proveedores", value: fmt(dash.total_suppliers), href: moduleSectionHref("proveedores", "directorio") },
            { id: "activos", label: "Activos", value: fmt(dash.active_suppliers), tone: "success", href: moduleSectionHref("proveedores", "directorio") },
            { id: "pref", label: "Preferidos", value: fmt(dash.preferred_suppliers), href: moduleSectionHref("proveedores", "directorio") },
            { id: "listas", label: "Productos indexados", value: fmt(prices.total_products), href: moduleSectionHref("proveedores", "listas") },
          ],
          activity: dash.by_category.slice(0, 6).map((c, i) => ({
            id: `cat-${i}`,
            title: c.name,
            subtitle: `${c.count} proveedor(es)`,
            href: moduleSectionHref("proveedores", "directorio"),
          })),
        };
      }

      case "empresas-grupo": {
        const hub = await apiClient.getDocumentsHubDashboard();
        return {
          kpis: [
            { id: "emp", label: "Empresas del grupo", value: fmt(hub.total_companies), href: moduleSectionHref("empresas-grupo", "empresas") },
            { id: "comp", label: "Perfiles completos", value: fmt(hub.companies_complete), tone: "success", href: moduleSectionHref("empresas-grupo", "empresas") },
            { id: "inc", label: "Incompletos", value: fmt(hub.companies_incomplete), tone: hub.companies_incomplete > 0 ? "warning" : "default", href: moduleSectionHref("empresas-grupo", "pendientes") },
            { id: "venc", label: "Docs. vencidos", value: fmt(hub.documents_expired), tone: hub.documents_expired > 0 ? "danger" : "default", href: moduleSectionHref("empresas-grupo", "pendientes") },
            { id: "pend", label: "Pendientes", value: fmt(hub.pending_items_open), tone: "warning", href: moduleSectionHref("empresas-grupo", "pendientes") },
          ],
          activity: (hub.company_cards ?? []).slice(0, 6).map((c) => ({
            id: c.id,
            title: c.razon_social,
            subtitle: `Perfil ${c.completeness_score}% · RNC ${c.rnc || "—"}`,
            href: c.href || `/apps/empresas-grupo/perfil/${c.id}`,
          })),
        };
      }

      case "documentos": {
        const hub = await apiClient.getDocumentsHubDashboard();
        return {
          kpis: [
            { id: "empresas", label: "Empresas del grupo", value: fmt(hub.total_companies), href: moduleSectionHref("empresas-grupo", "empresas") },
            { id: "legales", label: "Docs legales", value: fmt(hub.legal_documents_loaded), href: moduleSectionHref("documentos", "contratos") },
            { id: "pend", label: "Pendientes", value: fmt(hub.pending_items_open), tone: "warning", href: moduleSectionHref("documentos", "certificaciones") },
            { id: "venc", label: "Vencidos", value: fmt(hub.documents_expired), tone: hub.documents_expired > 0 ? "danger" : "default" },
          ],
          activity: (hub.recent_syncs ?? []).slice(0, 8).map((r, i) => ({
            id: `sync-${i}`,
            title: r.label,
            subtitle: `${r.status} · ${r.indexed_files} archivos`,
          })),
        };
      }

      default:
        return {
          kpis: [
            { id: "app", label: module.label, value: "Activo", tone: "primary", href: base },
            {
              id: "sections",
              label: "Secciones",
              value: fmt(module.sections.filter(isSectionNavVisible).length),
            },
          ],
          activity: buildVisibleSectionActivity(module),
        };
    }
  } catch {
    return emptyDashboard();
  }
}
