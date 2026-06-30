# Staging — tarball Enterprise desde portal Odoo

**No commitear archivos `.tar.gz` / `.zip` en Git.**

## Ubicación VPS

```
/opt/odoo-projects/hellenia/downloads/enterprise/
└── odoo-19.0-enterprise-sources.tar.gz   # nombre ejemplo
```

## Cómo obtener el archivo (sin SCP al VPS)

Ver **[docs/E0.6c-ENTERPRISE-DELIVERY-FLOW.md](../docs/E0.6c-ENTERPRISE-DELIVERY-FLOW.md)**.

| Flujo | Usuario | Cursor |
|-------|---------|--------|
| A | Copiar URL de descarga del portal | `download-enterprise-portal.sh 'URL'` |
| B | Adjuntar archivo al chat | `receive-enterprise-archive.sh --upload` |
| C | Descargar manualmente; entregar a Cursor | Igual que A o B |

## Validar sin instalar

```bash
scripts/e1a-portal-pipeline.sh --validate-only downloads/enterprise/<archivo>.tar.gz
```

## Extraer (tras aprobación E1a)

```bash
scripts/e1a-portal-pipeline.sh --execute downloads/enterprise/<archivo>.tar.gz
```

Ver [docs/E0.6b-ENTERPRISE-PORTAL-DOWNLOAD.md](../docs/E0.6b-ENTERPRISE-PORTAL-DOWNLOAD.md).
