# -*- coding: utf-8 -*-
from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

from odoo.addons.purchase.controllers.portal import CustomerPortal


class JustechPurchasePortal(CustomerPortal):
    """Vista previa nativa OC Hellenia — iframe + descargar/imprimir como factura."""

    def _purchase_order_get_page_view_values(self, order, access_token, **kwargs):
        values = super()._purchase_order_get_page_view_values(order, access_token, **kwargs)
        jt_preview = kwargs.get("jt_preview") == "1"
        values["jt_report_preview"] = jt_preview
        if jt_preview:
            values["jt_report_html_url"] = order.get_portal_url(suffix="/jt_report_html")
            values["jt_report_pdf_url"] = order.get_portal_url(suffix="/jt_report_pdf")
            values["jt_report_pdf_download_url"] = order.get_portal_url(
                suffix="/jt_report_pdf", download=True
            )
        return values

    def _jt_po_official_report_html(self, order_sudo, download=False):
        report_ref = "purchase.action_report_purchase_order"
        return self._show_report(
            model=order_sudo,
            report_type="html",
            report_ref=report_ref,
            download=download,
        )

    def _jt_po_official_report_pdf(self, order_sudo, download=False):
        report_ref = "purchase.action_report_purchase_order"
        return self._show_report(
            model=order_sudo,
            report_type="pdf",
            report_ref=report_ref,
            download=download,
        )

    @http.route(
        ["/my/purchase/<int:order_id>/jt_report_html"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_purchase_order_jt_report_html(self, order_id, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access(
                "purchase.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")
        return self._jt_po_official_report_html(order_sudo)

    @http.route(
        ["/my/purchase/<int:order_id>/jt_report_pdf"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_purchase_order_jt_report_pdf(self, order_id, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access(
                "purchase.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")
        return self._jt_po_official_report_pdf(
            order_sudo, download=bool(kw.get("download"))
        )
