# Migración — justech_l10n_do_ncf

## 19.0.1.8.0 → 19.0.2.0.0 (Fase 3A Sprint 2)

### Impacto

Nuevas pantallas administrativas y diagnóstico read-only. Duplicados v2.0 a nivel Python.
**Sin cambios en histórico** ni en asientos publicados.

### Procedimiento (justech_ncf_lab)

```bash
odoo -u justech_l10n_do_ncf -d justech_ncf_lab --stop-after-init --no-http
odoo -d justech_ncf_lab --test-enable --stop-after-init --no-http \
  --test-tags=/justech_l10n_do_ncf
```

### Rollback

Checkout módulo 19.0.1.8.0 + backup BD lab.

---

## 19.0.1.7.0 → 19.0.1.8.0 (Fase 3A Sprint 1)

### Impacto

Refactor a capa de servicios. **Comportamiento funcional idéntico** (asignación, duplicados, anulación).

### Procedimiento

```bash
# Requiere base 19.0.1.6.0+
odoo -u justech_l10n_do_base,justech_l10n_do_ncf -d justech_lab --stop-after-init
odoo -d justech_lab --test-enable --stop-after-init \
  --test-tags=post_install -i justech_l10n_do_ncf
```

### Rollback

Restaurar versión anterior de ambos módulos desde git + backup BD.

### Validación post-upgrade

- [ ] Publicar factura venta B01 → NCF auto-asignado
- [ ] Publicar factura B02 consumidor
- [ ] NC B04 referencia NCF origen
- [ ] Duplicado NCF rechazado
- [ ] Anulación NCF + consumo voided

### Histórico

No se modifican facturas publicadas, secuencias ni consumos existentes.
