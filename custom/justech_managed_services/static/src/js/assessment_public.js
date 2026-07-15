/**
 * Navegación multipágina del levantamiento público Justech.
 * Progreso, etiquetas y revisión basados en el schema centralizado.
 */
(function () {
    "use strict";

    // Estático: 16 + revisión. Dinámico: N categorías + revisión (window.JT_MS_SECTION_COUNT).
    const SECTION_COUNT = window.JT_MS_SECTION_COUNT || 17;
    const CONTENT_SECTIONS = Math.max(1, SECTION_COUNT - 1);
    let currentSection = 1;

    function qs(sel, root) {
        return (root || document).querySelector(sel);
    }
    function qsa(sel, root) {
        return Array.from((root || document).querySelectorAll(sel));
    }

    function getToken() {
        const parts = window.location.pathname.split("/").filter(Boolean);
        const idx = parts.indexOf("levantamiento");
        return idx >= 0 ? parts[idx + 1] : "";
    }

    function isFilled(value) {
        if (value === null || value === undefined || value === false) return false;
        if (typeof value === "string" && !value.trim()) return false;
        if (Array.isArray(value) && !value.length) return false;
        return true;
    }

    function collectFormData() {
        const data = {};
        const form = qs("#jt-ms-form");
        if (!form) return data;

        qsa("input, textarea, select", form).forEach((el) => {
            const name = el.name;
            if (!name || el.type === "button" || el.type === "submit") return;

            if (el.type === "checkbox") {
                if (name.endsWith("[]")) {
                    const key = name.slice(0, -2);
                    if (!data[key]) data[key] = [];
                    if (el.checked) data[key].push(el.value);
                } else {
                    data[name] = el.checked;
                }
            } else if (el.type === "radio") {
                if (el.checked) data[name] = el.value;
            } else {
                data[name] = el.value;
            }
        });
        return data;
    }

    function computeCompletionPercent(data) {
        const tracked = window.JT_MS_TRACKED_KEYS || [];
        if (!tracked.length) return 0;
        let filled = 0;
        tracked.forEach((key) => {
            if (isFilled(data[key])) filled += 1;
        });
        return Math.round((filled / tracked.length) * 100);
    }

    function updateProgressUI(sectionNum, completionPct) {
        const fill = qs("#jt-ms-progress-fill");
        const sectionLabel = qs("#jt-ms-progress-text");
        const pctLabel = qs("#jt-ms-progress-pct");
        const pct = Math.max(0, Math.min(100, Number(completionPct) || 0));

        if (fill) fill.style.width = pct + "%";
        if (pctLabel) pctLabel.textContent = pct + "% completado";
        if (sectionLabel) {
            sectionLabel.textContent =
                sectionNum >= SECTION_COUNT
                    ? "Revisión y envío"
                    : "Sección " + sectionNum + " de " + CONTENT_SECTIONS;
        }
    }

    function refreshCompletion(sectionNum) {
        const pct = computeCompletionPercent(collectFormData());
        updateProgressUI(sectionNum != null ? sectionNum : currentSection, pct);
        return pct;
    }

    function showSection(num) {
        currentSection = num;
        qsa(".jt-ms-section").forEach((el) => {
            const section = el.dataset.section;
            const isActive =
                section === "done"
                    ? false
                    : parseInt(section, 10) === num;
            el.classList.toggle("active", isActive);
        });
        refreshCompletion(num);
        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    function prefillForm(values) {
        if (!values) return;
        const form = qs("#jt-ms-form");
        if (!form) return;

        Object.keys(values).forEach((key) => {
            const value = values[key];
            const fields = qsa('[name="' + key + '"], [name="' + key + '[]"]', form);
            if (!fields.length) return;

            fields.forEach((el) => {
                if (el.type === "checkbox" && el.name.endsWith("[]")) {
                    el.checked = Array.isArray(value) && value.includes(el.value);
                } else if (el.type === "checkbox") {
                    el.checked = !!value;
                } else if (el.type === "radio") {
                    el.checked = el.value === String(value);
                } else {
                    el.value = value != null ? value : "";
                }
            });
        });
    }

    function rpc(route, data) {
        return fetch(route, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: { form_data: data },
                id: Date.now(),
            }),
        })
            .then((r) => r.json())
            .then((res) => res.result || res);
    }

    function showMessage(msg, type) {
        const box = qs("#jt-ms-message");
        if (!box) return;
        box.textContent = msg;
        box.className = "jt-ms-alert jt-ms-alert-" + (type || "error");
        box.classList.remove("jt-ms-hidden");
    }

    function hideMessage() {
        const box = qs("#jt-ms-message");
        if (box) box.classList.add("jt-ms-hidden");
    }

    function formatDisplayValue(key, value) {
        const optionLabels = (window.JT_MS_OPTION_LABELS || {})[key] || {};
        if (typeof value === "boolean") return value ? "Sí" : "No";
        if (Array.isArray(value)) {
            return value
                .map((item) => optionLabels[item] || item)
                .filter(Boolean)
                .join(", ");
        }
        if (value != null && optionLabels[value]) return optionLabels[value];
        return value == null ? "" : String(value);
    }

    function escapeHtml(text) {
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function savePartial() {
        const token = getToken();
        hideMessage();
        const data = collectFormData();
        const localPct = refreshCompletion(currentSection);
        return rpc("/servicios/levantamiento/" + token + "/save", data)
            .then((result) => {
                if (result.error) {
                    showMessage(result.message || "No se pudo guardar.", "error");
                    return false;
                }
                const pct =
                    result.completion_percent != null
                        ? Math.round(result.completion_percent)
                        : localPct;
                updateProgressUI(currentSection, pct);
                showMessage("Progreso guardado correctamente.", "success");
                setTimeout(hideMessage, 2500);
                return true;
            })
            .catch(() => {
                showMessage("Error de conexión al guardar.", "error");
                return false;
            });
    }

    function submitForm() {
        const token = getToken();
        const data = collectFormData();
        if (!data.acceptance_confirmed) {
            showMessage("Debe aceptar la confirmación antes de enviar.", "error");
            return;
        }
        if (!data.completed_by_name || !data.completed_by_job) {
            showMessage("Indique nombre y cargo de quien completa.", "error");
            return;
        }
        hideMessage();
        rpc("/servicios/levantamiento/" + token + "/submit", data)
            .then((result) => {
                if (result.error) {
                    showMessage(result.message || "No se pudo enviar.", "error");
                    return;
                }
                qsa(".jt-ms-section").forEach((el) => el.classList.remove("active"));
                const done = qs('[data-section="done"]');
                if (done) done.classList.add("active");
                const nav = qs(".jt-ms-nav");
                if (nav) nav.classList.add("jt-ms-hidden");
                updateProgressUI(SECTION_COUNT, 100);
            })
            .catch(() => showMessage("Error de conexión al enviar.", "error"));
    }

    function buildReview() {
        const container = qs("#jt-ms-review-content");
        if (!container) return;
        const data = collectFormData();
        const labels = window.JT_MS_FIELD_LABELS || {};
        const tracked = window.JT_MS_TRACKED_KEYS || Object.keys(labels);
        let html = "";

        tracked.forEach((key) => {
            if (["acceptance_confirmed"].includes(key)) return;
            const val = data[key];
            if (!isFilled(val) && val !== false) return;
            if (typeof val === "boolean" && val === false) {
                // mostrar "No" para booleanos marcados explícitamente en falso
            }
            const label = labels[key] || key;
            const display = formatDisplayValue(key, val);
            if (!display && typeof val !== "boolean") return;
            html +=
                '<div class="jt-ms-review-block"><h3>' +
                escapeHtml(label) +
                "</h3><p>" +
                escapeHtml(display) +
                "</p></div>";
        });

        // Meta de envío
        ["completed_by_name", "completed_by_job"].forEach((key) => {
            if (!isFilled(data[key])) return;
            html +=
                '<div class="jt-ms-review-block"><h3>' +
                escapeHtml(labels[key] || key) +
                "</h3><p>" +
                escapeHtml(String(data[key])) +
                "</p></div>";
        });

        container.innerHTML = html || "<p>No hay respuestas registradas aún.</p>";
    }

    document.addEventListener("DOMContentLoaded", function () {
        if (window.JT_MS_FORM_VALUES) prefillForm(window.JT_MS_FORM_VALUES);
        showSection(1);

        const form = qs("#jt-ms-form");
        if (form) {
            form.addEventListener("input", function () {
                refreshCompletion(currentSection);
            });
            form.addEventListener("change", function () {
                refreshCompletion(currentSection);
            });
        }

        qs("#jt-ms-btn-prev")?.addEventListener("click", function () {
            if (currentSection > 1) showSection(currentSection - 1);
        });
        qs("#jt-ms-btn-next")?.addEventListener("click", function () {
            if (currentSection < SECTION_COUNT) showSection(currentSection + 1);
            if (currentSection === SECTION_COUNT) buildReview();
        });
        qs("#jt-ms-btn-review")?.addEventListener("click", function () {
            buildReview();
            showSection(SECTION_COUNT);
        });
        qs("#jt-ms-btn-save")?.addEventListener("click", savePartial);
        qs("#jt-ms-btn-submit")?.addEventListener("click", submitForm);
    });
})();
