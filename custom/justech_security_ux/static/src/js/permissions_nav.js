/** @odoo-module **/

import { registry } from "@web/core/registry";

const MODULES = [
    { key: "sales", label: "Ventas", match: ["venta", "cotiz", "descuento", "nota de crédito", "cancelar factura"] },
    { key: "purchase", label: "Compras", match: ["compra", "b11", "b13", "b17", "documento recibido", "orden de compra"] },
    { key: "inventory", label: "Inventario", match: ["inventario", "serial", "lote", "transfer"] },
    { key: "accounting", label: "Contabilidad", match: ["contabilidad", "facturación", "asiento"] },
    { key: "payments", label: "Pagos", match: ["pago", "cobro", "aplicar", "conciliar", "diario", "banco"] },
    { key: "fiscal", label: "Fiscal", match: ["fiscal", "ncf", "anular", "rnc", "606", "607", "608", "609", "623", "rango"] },
    { key: "ecf", label: "e-CF", match: ["e-cf", "ecf", "auditor e-cf"] },
    { key: "withholding", label: "Retenciones", match: ["retencion", "retención", "catálogo"] },
    { key: "warranty", label: "Garantías", match: ["garant"] },
    { key: "fees", label: "Fees", match: ["fee", "recurrent"] },
    { key: "crm", label: "CRM", match: ["crm", "lead"] },
    { key: "hr", label: "RRHH", match: ["rrhh", "empleado", "hr"] },
    { key: "admin", label: "Administración", match: ["admin justech", "consola", "admin center"] },
];

function isOdooHidden(el) {
    return !el || el.classList.contains("o_invisible_modifier");
}

function readFieldText(page, fieldName) {
    const node =
        page.querySelector(`[name="${fieldName}"]`) ||
        page.querySelector(`.o_field_widget[name="${fieldName}"]`);
    if (!node) {
        return "—";
    }
    return ((node.innerText || node.textContent || "").trim() || "—");
}

function enhancePage(page) {
    if (!page || page.dataset.jxEnhanced === "1") {
        return;
    }
    page.dataset.jxEnhanced = "1";

    const toolbar = document.createElement("div");
    toolbar.className = "justech-jx-toolbar justech-jx-nav-widget";
    toolbar.innerHTML = `
      <div class="justech-jx-search-row">
        <label class="justech-jx-search-label" for="justech_jx_search">Buscar permiso</label>
        <input id="justech_jx_search" type="search" class="form-control justech-jx-search" placeholder="aplicar pagos, anular NCF, B13…" />
      </div>
      <div class="justech-jx-chip-row" role="tablist" aria-label="Módulos"></div>
      <div class="justech-jx-actions">
        <button type="button" class="btn btn-secondary btn-sm" data-jx-summary>Resumen general</button>
        <button type="button" class="btn btn-link btn-sm" data-jx-tech>Ver implementación técnica</button>
      </div>
      <div class="justech-jx-search-hint text-muted" data-jx-hint></div>
      <div class="justech-jx-summary-panel d-none" data-jx-summary-panel>
        <div class="justech-jx-summary-head">
          <strong>Resumen general (efectivo)</strong>
          <button type="button" class="btn btn-sm btn-secondary" data-jx-summary-close>Cerrar</button>
        </div>
        <div class="justech-jx-summary-grid">
          <div><div class="justech-jx-summary-title">Módulos con acceso</div><pre class="justech-jx-summary-pre" data-jx-sum-modules></pre></div>
          <div><div class="justech-jx-summary-title">Advertencias</div><pre class="justech-jx-summary-pre" data-jx-sum-warnings></pre></div>
          <div><div class="justech-jx-summary-title">Puede</div><pre class="justech-jx-summary-pre" data-jx-sum-can></pre></div>
          <div><div class="justech-jx-summary-title">No puede</div><pre class="justech-jx-summary-pre" data-jx-sum-cannot></pre></div>
        </div>
      </div>
    `;

    page.insertBefore(toolbar, page.firstChild);

    const chipRow = toolbar.querySelector(".justech-jx-chip-row");
    const hint = toolbar.querySelector("[data-jx-hint]");
    const summaryPanel = toolbar.querySelector("[data-jx-summary-panel]");
    const searchInput = toolbar.querySelector("#justech_jx_search");
    let active = null;
    let showTech = false;

    const sections = () =>
        [...page.querySelectorAll("[data-jx-module]")].filter((s) => !isOdooHidden(s));

    const presentModules = () => {
        const keys = new Set(sections().map((s) => s.dataset.jxModule));
        return MODULES.filter((m) => keys.has(m.key));
    };

    const applyTech = () => {
        page.classList.toggle("justech-jx-show-tech", showTech);
        page.querySelectorAll(".justech-jx-card, .justech-jx-tech").forEach((el) => {
            el.classList.toggle("justech-jx-tech-hidden", !showTech);
        });
        const btn = toolbar.querySelector("[data-jx-tech]");
        if (btn) {
            btn.textContent = showTech
                ? "Ocultar implementación técnica"
                : "Ver implementación técnica";
        }
    };

    const selectModule = (key) => {
        active = key;
        page.querySelectorAll("[data-jx-module]").forEach((section) => {
            const show = section.dataset.jxModule === key;
            section.classList.toggle("justech-jx-section-hidden", !show);
        });
        chipRow.querySelectorAll(".justech-jx-chip").forEach((btn) => {
            const on = btn.dataset.jxKey === key;
            btn.classList.toggle("btn-primary", on);
            btn.classList.toggle("btn-secondary", !on);
            btn.setAttribute("aria-selected", on ? "true" : "false");
        });
        applyTech();
    };

    const renderChips = () => {
        const mods = presentModules();
        chipRow.innerHTML = "";
        mods.forEach((mod) => {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "btn btn-secondary justech-jx-chip";
            btn.dataset.jxKey = mod.key;
            btn.textContent = mod.label;
            btn.addEventListener("click", () => {
                hint.textContent = "";
                page.querySelectorAll(".justech-jx-hit").forEach((el) => el.classList.remove("justech-jx-hit"));
                selectModule(mod.key);
            });
            chipRow.appendChild(btn);
        });
        if (!mods.length) {
            return;
        }
        if (!active || !mods.some((m) => m.key === active)) {
            active = mods[0].key;
        }
        selectModule(active);
    };

    const fillSummary = () => {
        toolbar.querySelector("[data-jx-sum-modules]").textContent = readFieldText(page, "jx_summary_modules");
        toolbar.querySelector("[data-jx-sum-warnings]").textContent = readFieldText(page, "jx_summary_warnings");
        toolbar.querySelector("[data-jx-sum-can]").textContent = readFieldText(page, "jx_summary_can");
        toolbar.querySelector("[data-jx-sum-cannot]").textContent = readFieldText(page, "jx_summary_cannot");
    };

    toolbar.querySelector("[data-jx-summary]").addEventListener("click", () => {
        fillSummary();
        summaryPanel.classList.toggle("d-none");
    });
    toolbar.querySelector("[data-jx-summary-close]").addEventListener("click", () => {
        summaryPanel.classList.add("d-none");
    });
    toolbar.querySelector("[data-jx-tech]").addEventListener("click", () => {
        showTech = !showTech;
        applyTech();
    });

    const runSearch = (qRaw) => {
        const q = (qRaw || "").trim().toLowerCase();
        page.querySelectorAll(".justech-jx-hit").forEach((el) => el.classList.remove("justech-jx-hit"));
        if (q.length < 2) {
            hint.textContent = "";
            return;
        }
        let target = null;
        let hitEl = null;
        for (const mod of MODULES) {
            if (mod.label.toLowerCase().includes(q) || mod.match.some((m) => q.includes(m) || m.includes(q))) {
                target = mod.key;
                break;
            }
        }
        for (const section of sections()) {
            const text = (section.innerText || "").toLowerCase();
            if (!text.includes(q)) {
                continue;
            }
            target = section.dataset.jxModule;
            const candidates = section.querySelectorAll(
                ".o_field_widget, .o_form_label, label, .o_radio_item, .form-check-label, .justech-jx-note"
            );
            for (const c of candidates) {
                if ((c.innerText || "").toLowerCase().includes(q)) {
                    hitEl = c;
                    break;
                }
            }
            if (!hitEl) {
                hitEl = section;
            }
            break;
        }
        if (!target) {
            hint.textContent = `Sin resultados para «${q}».`;
            return;
        }
        selectModule(target);
        if (hitEl) {
            hitEl.classList.add("justech-jx-hit");
            hitEl.scrollIntoView({ behavior: "smooth", block: "center" });
        }
        const modLabel = (MODULES.find((m) => m.key === target) || {}).label || target;
        hint.textContent = `Mostrando ${modLabel}.`;
    };

    searchInput.addEventListener("input", (ev) => runSearch(ev.target.value));
    searchInput.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter") {
            ev.preventDefault();
            runSearch(ev.target.value);
        }
    });

    renderChips();
    applyTech();

    // Re-render chips if Odoo toggles module visibility later
    const obs = new MutationObserver(() => {
        // Keep enhancement stable; only re-sync module list if needed
        const mods = presentModules().map((m) => m.key).join(",");
        if (page.dataset.jxMods !== mods) {
            page.dataset.jxMods = mods;
            renderChips();
        }
    });
    obs.observe(page, { childList: true, subtree: true, attributes: true, attributeFilter: ["class"] });
}

function scan() {
    document.querySelectorAll(".justech-jx-page").forEach((page) => {
        try {
            enhancePage(page);
        } catch (err) {
            // Never break the form for presentation helpers
            console.warn("[justech_security_ux] nav enhance failed", err);
        }
    });
}

registry.category("services").add("justech_permissions_ux", {
    start() {
        scan();
        setInterval(scan, 1200);
        return {};
    },
});
