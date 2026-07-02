# Hellenia Reports (`hellenia_reports`)

**Estado:** Implementado — Fase 13.6  
**Versión Odoo:** 19.0  
**Licencia:** LGPL-3

## Descripción

Formatos visuales corporativos PDF para documentos comerciales Hellenia:

- Layout `external_layout_hellenia`
- Cotización / pedido de venta
- Factura / nota de crédito (NCF destacado + QR)
- Orden de compra / RFQ
- Entrega / recepción (albarán)

## Instalación

```bash
# TEST
scripts/install-hellenia-reports.sh test
scripts/run-phase13-6-validate-reports.sh test

# PROD (tras PASS en TEST)
scripts/backup-hellenia.sh prod   # si existe
scripts/install-hellenia-reports.sh prod
scripts/run-phase13-6-validate-reports.sh prod
```

## Dependencias

- `hellenia_base`
- `sale`, `account`, `purchase`, `stock`
- `justech_l10n_do_ncf`

## Configuración

Configuración → Empresas → Documentos Hellenia:

- Colores corporativos
- Términos y condiciones
- Aviso legal
- Firma y sello
- Redes sociales
- QR en facturas

También configurar logo y RNC en la ficha de empresa.

## Autor

Justech — https://hellenia.cloud
