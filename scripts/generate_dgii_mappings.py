#!/usr/bin/env python3
"""Generate DGII format mapping JSON files (Fase 17.5)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAPPINGS_DIR = ROOT / "data/localizations/do/mappings"
TEMPLATES_JSON = ROOT / "data/localizations/do/templates/templates.json"

# Standard Odoo fields available without Justech localization (verified: not in JAIOS repo).
ODOO_STANDARD = {
    "partner_vat": "res.partner.vat",
    "partner_name": "res.partner.name",
    "move_name": "account.move.name",
    "move_ref": "account.move.ref",
    "invoice_date": "account.move.invoice_date",
    "invoice_date_due": "account.move.invoice_date_due",
    "amount_untaxed": "account.move.amount_untaxed",
    "amount_tax": "account.move.amount_tax",
    "amount_total": "account.move.amount_total",
    "amount_residual": "account.move.amount_residual",
    "move_type": "account.move.move_type",
    "state": "account.move.state",
    "payment_state": "account.move.payment_state",
    "company_vat": "res.company.vat",
    "payment_date": "account.payment.date",
    "payment_amount": "account.payment.amount",
    "journal_id": "account.move.journal_id",
    "currency_id": "account.move.currency_id",
    "line_tax_ids": "account.move.line.tax_ids",
    "line_balance": "account.move.line.balance",
}

# Referenced in Hellenia Fase 18 (Odoo TEST) but NOT present in this repository.
JUSTECH_HELLENIA_REF = {
    "withholding_catalog": "hellenia.withholding.catalog",
    "withholding_lines": "account.move / payment withholding lines (hellenia)",
}


def meta(zip_name: str) -> dict:
    data = json.loads(TEMPLATES_JSON.read_text())
    for p in data["plantillas"]:
        if p["archivo"] == zip_name:
            return p
    return {}


def col(
    orden: int,
    columna: str,
    nombre: str,
    tipo: str,
    *,
    longitud: int | None = None,
    formato: str | None = None,
    obligatorio: bool = False,
    catalogo: str | None = None,
    odoo: str | None = None,
    odoo_notas: str | None = None,
    faltante: str | None = None,
) -> dict:
    item = {
        "orden": orden,
        "columna_excel": columna,
        "nombre_dgii": nombre,
        "tipo_dato": tipo,
        "obligatorio": obligatorio,
    }
    if longitud is not None:
        item["longitud"] = longitud
    if formato:
        item["formato"] = formato
    if catalogo:
        item["catalogo"] = catalogo
    if odoo:
        item["campo_odoo_sugerido"] = odoo
    if odoo_notas:
        item["notas_mapeo"] = odoo_notas
    if faltante:
        item["campo_faltante"] = faltante
    return item


def base_mapping(
    codigo: str,
    nombre: str,
    zip_name: str,
    excel_name: str,
    hoja: str,
    header_row: int,
    data_start: int,
    columnas: list[dict],
    **extra,
) -> dict:
    m = meta(zip_name)
    out = {
        "schema_version": "1.0",
        "fase": "17.5",
        "fecha_mapeo_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "codigo": codigo,
        "nombre_oficial": nombre,
        "normativa": m.get("version") or "NG-07-2018",
        "archivo_fuente": zip_name,
        "archivo_excel_interno": excel_name,
        "sha256_plantilla": m.get("sha256"),
        "url_oficial": m.get("url_oficial"),
        "hoja_principal": hoja,
        "fila_encabezado": header_row,
        "fila_inicio_datos": data_start,
        "formato_fecha": "YYYYMMDD",
        "formato_periodo": "YYYYMM",
        "formato_rnc": "9 dígitos numéricos (persona jurídica)",
        "formato_cedula": "11 dígitos numéricos (persona física)",
        "formato_ncf": "Serie alfanumérica 11-13 caracteres (ej. B0100000001)",
        "columnas": columnas,
        "macros": extra.get("macros", False),
        "formulas_en_plantilla": extra.get("formulas", False),
        "validaciones": extra.get("validaciones", []),
        "catalogos": extra.get("catalogos", {}),
        "totales": extra.get("totales", []),
        "reglas_negocio": extra.get("reglas_negocio", []),
        "notas_dgii": extra.get("notas_dgii", []),
        "campos_odoo_referencia": ODOO_STANDARD,
        "modulos_justech_referencia": JUSTECH_HELLENIA_REF,
        "campos_faltantes": extra.get("campos_faltantes", []),
        "estado_exportador": extra.get("estado_exportador", "requiere_campos_faltantes"),
    }
    if extra.get("hojas_auxiliares"):
        out["hojas_auxiliares"] = extra["hojas_auxiliares"]
    return out


def mapping_606() -> dict:
    zip_name = "Formato-de-Envio-606-(NG-07-2018-y-05-2019).zip"
    cols = [
        col(1, "A", "Líneas", "integer", obligatorio=True, odoo_notas="Secuencia autogenerada por exportador"),
        col(2, "B", "RNC o Cédula", "identifier", longitud=11, obligatorio=True, odoo=ODOO_STANDARD["partner_vat"]),
        col(3, "C", "Tipo Id", "catalog", longitud=1, obligatorio=True, catalogo="tipo_identificacion", faltante="justech_do_partner_id_type"),
        col(4, "D", "Tipo Bienes y Servicios Comprados", "catalog", longitud=2, obligatorio=True, catalogo="tipo_bienes_servicios", faltante="justech_do_expense_type_606"),
        col(5, "E", "NCF", "ncf", longitud=13, obligatorio=True, faltante="justech_do_ncf / l10n_do e-CF number"),
        col(6, "F", "NCF ó Documento Modificado", "ncf", longitud=13, obligatorio=False, faltante="justech_do_ncf_modified"),
        col(7, "G", "Fecha Comprobante", "date", longitud=8, formato="YYYYMMDD", obligatorio=True, odoo=ODOO_STANDARD["invoice_date"]),
        col(8, "I", "Fecha Pago", "date", longitud=8, formato="YYYYMMDD", obligatorio=False, odoo=ODOO_STANDARD["payment_date"], odoo_notas="Solo si forma de pago implica pago en el período"),
        col(9, "K", "Monto Facturado en Servicios", "decimal", longitud=18, formato="0.00", obligatorio=False, odoo_notas="Derivar de account.move.line por tipo producto servicio"),
        col(10, "L", "Monto Facturado en Bienes", "decimal", longitud=18, formato="0.00", obligatorio=False, odoo_notas="Derivar de account.move.line por tipo producto almacenable/consumible"),
        col(11, "M", "Total Monto Facturado", "decimal", longitud=18, formato="0.00", obligatorio=True, odoo=ODOO_STANDARD["amount_untaxed"]),
        col(12, "N", "ITBIS Facturado", "decimal", longitud=18, formato="0.00", obligatorio=True, odoo=ODOO_STANDARD["amount_tax"], odoo_notas="Solo componente ITBIS 18%"),
        col(13, "O", "ITBIS Retenido", "decimal", longitud=18, formato="0.00", obligatorio=False, odoo=JUSTECH_HELLENIA_REF["withholding_lines"], odoo_notas="Retención ITBIS en compras"),
        col(14, "P", "ITBIS sujeto a Proporcionalidad (Art. 349)", "decimal", longitud=18, formato="0.00", obligatorio=False, faltante="justech_do_itbis_proportionality"),
        col(15, "Q", "ITBIS llevado al Costo", "decimal", longitud=18, formato="0.00", obligatorio=False, faltante="justech_do_itbis_cost"),
        col(16, "R", "ITBIS por Adelantar", "decimal", longitud=18, formato="0.00", obligatorio=False, faltante="justech_do_itbis_advance"),
        col(17, "S", "ITBIS percibido en compras", "decimal", longitud=18, formato="0.00", obligatorio=False, faltante="justech_do_itbis_perceived_purchase"),
        col(18, "T", "Tipo de Retención en ISR", "catalog", longitud=2, obligatorio=False, catalogo="tipo_retencion_isr", odoo=JUSTECH_HELLENIA_REF["withholding_catalog"]),
        col(19, "U", "Monto Retención Renta", "decimal", longitud=18, formato="0.00", obligatorio=False, odoo=JUSTECH_HELLENIA_REF["withholding_lines"]),
        col(20, "V", "ISR Percibido en compras", "decimal", longitud=18, formato="0.00", obligatorio=False, faltante="justech_do_isr_perceived_purchase"),
        col(21, "W", "Impuesto Selectivo al Consumo", "decimal", longitud=18, formato="0.00", obligatorio=False, faltante="justech_do_isc_amount"),
        col(22, "X", "Otros Impuesto/Tasas", "decimal", longitud=18, formato="0.00", obligatorio=False, odoo_notas="Otros impuestos no ITBIS/ISR en líneas de factura"),
        col(23, "Y", "Monto Propina Legal", "decimal", longitud=18, formato="0.00", obligatorio=False, faltante="justech_do_legal_tip"),
        col(24, "Z", "Forma de Pago", "catalog", longitud=2, obligatorio=True, catalogo="forma_pago", faltante="justech_do_payment_method_dgii"),
        col(25, "AA", "Estatus", "catalog", longitud=1, obligatorio=True, catalogo="estatus_linea", faltante="justech_do_dgii_line_status"),
    ]
    return base_mapping(
        "606",
        "Formato de Envío de Compras de Bienes y Servicios",
        zip_name,
        "Formato-de-Envio-606-(NG-07-2018-y-05-2019).xls",
        "Herramienta Formato 606",
        11,
        12,
        cols,
        hojas_auxiliares=["UtilitarioP"],
        macros=False,
        formulas=False,
        catalogos={
            "tipo_identificacion": [
                {"codigo": "1", "descripcion": "RNC"},
                {"codigo": "2", "descripcion": "Cédula"},
            ],
            "tipo_bienes_servicios": [
                {"codigo": "01", "descripcion": "GASTOS DE PERSONAL"},
                {"codigo": "02", "descripcion": "GASTOS POR TRABAJOS, SUMINISTROS Y SERVICIOS"},
                {"codigo": "03", "descripcion": "ARRENDAMIENTOS"},
                {"codigo": "04", "descripcion": "GASTOS DE ACTIVOS FIJO"},
                {"codigo": "05", "descripcion": "GASTOS DE REPRESENTACIÓN"},
                {"codigo": "06", "descripcion": "OTRAS DEDUCCIONES ADMITIDAS"},
                {"codigo": "07", "descripcion": "GASTOS FINANCIEROS"},
                {"codigo": "08", "descripcion": "GASTOS EXTRAORDINARIOS"},
                {"codigo": "09", "descripcion": "COMPRAS Y GASTOS QUE FORMARAN PARTE DEL COSTO DE VENTA"},
                {"codigo": "10", "descripcion": "ADQUISICIONES DE ACTIVOS"},
                {"codigo": "11", "descripcion": "GASTOS DE SEGUROS"},
            ],
            "tipo_retencion_isr": [
                {"codigo": "01", "descripcion": "ALQUILERES"},
                {"codigo": "02", "descripcion": "HONORARIOS POR SERVICIOS"},
                {"codigo": "03", "descripcion": "OTRAS RENTAS"},
                {"codigo": "04", "descripcion": "OTRAS RENTAS (Rentas Presuntas)"},
                {"codigo": "05", "descripcion": "INTERESES PAGADOS A PERSONAS JURIDICAS RESIDENTES"},
                {"codigo": "06", "descripcion": "INTERESES PAGADOS A PERSONAS FISICAS RESIDENTES"},
                {"codigo": "07", "descripcion": "RETENCION POR PROVEEDORES DEL ESTADO"},
                {"codigo": "08", "descripcion": "JUEGOS TELEFONICOS"},
                {"codigo": "09", "descripcion": "RETENCIONES SUBSECTOR DE GANADERÍA DE CARNE BOVINA"},
            ],
            "forma_pago": [
                {"codigo": "01", "descripcion": "EFECTIVO"},
                {"codigo": "02", "descripcion": "CHEQUES/TRANSFERENCIAS/DEPÓSITO"},
                {"codigo": "03", "descripcion": "TARJETA CRÉDITO/DÉBITO"},
                {"codigo": "04", "descripcion": "COMPRA A CREDITO"},
                {"codigo": "05", "descripcion": "PERMUTA"},
                {"codigo": "06", "descripcion": "NOTA DE CREDITO"},
                {"codigo": "07", "descripcion": "MIXTO"},
            ],
            "estatus_linea": [
                {"codigo": "1", "descripcion": "Válido"},
                {"codigo": "2", "descripcion": "Anulado / No incluir en archivo final"},
            ],
        },
        validaciones=[
            "Columna H reservada/vacía en plantilla oficial; no exportar datos en H.",
            "Fecha Comprobante y Fecha Pago en formato AAAAMMDD sin separadores.",
            "RNC 9 dígitos; Cédula 11 dígitos según Tipo Id.",
            "NCF debe corresponder a comprobante de proveedor (facturas vendor bills in_invoice).",
            "Monto servicios + bienes debe coincidir con Total Monto Facturado.",
            "Solo facturas de compra del período reportado.",
            "Plantilla incluye contador de errores (celda K6/K7) y validación interna DGII.",
        ],
        totales=[
            {"campo": "Cantidad Registros", "celda": "C6", "descripcion": "Total líneas válidas"},
            {"campo": "Lineas de Error", "celda": "K6", "descripcion": "Conteo de errores de validación"},
        ],
        reglas_negocio=[
            "Incluir facturas de proveedores (vendor bills) con NCF recibido.",
            "Notas de crédito de proveedor usan forma de pago 06 y NCF modificado.",
            "Retenciones ISR/ITBIS deben cuadrar con comprobantes de retención si aplican.",
            "Clasificación tipo bienes/servicios (col D) es deducible fiscalmente — requiere regla contable.",
            "Versión plantilla analizada: 2025.",
        ],
        notas_dgii=[
            "Norma General 07-2018 y modificación 05-2019.",
            "Encabezado: RNC declarante (A4), Período YYYYMM (A5).",
            "Hoja UtilitarioP contiene lista de períodos; no es hoja de exportación.",
            "Columnas AD-AF en plantilla son listas auxiliares de catálogo, no columnas de archivo TXT.",
        ],
        campos_faltantes=[
            "justech_do_ncf",
            "justech_do_partner_id_type",
            "justech_do_expense_type_606",
            "justech_do_ncf_modified",
            "justech_do_itbis_proportionality",
            "justech_do_itbis_cost",
            "justech_do_itbis_advance",
            "justech_do_itbis_perceived_purchase",
            "justech_do_isr_perceived_purchase",
            "justech_do_isc_amount",
            "justech_do_legal_tip",
            "justech_do_payment_method_dgii",
            "justech_do_dgii_line_status",
        ],
        estado_exportador="requiere_campos_faltantes",
    )


def mapping_607() -> dict:
    zip_name = "Formato-de-Envio-607-(NG-07-2018-y-05-2019).zip"
    cols = [
        col(1, "A", "No", "integer", obligatorio=True, odoo_notas="Secuencia autogenerada"),
        col(2, "B", "RNC/Cédula o Pasaporte", "identifier", longitud=11, obligatorio=True, odoo=ODOO_STANDARD["partner_vat"]),
        col(3, "C", "Tipo Identificación", "catalog", longitud=1, obligatorio=True, catalogo="tipo_identificacion", faltante="justech_do_partner_id_type"),
        col(4, "D", "Número Comprobante Fiscal", "ncf", longitud=13, obligatorio=True, faltante="justech_do_ncf"),
        col(5, "E", "Número Comprobante Fiscal Modificado", "ncf", longitud=13, obligatorio=False, faltante="justech_do_ncf_modified"),
        col(6, "F", "Tipo de Ingreso", "catalog", longitud=2, obligatorio=True, catalogo="tipo_ingreso", faltante="justech_do_income_type_607"),
        col(7, "G", "Fecha Comprobante", "date", longitud=8, formato="YYYYMMDD", obligatorio=True, odoo=ODOO_STANDARD["invoice_date"]),
        col(8, "H", "Fecha de Retención", "date", longitud=8, formato="YYYYMMDD", obligatorio=False, faltante="justech_do_withholding_date"),
        col(9, "I", "Monto Facturado", "decimal", longitud=18, formato="0.00", obligatorio=True, odoo=ODOO_STANDARD["amount_untaxed"]),
        col(10, "J", "ITBIS Facturado", "decimal", longitud=18, formato="0.00", obligatorio=True, odoo=ODOO_STANDARD["amount_tax"]),
        col(11, "K", "ITBIS Retenido por Terceros", "decimal", longitud=18, formato="0.00", obligatorio=False, faltante="justech_do_itbis_withheld_by_third"),
        col(12, "L", "ITBIS Percibido", "decimal", longitud=18, formato="0.00", obligatorio=False, faltante="justech_do_itbis_perceived_sale"),
        col(13, "M", "Retención Renta por Terceros", "decimal", longitud=18, formato="0.00", obligatorio=False, faltante="justech_do_isr_withheld_by_third"),
        col(14, "N", "ISR Percibido", "decimal", longitud=18, formato="0.00", obligatorio=False, faltante="justech_do_isr_perceived_sale"),
        col(15, "O", "Impuesto Selectivo al Consumo", "decimal", longitud=18, formato="0.00", obligatorio=False, faltante="justech_do_isc_amount"),
        col(16, "P", "Otros Impuestos/Tasas", "decimal", longitud=18, formato="0.00", obligatorio=False),
        col(17, "Q", "Monto Propina Legal", "decimal", longitud=18, formato="0.00", obligatorio=False, faltante="justech_do_legal_tip"),
        col(18, "R", "Efectivo", "decimal", longitud=18, formato="0.00", obligatorio=False, faltante="justech_do_sale_payment_breakdown"),
        col(19, "S", "Cheque/ Transferencia/ Depósito", "decimal", longitud=18, formato="0.00", obligatorio=False, faltante="justech_do_sale_payment_breakdown"),
        col(20, "T", "Tarjeta Débito/Crédito", "decimal", longitud=18, formato="0.00", obligatorio=False, faltante="justech_do_sale_payment_breakdown"),
        col(21, "U", "Venta a Crédito", "decimal", longitud=18, formato="0.00", obligatorio=False, faltante="justech_do_sale_payment_breakdown"),
        col(22, "V", "Bonos o Certificados de Regalo", "decimal", longitud=18, formato="0.00", obligatorio=False, faltante="justech_do_sale_payment_breakdown"),
        col(23, "W", "Permuta", "decimal", longitud=18, formato="0.00", obligatorio=False, faltante="justech_do_sale_payment_breakdown"),
        col(24, "X", "Otras Formas de Ventas", "decimal", longitud=18, formato="0.00", obligatorio=False, faltante="justech_do_sale_payment_breakdown"),
        col(25, "Y", "Estatus", "catalog", longitud=1, obligatorio=True, catalogo="estatus_linea", faltante="justech_do_dgii_line_status"),
    ]
    return base_mapping(
        "607",
        "Formato de Envío de Ventas de Bienes y Servicios",
        zip_name,
        "Herramienta de Envio Formato 607.xls",
        "Herramienta Formato 607",
        11,
        12,
        cols,
        macros=False,
        catalogos={
            "tipo_identificacion": [
                {"codigo": "1", "descripcion": "RNC"},
                {"codigo": "2", "descripcion": "Cédula"},
                {"codigo": "3", "descripcion": "Pasaporte"},
            ],
            "tipo_ingreso": [
                {"codigo": "01", "descripcion": "Ingresos por Operaciones (No Financieros)"},
                {"codigo": "02", "descripcion": "Ingresos Financieros"},
                {"codigo": "03", "descripcion": "Ingresos Extraordinarios"},
                {"codigo": "04", "descripcion": "Ingresos por Arrendamientos"},
                {"codigo": "05", "descripcion": "Ingresos por Venta de Activo Depreciable"},
                {"codigo": "06", "descripcion": "Otros Ingresos"},
            ],
            "estatus_linea": [
                {"codigo": "1", "descripcion": "Válido"},
                {"codigo": "2", "descripcion": "Anulado"},
            ],
        },
        validaciones=[
            "Suma de columnas R-X (formas de venta) debe igualar Monto Facturado + ITBIS Facturado según reglas DGII.",
            "Solo facturas de cliente (out_invoice / out_refund) del período.",
            "Versión plantilla analizada: 2023.1.1.",
        ],
        totales=[
            {"campo": "Cantidad Registros", "celda": "C6"},
            {"campo": "Valor Calculado", "celda": "E6"},
            {"campo": "Total Errores", "celda": "G6"},
        ],
        reglas_negocio=[
            "Desglose de formas de pago es obligatorio cuando hay cobros en el período.",
            "Notas de crédito referencian NCF modificado.",
            "Tipo de ingreso depende de naturaleza de la cuenta de ingreso — requiere mapeo contable.",
        ],
        notas_dgii=[
            "Norma General 07-2018 y 05-2019.",
            "Encabezado: RNC (A4), Período YYYYMM (A5).",
        ],
        campos_faltantes=[
            "justech_do_ncf",
            "justech_do_partner_id_type",
            "justech_do_income_type_607",
            "justech_do_ncf_modified",
            "justech_do_withholding_date",
            "justech_do_itbis_withheld_by_third",
            "justech_do_itbis_perceived_sale",
            "justech_do_isr_withheld_by_third",
            "justech_do_isr_perceived_sale",
            "justech_do_isc_amount",
            "justech_do_legal_tip",
            "justech_do_sale_payment_breakdown",
            "justech_do_dgii_line_status",
        ],
        estado_exportador="requiere_campos_faltantes",
    )


def mapping_608() -> dict:
    zip_name = "Formato-de-Envio-608-(NG-07-2018-y-05-2019).zip"
    cols = [
        col(1, "A", "Líneas", "integer", obligatorio=True),
        col(2, "B", "Número de Comprobante Fiscal", "ncf", longitud=13, obligatorio=True, faltante="justech_do_ncf"),
        col(3, "D", "Fecha de Comprobante", "date", longitud=8, formato="YYYYMMDD", obligatorio=True, odoo=ODOO_STANDARD["invoice_date"]),
        col(4, "E", "Tipo de Anulación", "catalog", longitud=2, obligatorio=True, catalogo="tipo_anulacion", faltante="justech_do_ncf_cancel_type"),
        col(5, "G", "Estatus", "catalog", longitud=1, obligatorio=True, catalogo="estatus_linea", faltante="justech_do_dgii_line_status"),
    ]
    return base_mapping(
        "608",
        "Formato de Envío de Comprobantes Fiscales Anulados",
        zip_name,
        "Herramienta de envio Formato 608.xls",
        "Formato 608",
        11,
        12,
        cols,
        macros=False,
        catalogos={
            "tipo_anulacion": [
                {"codigo": "01", "descripcion": "Anulación por secuencia no utilizada"},
                {"codigo": "02", "descripcion": "Errores de Impresión (Factura Pre-Impresa)"},
                {"codigo": "03", "descripcion": "Impresión Defectuosa"},
                {"codigo": "04", "descripcion": "Corrección de la Información"},
                {"codigo": "05", "descripcion": "Cambio de Productos"},
                {"codigo": "06", "descripcion": "Devolución de Productos"},
                {"codigo": "07", "descripcion": "Omisión de Productos"},
                {"codigo": "08", "descripcion": "Errores en Secuencias de NCF"},
                {"codigo": "09", "descripcion": "Por Cese de Operaciones"},
                {"codigo": "10", "descripcion": "Pérdida O Hurto De Talonario(s)"},
            ],
            "estatus_linea": [
                {"codigo": "1", "descripcion": "Válido"},
                {"codigo": "2", "descripcion": "Anulado"},
            ],
        },
        validaciones=[
            "Columna C reservada/vacía en plantilla oficial.",
            "Solo NCF anulados en el período, no ventas activas.",
            "Versión plantilla: 2018.2.1.",
        ],
        reglas_negocio=[
            "Fuente: facturas canceladas/anuladas en Odoo (state=cancel) o módulo NCF con motivo de anulación.",
            "Debe existir trazabilidad del NCF original emitido.",
        ],
        notas_dgii=[
            "Reporte independiente del 607; solo comprobantes anulados.",
            "Encabezado: RNC (A5), Período (A6).",
        ],
        campos_faltantes=[
            "justech_do_ncf",
            "justech_do_ncf_cancel_type",
            "justech_do_dgii_line_status",
        ],
        estado_exportador="requiere_campos_faltantes",
    )


def mapping_609() -> dict:
    zip_name = "Formato609-NG-7-18.zip"
    cols = [
        col(1, "A", "Lineas", "integer", obligatorio=True),
        col(2, "B", "Nombre / Razón Social", "string", longitud=80, obligatorio=True, odoo=ODOO_STANDARD["partner_name"]),
        col(3, "D", "Tipo ID Tributaria", "catalog", longitud=1, obligatorio=True, catalogo="tipo_id_tributaria", faltante="justech_do_foreign_id_type"),
        col(4, "E", "ID Tributaria", "string", longitud=20, obligatorio=True, odoo=ODOO_STANDARD["partner_vat"]),
        col(5, "F", "País de Destino", "catalog", longitud=3, obligatorio=True, catalogo="pais_destino", faltante="justech_do_country_dgii_code"),
        col(6, "G", "Tipo de Servicio Adquirido", "catalog", longitud=2, obligatorio=True, catalogo="tipo_servicio", faltante="justech_do_foreign_service_type"),
        col(7, "H", "Detalle del Servicio Adquirido", "string", longitud=100, obligatorio=True, odoo_notas="Descripción de líneas de factura"),
        col(8, "I", "Parte Relacionada", "catalog", longitud=1, obligatorio=True, catalogo="parte_relacionada", faltante="justech_do_related_party"),
        col(9, "J", "Número de Documento", "string", longitud=20, obligatorio=True, odoo=ODOO_STANDARD["move_name"]),
        col(10, "K", "Fecha de Documento", "date", longitud=8, formato="YYYYMMDD", obligatorio=True, odoo=ODOO_STANDARD["invoice_date"]),
        col(11, "L", "Monto Facturado", "decimal", longitud=18, formato="0.00", obligatorio=True, odoo=ODOO_STANDARD["amount_untaxed"]),
        col(12, "M", "Fecha de Retención ISR", "date", longitud=8, formato="YYYYMMDD", obligatorio=False, faltante="justech_do_isr_withholding_date"),
        col(13, "N", "Renta Presunta", "decimal", longitud=18, formato="0.00", obligatorio=False, faltante="justech_do_presumed_income"),
        col(14, "O", "ISR Retenido", "decimal", longitud=18, formato="0.00", obligatorio=False, odoo=JUSTECH_HELLENIA_REF["withholding_lines"]),
        col(15, "P", "Estatus", "catalog", longitud=1, obligatorio=True, catalogo="estatus_linea", faltante="justech_do_dgii_line_status"),
    ]
    return base_mapping(
        "609",
        "Formato de Envío de Pagos al Exterior",
        zip_name,
        "Herramienta de Envio Formato 609.xlsm",
        "Formato 609",
        11,
        12,
        cols,
        hojas_auxiliares=["Listas"],
        macros=True,
        formulas=False,
        catalogos={
            "tipo_id_tributaria": [
                {"codigo": "1", "descripcion": "RNC"},
                {"codigo": "2", "descripcion": "Cédula"},
                {"codigo": "3", "descripcion": "Pasaporte / ID extranjero"},
            ],
            "parte_relacionada": [
                {"codigo": "1", "descripcion": "Sí"},
                {"codigo": "2", "descripcion": "No"},
            ],
            "pais_destino": "Ver hoja Listas — códigos ISO numéricos DGII (ej. 276=Alemania)",
            "tipo_servicio": "Ver hoja Listas — catálogo Código Servicio",
        },
        validaciones=[
            "Columna C reservada/vacía en numeración oficial.",
            "Proveedores extranjeros sin RNC dominicano.",
            "Archivo .xlsm contiene macros VBA de validación DGII.",
            "Versión plantilla: 2018.5.0.",
        ],
        reglas_negocio=[
            "Aplica a pagos por servicios al exterior con retención ISR.",
            "Requiere catálogo de países y tipos de servicio de hoja Listas.",
            "Investigación contable: identificar facturas de proveedores extranjeros vs locales.",
        ],
        notas_dgii=[
            "Norma General 07-2018 — vigente desde mayo 2018.",
            "Reemplaza versión pre-2018 (PagosalExterior609.zip).",
        ],
        campos_faltantes=[
            "justech_do_foreign_id_type",
            "justech_do_country_dgii_code",
            "justech_do_foreign_service_type",
            "justech_do_related_party",
            "justech_do_isr_withholding_date",
            "justech_do_presumed_income",
            "justech_do_dgii_line_status",
        ],
        estado_exportador="requiere_investigacion_contable",
    )


def mapping_623() -> dict:
    zip_name = "FormatoenvioRetencionesEstado623.zip"
    cols = [
        col(1, "A", "Líneas", "integer", obligatorio=True),
        col(2, "B", "RNC Entidad del Estado", "identifier", longitud=9, obligatorio=True, faltante="justech_do_state_entity_rnc"),
        col(3, "C", "Período", "period", longitud=6, formato="YYYYMM", obligatorio=True, odoo_notas="Período del wizard de exportación"),
        col(4, "D", "Fecha de Retención", "date", longitud=8, formato="YYYYMMDD", obligatorio=True, faltante="justech_do_state_withholding_date"),
        col(5, "E", "Valor de Retención", "decimal", longitud=18, formato="0.00", obligatorio=True, odoo=JUSTECH_HELLENIA_REF["withholding_lines"]),
        col(6, "F", "Número de Referencia", "string", longitud=30, obligatorio=True, faltante="justech_do_state_reference_number"),
        col(7, "G", "Tipo de Referencia", "catalog", longitud=2, obligatorio=True, catalogo="tipo_referencia", faltante="justech_do_state_reference_type"),
        col(8, "H", "Banco", "string", longitud=50, obligatorio=False, faltante="justech_do_state_withholding_bank"),
    ]
    return base_mapping(
        "623",
        "Formato de Envío de Retenciones del Estado",
        zip_name,
        "Formato 623.xls",
        "Formato 623",
        12,
        13,
        cols,
        macros=False,
        catalogos={
            "tipo_referencia": "Catálogo DGII en plantilla (factura, orden de pago, etc.) — extraer de instructivo"
        },
        validaciones=[
            "Encabezado: RNC declarante, Período, Fecha de Cierre.",
            "Totales: Cantidad Registros, Monto Total en Retenciones, Total Errores.",
            "Versión plantilla: 1.5.1.",
        ],
        totales=[
            {"campo": "Cantidad Registros", "celda": "C7"},
            {"campo": "Monto Total en Retenciones", "celda": "C8"},
            {"campo": "Total Errores", "celda": "G7"},
        ],
        reglas_negocio=[
            "Retenciones aplicadas por entidades gubernamentales al contribuyente.",
            "Relacionar con retención GOB del catálogo hellenia.withholding.catalog (código RET-GOB-5 en TEST).",
            "Requiere módulo de pagos/recibos de retención del Estado.",
        ],
        notas_dgii=[
            "Formato específico para retenciones del Estado Dominicano.",
            "No confundir con Norma 2-05 (retenciones que el contribuyente practica a terceros).",
        ],
        campos_faltantes=[
            "justech_do_state_entity_rnc",
            "justech_do_state_withholding_date",
            "justech_do_state_reference_number",
            "justech_do_state_reference_type",
            "justech_do_state_withholding_bank",
        ],
        estado_exportador="requiere_investigacion_contable",
    )


def mapping_itbis() -> dict:
    zip_name = "FormatoExcelEnvioDatosITBIS.zip"
    cols_local = [
        col(1, "A", "Cédula/ RNC", "identifier", longitud=11, obligatorio=True, odoo=ODOO_STANDARD["partner_vat"]),
        col(2, "B", "Nombre/Razón Social", "string", longitud=80, obligatorio=True, odoo=ODOO_STANDARD["partner_name"]),
        col(3, "C", "Bien/Servicio", "string", longitud=100, obligatorio=True, odoo_notas="Descripción de producto/línea"),
        col(4, "D", "Número Factura", "string", longitud=20, obligatorio=True, odoo=ODOO_STANDARD["move_name"], odoo_notas="NCF o número de factura proveedor"),
        col(5, "E", "Fecha Factura (aaaammdd)", "date", longitud=8, formato="YYYYMMDD", obligatorio=True, odoo=ODOO_STANDARD["invoice_date"]),
        col(6, "F", "Total Factura (Sin ITBIS)", "decimal", longitud=18, formato="0.00", obligatorio=True, odoo=ODOO_STANDARD["amount_untaxed"]),
        col(7, "G", "ITBIS Pagado", "decimal", longitud=18, formato="0.00", obligatorio=True, odoo=ODOO_STANDARD["amount_tax"]),
    ]
    cols_import = [
        col(1, "A", "Colecturia", "string", obligatorio=True, faltante="justech_do_customs_office"),
        col(2, "B", "Fecha Declaración (aaaammdd)", "date", longitud=8, formato="YYYYMMDD", obligatorio=True, faltante="justech_do_import_declaration_date"),
        col(3, "C", "No. Recibo", "string", obligatorio=True, faltante="justech_do_import_receipt_number"),
        col(4, "D", "Planilla", "string", obligatorio=True, faltante="justech_do_import_form_number"),
        col(5, "E", "Liquidación", "string", obligatorio=True, faltante="justech_do_import_liquidation_number"),
        col(6, "F", "Monto CIF RD$", "decimal", obligatorio=True, faltante="justech_do_import_cif_amount"),
        col(7, "G", "Monto FOB RD$", "decimal", obligatorio=True, faltante="justech_do_import_fob_amount"),
        col(8, "H", "Monto ITBIS RD$", "decimal", obligatorio=True, faltante="justech_do_import_itbis_amount"),
    ]
    m = base_mapping(
        "ITBIS",
        "Formato en Excel para Envío de Datos de ITBIS (Adelantos)",
        zip_name,
        "Formato _AdelantosItbis_v1.0.xls",
        "LOCAL",
        6,
        7,
        cols_local,
        hojas_auxiliares=["IMPORTACION"],
        macros=False,
        validaciones=[
            "Dos hojas: LOCAL (compras locales) e IMPORTACION (DGA/aduanas).",
            "Período en encabezado formato AñoMes.",
            "Versión LOCAL: 1.0; IMPORTACION: 1.0.",
        ],
        reglas_negocio=[
            "LOCAL: facturas de compra con ITBIS pagado en el período (adelantos).",
            "IMPORTACION: declaraciones aduaneras — típicamente fuera de Odoo estándar.",
            "No es el mismo archivo que declaración ITBIS resumen (formulario 606/IT1).",
        ],
        notas_dgii=[
            "Instructivo y manual incluidos en ZIPs separados del repositorio.",
            "Encabezado empresa/RNC en filas 1-2 de cada hoja.",
        ],
        campos_faltantes=[
            "justech_do_ncf (para NCF en compras locales)",
            "justech_do_customs_office",
            "justech_do_import_declaration_date",
            "justech_do_import_receipt_number",
            "justech_do_import_form_number",
            "justech_do_import_liquidation_number",
            "justech_do_import_cif_amount",
            "justech_do_import_fob_amount",
            "justech_do_import_itbis_amount",
        ],
        estado_exportador="requiere_campos_faltantes",
    )
    m["hojas"] = {
        "LOCAL": {"fila_encabezado": 6, "fila_inicio_datos": 7, "columnas": cols_local},
        "IMPORTACION": {"fila_encabezado": 6, "fila_inicio_datos": 7, "columnas": cols_import},
    }
    return m


def mapping_norma_205() -> dict:
    zip_name = "FormatoExcelNORMA2-05RetencionesTerceros.zip"
    cols = [
        col(1, "A", "Cédula/ RNC", "identifier", longitud=11, obligatorio=True, odoo=ODOO_STANDARD["partner_vat"]),
        col(2, "B", "Tipo Identificación", "catalog", longitud=1, obligatorio=True, catalogo="tipo_identificacion", faltante="justech_do_partner_id_type"),
        col(3, "C", "Número Factura", "string", longitud=20, obligatorio=True, odoo=ODOO_STANDARD["move_name"]),
        col(4, "D", "Fecha Factura (aaaammdd)", "date", longitud=8, formato="YYYYMMDD", obligatorio=True, odoo=ODOO_STANDARD["invoice_date"]),
        col(5, "E", "Total Factura", "decimal", longitud=18, formato="0.00", obligatorio=True, odoo=ODOO_STANDARD["amount_total"]),
        col(6, "F", "Total ITBIS", "decimal", longitud=18, formato="0.00", obligatorio=True, odoo=ODOO_STANDARD["amount_tax"]),
        col(7, "G", "ITBIS Retenido", "decimal", longitud=18, formato="0.00", obligatorio=True, odoo=JUSTECH_HELLENIA_REF["withholding_lines"]),
        col(8, "H", "Identificacion Retención", "catalog", longitud=2, obligatorio=True, catalogo="identificacion_retencion", odoo=JUSTECH_HELLENIA_REF["withholding_catalog"], odoo_notas="Mapear código catálogo retención ITBIS"),
    ]
    return base_mapping(
        "NORM-2-05",
        "Formato en Excel NORMA 2-05 (Retenciones a Terceros)",
        zip_name,
        "Formato _Norma205_v1.0.xls",
        "Norma 2-05",
        6,
        7,
        cols,
        macros=False,
        catalogos={
            "tipo_identificacion": [
                {"codigo": "1", "descripcion": "RNC"},
                {"codigo": "2", "descripcion": "Cédula"},
            ],
            "identificacion_retencion": "Códigos DGII de tipo retención ITBIS — mapear desde hellenia.withholding.catalog",
        },
        validaciones=[
            "Encabezado: EMPRESA y RNC en filas 1-2.",
            "Versión plantilla: 1.0.",
            "ITBIS Retenido > 0 solo en operaciones con retención practicada.",
        ],
        reglas_negocio=[
            "Reporta retenciones de ITBIS que el contribuyente practica a proveedores.",
            "Integrar con motor de retenciones Fase 18 (hellenia.withholding.catalog).",
            "Códigos RET-ITBIS-30, RET-ITBIS-100, RET-INF-ITBIS-75 en TEST deben mapearse a Identificacion Retención DGII.",
        ],
        notas_dgii=[
            "Norma 2-05 DGII — retenciones a terceros por ITBIS.",
            "Complementa formato 606 columnas de ITBIS retenido.",
        ],
        campos_faltantes=[
            "justech_do_partner_id_type",
            "justech_do_ncf",
            "dgii_withholding_code en hellenia.withholding.catalog",
        ],
        estado_exportador="requiere_campos_faltantes",
    )


MAPPINGS = {
    "dgii_606.json": mapping_606,
    "dgii_607.json": mapping_607,
    "dgii_608.json": mapping_608,
    "dgii_609.json": mapping_609,
    "dgii_623.json": mapping_623,
    "dgii_itbis.json": mapping_itbis,
    "dgii_norma_2_05.json": mapping_norma_205,
}


def main() -> None:
    MAPPINGS_DIR.mkdir(parents=True, exist_ok=True)
    for filename, builder in MAPPINGS.items():
        path = MAPPINGS_DIR / filename
        path.write_text(json.dumps(builder(), ensure_ascii=False, indent=2) + "\n")
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
