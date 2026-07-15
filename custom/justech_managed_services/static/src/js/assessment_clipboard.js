/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

async function justechCopyToClipboard(env, action) {
    const text = action.params?.text || "";
    const title = action.params?.title || _t("Copiado");
    try {
        if (navigator?.clipboard?.writeText) {
            await navigator.clipboard.writeText(text);
        } else {
            const area = document.createElement("textarea");
            area.value = text;
            area.setAttribute("readonly", "");
            area.style.position = "absolute";
            area.style.left = "-9999px";
            document.body.appendChild(area);
            area.select();
            document.execCommand("copy");
            document.body.removeChild(area);
        }
        env.services.notification.add(title, { type: "success" });
    } catch (error) {
        env.services.notification.add(
            text || _t("No se pudo copiar automáticamente. Seleccione el texto manualmente."),
            { type: "warning", sticky: true }
        );
    }
}

registry.category("actions").add("justech_copy_to_clipboard", justechCopyToClipboard);
