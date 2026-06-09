/**
 * JAIOS QA visual — ejecutar en consola del navegador estando logueado en /odoo
 * Copiar/pegar todo el archivo en DevTools → Console
 */
(async function jaiosQaOdoo() {
  const token = localStorage.getItem("jaios_access_token");
  const tenant = localStorage.getItem("jaios_tenant_id");
  if (!token) {
    console.error("QA FAIL: sin sesión JAIOS");
    return;
  }
  const base = (window.__JAIOS_API__ || "http://localhost:8000/api/v1");
  const headers = {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
    ...(tenant ? { "X-Tenant-ID": tenant } : {}),
  };
  const get = async (path) => {
    const r = await fetch(`${base}${path}`, { headers });
    const b = await r.json().catch(() => ({}));
    return { status: r.status, body: b };
  };
  const rows = (sel) => document.querySelectorAll(`${sel} tbody tr`).length;

  const report = [];
  const summary = await get("/odoo/summary");
  report.push(["Resumen API customers", summary.body.customers]);
  report.push(["Resumen API products", summary.body.products]);

  const tabs = [
    ["clientes", "/odoo/customers?limit=50", null],
    ["productos", "/odoo/products?limit=50", null],
    ["ventas", "/odoo/sales/history?limit=50", null],
    ["facturas_open", "/odoo/invoices/open?limit=50", null],
    ["cotizaciones", "/odoo/quotations?limit=50", null],
    ["oportunidades", "/odoo/opportunities?limit=50", null],
    ["proyectos", "/odoo/projects?limit=50", null],
    ["proveedores", "/odoo/vendors?limit=50", null],
  ];
  for (const [name, path] of tabs) {
    const { status, body } = await get(path);
    report.push([`API ${name}`, status, body.total, body.items?.length ?? 0]);
  }
  const companies = await get("/odoo/companies");
  report.push(["API companies", companies.body.items?.length, companies.body.items?.map((c) => c.name).join(", ")]);

  const me = await get("/odoo/me");
  const m = me.body.user_mapping;
  report.push(["API me linked", m?.odoo_login, m?.odoo_user_id, m?.allowed_company_ids?.length]);

  const dgcp = await get("/dgcp/opportunities?limit=5");
  report.push(["API dgcp", dgcp.status, dgcp.body.total ?? dgcp.body.items?.length]);

  console.table(report);
  console.log("Ahora cambia cada pestaña en /odoo y ejecuta:");
  console.log("  jaiosQaCountRows()  // definido abajo");
  window.jaiosQaCountRows = () => {
    const tables = document.querySelectorAll("table tbody");
    const counts = Array.from(tables).map((tb, i) => [i, tb.querySelectorAll("tr").length]);
    console.table(counts);
    return counts;
  };
  console.log("QA API OK — valida pestañas manualmente y compara items API (50) vs filas visibles");
})();
