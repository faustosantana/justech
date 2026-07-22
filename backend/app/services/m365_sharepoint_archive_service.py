"""Auto-archivo corporativo SharePoint — rutas y metadatos."""

from __future__ import annotations

from app.services.m365_email_classifier import EMAIL_CLASS_LABELS


SHAREPOINT_ROOT = "JAIOS_Corporativo"

FOLDER_BY_CLASSIFICATION: dict[str, str] = {
    "licitacion": "01_LICITACIONES",
    "cotizacion_proveedor": "02_COTIZACIONES",
    "catalogo": "02_COTIZACIONES",
    "factura_proveedor": "03_PROVEEDORES",
    "ficha_tecnica": "05_FICHAS_TECNICAS",
    "documento_legal": "06_DOCUMENTOS_LEGALES",
    "contrato": "06_DOCUMENTOS_LEGALES",
    "factura_cliente": "04_CLIENTES",
    "comprobante_pago": "04_CLIENTES",
    "orden_compra": "04_CLIENTES",
    "presentacion_comercial": "02_COTIZACIONES",
}


class M365SharePointArchiveService:
    def build_path(
        self,
        *,
        classification: str,
        vendor: str | None,
        client: str | None,
        dgcp_code: str | None,
        filename: str,
    ) -> str:
        folder = FOLDER_BY_CLASSIFICATION.get(classification, "06_DOCUMENTOS_LEGALES")
        parts = [SHAREPOINT_ROOT, folder]
        if dgcp_code:
            parts.append(dgcp_code.replace("/", "-"))
        elif client:
            parts.append(client.replace(" ", "_")[:40])
        elif vendor:
            parts.append(vendor.replace(" ", "_")[:40])
        else:
            parts.append("GENERAL")
        parts.append(filename)
        return "/".join(parts)

    def archive_metadata(
        self,
        *,
        classification: str,
        sharepoint_path: str,
        extracted: dict,
        hermes_indexed: bool = True,
    ) -> dict:
        return {
            "sharepoint_path": sharepoint_path,
            "folder": sharepoint_path.split("/")[1] if "/" in sharepoint_path else SHAREPOINT_ROOT,
            "classification": classification,
            "classification_label": EMAIL_CLASS_LABELS.get(classification, classification),
            "indexed": hermes_indexed,
            "versioned": True,
            "embedded_in_hermes": hermes_indexed,
            "vendor": extracted.get("vendor"),
            "client": extracted.get("client"),
            "dgcp_process_code": extracted.get("dgcp_process_code"),
        }
