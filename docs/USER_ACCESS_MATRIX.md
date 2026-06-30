# Matriz de acceso de usuarios — Hellenia Odoo

**Fecha inventario:** 2026-06-30  
**Ambientes:** DEV (`hellenia_dev`), TEST (`hellenia_test`)  
**Método:** `scripts/audit-users.py` vía `odoo shell`

---

## 1. Resumen

| Ambiente | Usuarios totales | Operativos activos | Neutralizado |
|----------|------------------|--------------------|--------------|
| DEV | 4 | 1 | No |
| TEST | 4 | 1 | Sí |

**Usuarios accidentales de desarrollo:** ninguno detectado.

---

## 2. DEV — `hellenia_dev`

| Login | Nombre | Correo | Activo | Grupos principales | Notas |
|-------|--------|--------|--------|-------------------|-------|
| `admin` | Administrator | — | ✅ Sí | Accounting Admin, Sales Admin, Purchase Admin, Inventory Admin, Role Administrator | **Solo emergencia** |
| `__system__` | OdooBot | odoobot@example.com | No | System (inactivo) | Sistema Odoo |
| `portaltemplate` | Portal User Template | — | No | Portal | Plantilla |
| `public` | Public user | — | No | Public | Plantilla |

---

## 3. TEST — `hellenia_test`

| Login | Nombre | Correo | Activo | Grupos principales | Notas |
|-------|--------|--------|--------|-------------------|-------|
| `admin` | Administrator | — | ✅ Sí | Accounting Admin, Sales Admin, Purchase Admin, Inventory Admin, Role Administrator | **Solo emergencia** |
| `__system__` | OdooBot | odoobot@example.com | No | System | Sistema |
| `portaltemplate` | Portal User Template | — | No | Portal | Plantilla |
| `public` | Public user | — | No | Public | Plantilla |

Clon de DEV con `database.is_neutralized=true` (emails/crons desactivados).

---

## 4. Usuario planificado — Justech IT

| Campo | Valor |
|-------|-------|
| Login | `it@justech.do` |
| Nombre | Justech IT |
| Correo | `it@justech.do` |
| Idioma | `es_DO` |
| Timezone | `America/Santo_Domingo` |
| Estado | **Pendiente creación** |

### Grupos previstos (Odoo 19)

| Grupo negocio | XML ID |
|---------------|--------|
| Settings / Technical | `base.group_system`, `base.group_no_one` |
| Administration | `base.group_erp_manager` |
| Accounting Administrator | `account.group_account_manager` |
| Sales Administrator | `sales_team.group_sale_manager` |
| Purchase Administrator | `purchase.group_purchase_manager` |
| Inventory Administrator | `stock.group_stock_manager` |
| POS Administrator | `point_of_sale.group_pos_manager` — **omitido** (POS no instalado) |

### Creación

```bash
export JUSTECH_IT_PASSWORD='<indicada por Hellenia>'
./scripts/create-justech-it-user.sh dev
./scripts/create-justech-it-user.sh test
```

---

## 5. Matriz de roles (post-UAT — referencia)

| Rol | Usuario previsto | Ambiente | Permisos |
|-----|------------------|----------|----------|
| Recuperación emergencia | `admin` | DEV, TEST | Superusuario — uso restringido |
| Administración técnica Justech | `it@justech.do` | DEV, TEST | Settings + módulos operativos |
| Usuarios negocio Hellenia | *Por definir en UAT* | TEST primero | Según matriz aprobada por cliente |

---

## 6. Verificaciones de seguridad

| Check | Resultado |
|-------|-----------|
| Sin logins duplicados entre DEV/TEST operativos | ✅ |
| Sin usuarios `fiscal_user_*@test.com` persistentes | ✅ |
| Sin usuarios `test_fiscal_*@hellenia.test` persistentes | ✅ |
| Solo `admin` activo hasta crear `it@justech.do` | ✅ |

---

## 7. Evidencia

- `evidence/uat-user-audit-dev.json`
- `evidence/uat-user-audit-test.json`
- Regenerar: `./scripts/audit-users.sh dev|test`
