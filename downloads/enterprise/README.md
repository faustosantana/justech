# Staging — tarball Enterprise desde portal Odoo

**No commitear archivos `.tar.gz` / `.zip` en Git.**

## Ubicación VPS

```
/opt/odoo-projects/hellenia/downloads/enterprise/
└── odoo-19-enterprise-sources.tar.gz   # nombre ejemplo
```

## Cómo obtener el archivo

1. Login en https://www.odoo.com (cuenta vinculada a `M260616306091776`)
2. https://www.odoo.com/page/download → Odoo 19 → Enterprise → **Sources**
3. Transferir al VPS:

```bash
scp <archivo-descargado>.tar.gz root@<vps>:/opt/odoo-projects/hellenia/downloads/enterprise/
chmod 600 /opt/odoo-projects/hellenia/downloads/enterprise/*
```

## Validar sin instalar

```bash
scripts/validate-enterprise-archive.sh downloads/enterprise/<archivo>.tar.gz
```

## Extraer (tras aprobación E1)

```bash
scripts/extract-enterprise-portal.sh downloads/enterprise/<archivo>.tar.gz
```

Ver [docs/E0.6b-ENTERPRISE-PORTAL-DOWNLOAD.md](../docs/E0.6b-ENTERPRISE-PORTAL-DOWNLOAD.md).
