# Configuración de Usuarios — Hellenia

**Fase:** 12  
**Estado:** **Plantillas listas — usuarios reales NO creados** (pendiente cliente)

---

## 1. Principio

| Tipo | Ubicación |
|------|-----------|
| Roles y grupos (diseño) | [ROLE_MATRIX.md](ROLE_MATRIX.md) — documentación Justech/Hellenia |
| Usuarios reales | Solo en BD `hellenia_prod` al Go-Live |
| Admin técnico | `it@justech.do` (ya existe DEV/TEST) |
| Emergencia | `admin` — deshabilitar uso rutinario post-Go-Live |

**Fase 12:** No se crearon usuarios funcionales adicionales (regla explícita sin lista del cliente).

---

## 2. Roles a implementar en Go-Live

| Rol | Grupos Odoo principales |
|-----|-------------------------|
| Gerencia General | Sale/Purchase/Stock manager (readonly contable) |
| Contabilidad | `account.group_account_manager` + Fiscal Manager |
| Caja | `account.group_account_invoice` + Fiscal User |
| Compras | `purchase.group_purchase_user` + Fiscal User |
| Ventas | `sales_team.group_sale_salesman` + Fiscal User |
| Inventario | `stock.group_stock_user` |
| Atención al cliente | `sales_team.group_sale_salesman` (sin facturación) |
| Administrador TI | `it@justech.do` — ya definido |

---

## 3. Plantilla de importación

**Archivo:** `data/hellenia/templates/users_import_template.csv`

Columnas: `login`, `name`, `email`, `role_hellenia`, `groups_odoo`, `lang`, `tz`, `notes`

### Entregable requerido del cliente

Lista con:
- Correo corporativo `@helleniadr.com` por usuario
- Nombre completo
- Rol según matriz
- Confirmación de acceso (ventas, compras, contabilidad, etc.)

---

## 4. Procedimiento Go-Live (Justech)

1. Recibir CSV completado por Hellenia
2. Crear usuarios en `hellenia_prod` con `lang=es_DO`, `tz=America/Santo_Domingo`
3. Asignar grupos según ROLE_MATRIX
4. Enviar invitación / contraseña temporal por canal seguro
5. Validar login por rol (checklist Fase 3 PRODUCTION_CHECKLIST)
6. **No** reutilizar contraseñas de DEV/TEST

---

## 5. Usuarios temporales eliminados

Script Fase 12 elimina logins `*hellenia.test*` si existen.

Usuarios actuales DEV/TEST: `admin`, `it@justech.do` únicamente.

---

## 6. Estado Fase 12

| Criterio | Estado |
|----------|--------|
| Diseño roles | **PASS** |
| Plantilla importación | **PASS** |
| Usuarios reales creados | **FAIL** — pendiente cliente |
| Admin solo emergencia | PASS CON OBS |
