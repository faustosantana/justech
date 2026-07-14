# CAUSA RAÍZ Y PREVIEW — Preservar configuración fiscal histórica

Fecha: 2026-07-14
Go-Live cutoff: 2026-07-14
Entorno preview: PRODUCCIÓN (solo lectura)
Hotfix probado: DEV `justech_dev` (rollback en savepoints)

## Causa raíz

El UI/estado principal del contacto usaba `justech_do_rnc_status=pending` (“Pendiente de validar”)
como señal única, sin distinguir clientes históricos con NCF/facturas correctas.

Además:
- `justech_do_default_document_type_id` quedó vacío tras el go-live (0/532 con default).
- La validación con padrón es manual y no confirma históricos.
- El resolver de factura caía en RNC→B01 / sin RNC→B02, ignorando histórico.

Código afectado (hotfix):
- `justech_l10n_do_base`: `res.partner` estados fiscales + reconstrucción histórica
- `justech_l10n_do_ncf`: resolver de tipo, onchange partner, reglas pre-post

## Preview PROD (read-only)

- Clientes (customer_rank>0, comerciales): **532**
- Históricos (factura/NCF o SO o pago): **182**
- Nuevos (sin evidencia operativa): **350**
- Históricos consistentes (auto-confirmables): **116**
- Históricos inconsistentes (tipos mixtos): **5**
- Buckets: `{"historical_consistent": 115, "historical_inconsistent": 5, "historical_consistent_per_company": 1, "new_pending": 350, "historical_no_invoice_ncf": 61}`

### Capital Dbg S.R.L. (RNC 130279896)

[
  {
    "id": 1088,
    "name": "Capital Dbg S.R.L.",
    "vat": "130279896",
    "payer": "taxpayer",
    "rnc_status": "pending",
    "default_doc": "",
    "customer_rank": 100,
    "is_company": true,
    "country": "DO",
    "create_date": "2026-03-05",
    "is_historical": true,
    "invoice_count": 58,
    "bucket": "historical_consistent",
    "proposed_prefixes": [
      "B01"
    ],
    "companies": [
      {
        "company_id": 1,
        "company": "JUSTECH S.R.L.",
        "proposed_prefix": "B01",
        "count_top": 50,
        "count_total": 50,
        "ratio": 1.0,
        "types": {
          "B01": 50
        },
        "status": "consistent",
        "last_invoice": "FC/2026/00374",
        "last_ncf": "B0100001615",
        "last_date": "2026-07-13"
      },
      {
        "company_id": 2,
        "company": "PlugSafe SRL",
        "proposed_prefix": "B01",
        "count_top": 5,
        "count_total": 5,
        "ratio": 1.0,
        "types": {
          "B01": 5
        },
        "status": "consistent",
        "last_invoice": "FC/2026/00006",
        "last_ncf": "B0100000060",
        "last_date": "2026-07-07"
      },
      {
        "company_id": 3,
        "company": "Just Office SRL",
        "proposed_prefix": "B01",
        "count_top": 3,
        "count_total": 3,
        "ratio": 1.0,
        "types": {
          "B01": 3
        },
        "status": "consistent",
        "last_invoice": "INV/2026/00152",
        "last_ncf": "B0100000210",
        "last_date": "2026-03-18"
      }
    ]
  }
]

Propuesta: **B01** / estado **Confirmado por histórico**.

## DEV validation

OK=True
counts={"customers": 532, "historical_signal": 181, "new": 351, "states_after_confirm_sim": {"pending_new": 351, "confirmed_history": 116, "needs_review": 65}, "golive_cutoff": "2026-07-14"}
integrity={"posted_delta": 0, "payments_delta": 0, "ncf_ranges_unchanged": true, "test_partners_persisted": 0}
casos clave:
- capital_confirm: {'state': 'confirmed_history', 'prefix': 'B01', 'default': 'B01', 'source': 'Confirmado por historial de facturación'}
- case1 B01: {'partner': 'AB INDUSTRIAL SUPPLY CORPORATION SRL', 'state': 'confirmed_history', 'doc': 'B01'}
- case2 B02: {'partner': 'ABIGAIL ROMERO', 'state': 'confirmed_history', 'doc': 'B02'}
- case3 B14/B15: {'partner': 'HENRIQUEZ LOGISTICS CENTER SRL', 'state': 'confirmed_history', 'doc': 'B14'} / {'partner': 'Ayuntamiento Municipal Pedro Santana', 'state': 'confirmed_history', 'doc': 'B15'}
- case4/5 nuevo: {'state': 'pending_new', 'pending': True} / True
- case6 mixed: {'partner': 'DALGANSA SRL', 'state': 'needs_review', 'default_unchanged_or_empty': True}
- case7 partner change: {'r1': 'B01', 'r2': 'B01'}

Post-fix multiempresa Capital (DEV): JUSTECH/PlugSafe/Just Office → B01; Omni sin histórico → null.

## Regla propuesta

1. Histórico consistente ≥80% mismo prefijo (excl. NC/anulación) → `confirmed_history` + default Bxx.
2. Mixto dentro de empresa → `needs_review` (sin reclasificar B01↔B14/B15/B02).
3. Nuevo → `pending_new`; bloquear publicación hasta validar/asignar.
4. Resolución factura: default persistido → histórico por empresa → padrón → regla inequívoca.
5. No tocar facturas/NCF/pagos/asientos históricos.

## Producción

**NO MODIFICADA** (solo lectura preview). Esperar aprobación antes de despliegue.
