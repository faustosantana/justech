# Importación Go-Live — Hellenia

Coloque aquí los archivos CSV **reales** del cliente (sin líneas de comentario `#`).

| Archivo | Plantilla | Obligatorio |
|---------|-----------|-------------|
| `users.csv` | `templates/users_import_template.csv` | Sí (P0) |
| `ncf_rangos_dgii.csv` | `templates/ncf_rangos_dgii_template.csv` | Sí (P0) |
| `clientes.csv` | `templates/clientes_import_template.csv` | Sí (P1) |
| `proveedores.csv` | `templates/proveedores_import_template.csv` | Sí (P1) |
| `productos.csv` | `templates/productos_import_template.csv` | Sí (P1) |
| `existencias.csv` | columnas: `default_code,qty,location` | Opcional |

**SMTP:** configurar variables en `config/production/.env`:

```
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=noreply@helleniadr.com
SMTP_PASSWORD=<secreto>
SMTP_FROM=noreply@helleniadr.com
SMTP_SSL=false
```

No commitear contraseñas. Ejecutar: `bash scripts/run-phase16-prod.sh`
