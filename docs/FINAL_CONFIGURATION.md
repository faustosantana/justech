# Configuración Final — Hellenia

**Fecha validación:** 2026-06-30  
**Ambientes:** DEV, TEST (staging)  
**Evidencia:** `evidence/phase12-config-test.json`, `evidence/phase12-config-dev.json`

---

## 1. Empresa

| Campo | Valor | Estado |
|-------|-------|--------|
| Razón social | Hellenia, S.R.L. | ✅ |
| RNC | 133621282 | ✅ |
| Dirección | Calle Federico Geraldino No.164, Esquina David Ben Gurión | ✅ |
| Ciudad | Santo Domingo, Distrito Nacional | ✅ |
| País | República Dominicana | ✅ |
| Teléfono | +1 849-434-8694 | ✅ |
| Correo | info@helleniadr.com | ✅ |
| Website | https://hellenia.cloud | ✅ |
| Moneda | DOP | ✅ |
| Fiscal Justech | Habilitado | ✅ |

---

## 2. Regionalización

| Parámetro | Valor |
|-----------|-------|
| Idioma | `es_DO` |
| Zona horaria | `America/Santo_Domingo` |
| `web.base.url` TEST | https://test.hellenia.cloud |
| `web.base.url` DEV | https://dev.hellenia.cloud |
| `proxy_mode` | True |

---

## 3. Diarios

| Tipo | Código | Uso |
|------|--------|-----|
| Ventas | INV | Facturas cliente + NCF |
| Compras | FACTU | Facturas proveedor |
| Banco | BNK1 | Conciliación |
| Caja | CSH1 | Cobros/pagos efectivo |

---

## 4. Impuestos

| Impuesto | Estado |
|----------|--------|
| 18% ITBIS ventas | ✅ |
| ITBIS compras (16/9/8/18/exento) | ✅ `l10n_do` |
| Retenciones ISR/ITBIS | ✅ configuradas |

---

## 5. Métodos de pago

3 métodos estándar Odoo configurados (manual, transferencia, etc.).

---

## 6. Bancos

2 cuentas bancarias en partner empresa (verificar datos reales pre-Go-Live).

---

## 7. Módulos instalados

| Módulo | Rol |
|--------|-----|
| `account`, `account_accountant`, `account_reports` | Contabilidad EE |
| `spreadsheet_dashboard_account` | Tablero contable |
| `sale`, `purchase`, `stock`, `contacts` | Operación |
| `l10n_do` | Localización RD estándar |
| `justech_l10n_do_base`, `_ncf`, `_reports` | **Producto Justech** |

**No instalados (por diseño):** CRM, POS, eCommerce, MRP, Helpdesk, Project.

---

## 8. Pendientes configuración producción

| Item | Estado |
|------|--------|
| SMTP corporativo real | ❌ |
| Licencia EE `hellenia_prod` | ❌ |
| Rangos NCF DGII | ❌ |
| Usuarios funcionales | ❌ |

---

## 9. Re-ejecutar validación

```bash
./scripts/run-odoo-shell-env.sh test phase12-validate-configuration.py PHASE12_CONFIG evidence/phase12-config-test.json
```
