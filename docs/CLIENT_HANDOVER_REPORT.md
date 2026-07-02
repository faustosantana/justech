# Client Handover Report — Hellenia ERP

**Para:** Hellenia, S.R.L.  
**De:** Justech  
**Fecha:** 2026-06-30  
**Sistema:** Odoo 19 EE — https://odoo.hellenia.cloud  
**Fase:** 16 — Pre-Go-Live

---

## 1. Estado del sistema

El ERP Hellenia está **técnicamente operativo** (infraestructura, localización dominicana, menús en español, reportes DGII, PDFs corporativos) pero **no está listo para uso operativo diario** hasta completar los entregables listados en la sección 3.

| Componente | Estado |
|------------|--------|
| Plataforma web | Operativa |
| Localización Justech (NCF, DGII) | Instalada — requiere rangos reales |
| Menús y permisos | Certificados (Fase 15) |
| Logo corporativo | Configurado |
| Datos maestros reales | **Pendiente** |
| Usuarios operativos | **Pendiente** |
| Correo electrónico (SMTP) | **Pendiente** |

---

## 2. Accesos actuales

| Usuario | Propósito | Acción requerida |
|---------|-----------|------------------|
| `it@justech.do` | Soporte técnico Justech | Mantener — no es usuario Hellenia |
| `admin` | Emergencia Odoo | Cambiar contraseña; no usar en operación |

**No existen aún usuarios `@helleniadr.com`.**

---

## 3. Entregables requeridos de Hellenia

### Prioridad inmediata (P0)

1. **Lista de usuarios** — completar plantilla `users_import_template.csv`:
   - Correo `@helleniadr.com`
   - Nombre completo
   - Rol: Gerencia, Contabilidad, Caja, Compras, Ventas, Inventario, Atención al cliente

2. **Autorizaciones NCF DGII** — completar `ncf_rangos_dgii_template.csv`:
   - B01, B02, B03, B04 (ventas)
   - B11, B13 (compras)
   - Número autorización, secuencia inicial/final, vigencia

3. **Credenciales SMTP** para `noreply@helleniadr.com` (o cuenta acordada):
   - Servidor, puerto, usuario, contraseña

### Prioridad operativa (P1)

4. **Catálogo de productos** — `productos_import_template.csv`  
5. **Base de clientes** — `clientes_import_template.csv` (con RNC/cédula)  
6. **Base de proveedores** — `proveedores_import_template.csv`  
7. **Existencias iniciales** (opcional) — `default_code,qty`  
8. **Datos bancarios** para diarios de cobro/pago  

Plantillas disponibles en el repositorio: `data/hellenia/templates/`

---

## 4. Datos de prueba residuales

Quedan en producción elementos de validación técnica que se eliminarán al cargar datos reales:

- 3 facturas de prueba (`INV/2026/00001–00003`) con NCF de secuencia 9900
- 3 clientes y productos etiquetados `SMOKE`
- 1 rango NCF de prueba B02 (secuencias 9900–9999)

**Acción:** el contador debe autorizar reversión/notas de crédito antes del Go-Live, o Justech ejecutará limpieza tras recibir rango B04 real.

---

## 5. Próximos pasos

| Paso | Responsable | Plazo sugerido |
|------|-------------|----------------|
| Entregar CSVs y SMTP | Hellenia | Antes de Go-Live |
| Importación y validación | Justech | 1 sesión tras entrega |
| UAT por rol | Hellenia + Justech | 2–3 días |
| Capacitación usuarios | Hellenia | Post-UAT |
| Apertura producción | Conjunto | Tras checklist P0 PASS |

---

## 6. Contacto soporte

- **Técnico:** it@justech.do (Justech)
- **Documentación:** `docs/GO_LIVE_FINAL_CHECKLIST.md`, `docs/ROLE_MATRIX.md`, `docs/NCF_CONFIGURATION.md`

---

## 7. Confirmación

| Pregunta | Respuesta |
|----------|-----------|
| ¿Sistema técnicamente funcional? | **Sí** |
| ¿Listo para usuarios reales hoy? | **No** |
| ¿Qué falta? | CSVs, SMTP, NCF DGII, limpieza smoke |
| ¿Backup disponible? | **Sí** — `2026-06-30_1811` |
