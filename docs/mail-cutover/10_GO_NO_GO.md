# 10 — GO / NO-GO

## Checklist

| Criterio | Estado |
|---|---|
| Producción coincide con DEV | **NO** |
| Sin diferencias críticas | **NO** (3 críticas) |
| SMTP compatible | Parcial (live dual; PlugSafe off) |
| Alias compatibles | **NO** (4 mismatches) |
| Templates compatibles | **NO** (hardcodes) |
| Riesgo controlado | No sin bump 19.0.1.2.0 + ventana |

## Decisión

**GO PARA DESPLIEGUE: NO**

### Causas exactas

1. Código P1 company-first **ausente** en filesystem Prod pese a versión `19.0.1.1.0`.  
2. **Colisión de versión**: migraciones `19.0.1.1.0` no se re-ejecutarían.  
3. Datos Prod: **4 aliases cruzados** + **hardcodes** Helpdesk.  
4. SMTP real activo → riesgo de impacto a clientes sin plan de bump + smoke.

### Condiciones para re-evaluar a GO

- Artefacto `19.0.1.2.0` (o superior) con migrate de aliases/templates.  
- Backup + restore test PASS.  
- Plan SMTP PlugSafe/Omni acordado.  
- Autorización expresa de despliegue.
