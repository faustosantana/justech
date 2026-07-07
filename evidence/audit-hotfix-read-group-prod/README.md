# Hotfix PROD — read_group(having=...) auditoría

**Fecha:** 2026-07-07  
**Módulo:** `justech_global_audit_log` v19.0.4.1.0  
**Entorno:** hellenia_prod (https://odoo.hellenia.cloud)

## Causa raíz

Odoo 19 eliminó el argumento `having` de `read_group()`. El panel de investigación (`justech.audit.dashboard`) llamaba:

```python
Log.read_group(..., having=[("user_id_count", ">", 20)])
```

Esto provocaba `TypeError: BaseModel.read_group() got an unexpected keyword argument 'having'` al abrir el dashboard.

## Corrección

Archivo: `custom/justech_global_audit_log/models/audit_dashboard.py`  
Método: `_compute_stats` (líneas ~72-80)

- `read_group` normal por `user_id`
- Filtrado en Python: contar solo grupos con más de 20 cambios hoy

## Backup

Ver `backup_path.txt`

## Validación

Ver `validation.json` — **PASS**

## Healthcheck

Ver `healthcheck.log`

## Reglas PROD (sin cambios)

ON: res.partner, sale.order, product.template  
OFF: account.move, account.payment, stock.*, pos.*
