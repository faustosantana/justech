import { Sidebar } from "@portal/interactions/sidebar";
import { registry } from "@web/core/registry";
import { scrollTo } from "@web/core/utils/scrolling";

export class PurchaseSidebar extends Sidebar {
    static selector = ".o_portal_purchase_sidebar";

    dynamicContent = {
        _window: { "t-on-resize": this.updateIframeSize },
        ".o_portal_po_print": { "t-on-click.prevent.withTarget": this.onPurchasePrintClick },
    };

    setup() {
        super.setup();
        this.purchaseHTMLEl = undefined;
    }

    start() {
        super.start();
        this.purchaseHTMLEl = document.getElementById("purchase_order_html");
        if (!this.purchaseHTMLEl) {
            return;
        }
        const iframeDoc =
            this.purchaseHTMLEl.contentDocument ||
            this.purchaseHTMLEl.contentWindow.document;
        if (iframeDoc.readyState === "complete") {
            this.updateIframeSize();
        } else {
            this.addListener(this.purchaseHTMLEl, "load", this.updateIframeSize);
        }
    }

    updateIframeSize() {
        if (!this.purchaseHTMLEl?.contentDocument) {
            return;
        }
        const wrapwrapEl =
            this.purchaseHTMLEl.contentDocument.querySelector("div#wrapwrap");
        if (!wrapwrapEl) {
            return;
        }
        this.purchaseHTMLEl.height = 0;
        this.purchaseHTMLEl.height = wrapwrapEl.scrollHeight;
        const isAnchor = /^#[\w-]+$/.test(window.location.hash);
        if (!isAnchor) {
            return;
        }
        const targetEl = document.querySelector(window.location.hash);
        if (targetEl) {
            scrollTo(targetEl, { behavior: "instant" });
        }
    }

    onPurchasePrintClick(ev, currentTargetEl) {
        this.printIframeContent(currentTargetEl.getAttribute("href"));
    }
}

registry
    .category("public.interactions")
    .add("justech_report_design.purchase_sidebar", PurchaseSidebar);
