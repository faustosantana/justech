# Fase 16 — Reporte importación datos reales

**Fecha:** 2026-06-30  
**Ambiente:** `hellenia_prod`  
**Backup:** `/opt/odoo-projects/hellenia/backups/hellenia-prod/2026-06-30_1811`  
**Evidencia:** `evidence/phase16-go-live-prod.json`  
**Resultado:** **FAIL** — infraestructura lista; **datos reales pendientes del cliente**

---

## 1. Resumen ejecutivo

| Tarea | Estado | Detalle |
|-------|--------|---------|
| 1. Backup producción | **PASS** | `2026-06-30_1811` |
| 2. Logo final | **PASS** | Ya presente en `res.company` |
| 3. SMTP corporativo | **FAIL** | Sin credenciales en `.env` |
| 4. Usuarios reales | **FAIL** | `users.csv` no entregado |
| 5. Rangos NCF DGII | **FAIL** | `ncf_rangos_dgii.csv` no entregado |
| 6. Importar maestros | **FAIL** | CSVs clientes/proveedores/productos vacíos |
| 7. Validar flujo real | **FAIL** | Bloqueado sin NCF y maestros reales |
| 8. Limpiar datos prueba | **PASS PARCIAL** | Usuarios demo desactivados; facturas smoke pendientes |

---

## 2. Acciones ejecutadas

### Completadas

- Backup PostgreSQL + filestore + custom antes de cualquier cambio
- Verificación logo Hellenia (RNC `133621282`, email `info@helleniadr.com`)
- Desactivación usuarios demo Fase 14/15:
  - `usuario.contabilidad.demo15`
  - `usuario.inventario.demo15`
  - `usuario.normal.demo14`
  - `usuario.compras.demo15`
  - `usuario.ventas.demo15`
- Creación infraestructura importación: `data/hellenia/import/`
- Script automatizado: `scripts/phase16-go-live-prod.py` + `run-phase16-prod.sh`

### Usuarios activos post-Fase 16

| Login | Rol |
|-------|-----|
| `admin` | Emergencia |
| `it@justech.do` | Administrador TI Justech |

### Pendiente limpieza (requiere NCF B04 o contador)

| Elemento | Estado |
|----------|--------|
| Facturas smoke `INV/2026/00001–00003` | Publicadas con NCF B02 test (9900) — reversión requiere rango B04 |
| Partners `SMOKE P13.4 CF` (×3) | Referenciados en asientos |
| Productos `SMOKE-P134-DELETE` | Presentes |
| Rango NCF `SMOKE P13.4 B02` | Activo (secuencias 9900+) — reemplazar con rango DGII real |

---

## 3. Datos NO cargados (pendiente cliente)

| Archivo requerido | Ubicación | Responsable |
|-------------------|-----------|-------------|
| `users.csv` | `data/hellenia/import/` | Hellenia RRHH |
| `ncf_rangos_dgii.csv` | `data/hellenia/import/` | Hellenia + contador |
| `clientes.csv` | `data/hellenia/import/` | Hellenia comercial |
| `proveedores.csv` | `data/hellenia/import/` | Hellenia compras |
| `productos.csv` | `data/hellenia/import/` | Hellenia catálogo |
| `existencias.csv` | `data/hellenia/import/` | Hellenia inventario (opcional) |
| SMTP en `.env` | `config/production/.env` | Hellenia TI |

Plantillas en `data/hellenia/templates/`.

---

## 4. Rangos NCF requeridos

| Prefijo | Uso | Estado |
|---------|-----|--------|
| B01 | Factura crédito fiscal | **Pendiente** |
| B02 | Factura consumo | Solo rango smoke (invalidar) |
| B03 | Nota débito | **Pendiente** |
| B04 | Nota crédito | **Pendiente** |
| B11 | Comprobante compras | **Pendiente** |
| B13 | Gastos menores | **Pendiente** |

---

## 5. Procedimiento para completar Go-Live

```bash
# 1. Colocar CSVs reales en VPS:
#    /opt/odoo-projects/hellenia/data/hellenia/import/

# 2. Añadir SMTP a config/production/.env:
#    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM

# 3. Ejecutar (hace backup automático):
bash scripts/run-phase16-prod.sh
```

---

## 6. Estado datos actuales PROD

| Métrica | Valor |
|---------|-------|
| Clientes | 3 (smoke) |
| Proveedores | 0 |
| Productos | 8 (incl. smoke/sistema) |
| Usuarios operativos Hellenia | 0 |
| Rangos NCF DGII reales | 0 |

---

## 7. Conclusión

**FAIL** — El sistema técnico está operativo (HTTPS, menús, módulos fiscales, logo) pero **no está listo para usuarios reales** hasta que Hellenia entregue los archivos CSV y credenciales SMTP listados arriba.
