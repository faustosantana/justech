# Community — Odoo oficial (imagen Docker)

**No colocar código fuente Community en esta carpeta.**

## Origen

Los módulos Community se obtienen de la imagen Docker oficial pinneada:

```
odoo:19.0-20260619
```

## Path dentro del contenedor

```
/usr/lib/python3/dist-packages/odoo/addons
```

## En `addons_path`

Community es la **segunda** ruta (después de Enterprise, antes de Custom):

```ini
addons_path = /mnt/enterprise,/usr/lib/python3/dist-packages/odoo/addons,/mnt/custom
```

## Reglas

- ❌ No clonar `odoo/odoo` aquí salvo necesidad excepcional de auditoría
- ❌ No modificar archivos Community
- ❌ No mezclar módulos custom en esta capa
- ✅ Actualizar versión solo cambiando tag Docker en `docker-compose.yml`

## Referencia

- [Docker Hub — odoo](https://hub.docker.com/_/odoo)
- [ARCHITECTURE.md](../docs/ARCHITECTURE.md)
