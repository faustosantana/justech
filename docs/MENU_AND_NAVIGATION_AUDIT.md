# Fase 15 — Auditoría de menús y navegación

**Fecha:** 2026-06-30  
**Ambiente auditado:** `hellenia_test`  
**Evidencia:** `evidence/phase15-menu-audit-test.json`

---

## 1. Hallazgos principales (pre-corrección)

| # | Problema | Causa |
|---|----------|-------|
| 1 | Contabilidad abría **Ajustes** | `repair_accounting_menu_tree()` (Fase 14.1) promovía `account.menu_account_config` como hijo directo de `account.menu_finance` con secuencia 1 |
| 2 | Menús **Contabilidad/Accounting** duplicados | `account_accountant.menu_accounting` reparentado al raíz + contenedores huérfanos activos |
| 3 | Localización Justech poco visible | Anidada 3 niveles bajo Configuración; sin menú Auditoría; grupos fiscales no heredados por contadores |

## 2. Árbol contable detectado (post-fix)

```
Contabilidad (account.menu_finance) → acción: Dashboard
├── Tablero                    (seq 1)
├── Clientes                   (seq 10)
├── Proveedores                (seq 20)
├── Asientos contables         (seq 30)
├── Apuntes contables          (seq 40)
├── Reportes                   (seq 50)
│   └── Reportes DGII
│       ├── 606 — Compras
│       ├── 607 — Ventas
│       ├── 608 — Anulados
│       └── Historial fiscal
├── Auditoría                  (seq 55)
│   ├── Consumo NCF
│   ├── NCF anulados
│   └── Historial fiscal
└── Configuración              (seq 90)
    ├── Ajustes
    └── Localización Dominicana
        ├── Tipos de NCF
        ├── Rangos NCF
        ├── Consumo NCF
        └── Configuración fiscal
```

## 3. Módulos validados

| Módulo | Estado |
|--------|--------|
| account, account_accountant, account_reports | installed |
| sale_management, purchase, stock, contacts | installed |
| hellenia_ui | installed |
| justech_l10n_do_base, justech_l10n_do_ncf, justech_l10n_do_reports | installed |

## 4. Menús ocultos (fuera de alcance)

CRM, POS, MRP, HR, Website, Barcode, Tests, Link Tracker, Spreadsheet Dashboards.

## 5. Apps

Restringido a `base.group_system` — solo `it@justech.do` y administradores técnicos.

## 6. Resultado auditoría post-fix

`issues: []` — **PASS**
