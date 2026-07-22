"""Fixtures demo — bandeja M365 cuando Graph no está conectado."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def demo_inbox_messages() -> list[dict]:
    now = datetime.now(timezone.utc)
    return [
        {
            "external_message_id": "demo-dell-cotizacion-001",
            "mailbox": "cotizaciones@justech.do",
            "subject": "Adjunto cotización Dell — Latitude y Optiplex",
            "sender_email": "quotes@dell.com",
            "sender_name": "Dell Technologies",
            "received_at": now - timedelta(hours=2),
            "body_text": (
                "Estimados,\n\nAdjunto cotización Dell para proceso DGCP-2026-00125.\n"
                "Productos: Latitude 5450, Optiplex 7020, Monitor 27.\n"
                "Monto total: USD 12,500.00\n"
                "Cliente referencia: Banco Ademi\n\nSaludos."
            ),
            "attachments": [
                {
                    "name": "Cotizacion_Dell_DGCP-2026-00125.pdf",
                    "content_type": "application/pdf",
                    "size_bytes": 245000,
                    "extracted_text": (
                        "Dell Technologies Quote DGCP-2026-00125 Banco Ademi "
                        "Latitude 5450 Optiplex 7020 Monitor 27 USD 12,500.00"
                    ),
                }
            ],
        },
        {
            "external_message_id": "demo-ademi-oc-002",
            "mailbox": "ventas@justech.do",
            "subject": "Orden de compra Banco Ademi — equipos informáticos",
            "sender_email": "compras@bancoademi.com.do",
            "sender_name": "Banco Ademi Compras",
            "received_at": now - timedelta(hours=5),
            "body_text": (
                "Adjuntamos orden de compra PO-2026-458 por USD 8,750.00 "
                "referente a cotización previa."
            ),
            "attachments": [
                {
                    "name": "PO-2026-458.pdf",
                    "content_type": "application/pdf",
                    "extracted_text": "Orden de compra Banco Ademi PO-2026-458 USD 8,750.00",
                }
            ],
        },
        {
            "external_message_id": "demo-factura-proveedor-003",
            "mailbox": "crm@justech.do",
            "subject": "Factura proveedor Lenovo — INV-2026-8891",
            "sender_email": "billing@lenovo.com",
            "sender_name": "Lenovo Billing",
            "received_at": now - timedelta(hours=8),
            "body_text": "Factura INV-2026-8891 por USD 4,200.00 — vencimiento 30 días.",
            "attachments": [
                {
                    "name": "INV-2026-8891.pdf",
                    "content_type": "application/pdf",
                    "extracted_text": "Lenovo Invoice INV-2026-8891 USD 4200 vencimiento 30 dias",
                }
            ],
        },
        {
            "external_message_id": "demo-dgcp-pliego-004",
            "mailbox": "licitaciones@justech.do",
            "subject": "Pliego modificado — DGCP-2026-00125",
            "sender_email": "noreply@dgcp.gob.do",
            "sender_name": "DGCP",
            "received_at": now - timedelta(hours=10),
            "body_text": "Circular de enmienda al pliego del proceso DGCP-2026-00125. Fecha cierre actualizada.",
            "attachments": [
                {
                    "name": "Enmienda_DGCP-2026-00125.pdf",
                    "content_type": "application/pdf",
                    "extracted_text": "Enmienda pliego DGCP-2026-00125 licitacion equipos computo",
                }
            ],
        },
        {
            "external_message_id": "demo-comprobante-005",
            "mailbox": "info@justech.do",
            "subject": "Comprobante de pago — Capital DBG",
            "sender_email": "tesoreria@capitaldbg.com",
            "sender_name": "Capital DBG Tesorería",
            "received_at": now - timedelta(hours=12),
            "body_text": "Comprobante de pago factura FC/2026/00237 por RD$ 125,000.00",
            "attachments": [],
        },
        {
            "external_message_id": "demo-ficha-tecnica-006",
            "mailbox": "cotizaciones@justech.do",
            "subject": "Ficha técnica — Monitor Dell 27 pulgadas",
            "sender_email": "support@dell.com",
            "sender_name": "Dell Support",
            "received_at": now - timedelta(days=1),
            "body_text": "Adjuntamos ficha técnica del monitor propuesto en cotización.",
            "attachments": [
                {"name": "Dell_Monitor_27_Spec.pdf", "content_type": "application/pdf", "extracted_text": "Dell Monitor 27 spec sheet"},
            ],
        },
        {
            "external_message_id": "demo-licitacion-nueva-007",
            "mailbox": "licitaciones@justech.do",
            "subject": "Invitación a participar — equipos de cómputo institución pública",
            "sender_email": "alertas@dgcp.gob.do",
            "sender_name": "DGCP Alertas",
            "received_at": now - timedelta(days=1, hours=3),
            "body_text": "Nueva licitación publicada. Proceso relacionado con equipos Latitude y servicios.",
            "attachments": [],
        },
    ]
