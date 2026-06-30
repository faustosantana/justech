# Fase 19.3 — Validación TEST bandeja revisión DGII

## Ejecución VPS

```bash
cd /opt/odoo-projects/hellenia
git fetch --all
git checkout cursor/phase19-3-dgii-review-tray-dd85
git pull
rsync -av repository/custom/ ./custom/
rsync -av repository/scripts/ ./scripts/
bash scripts/run-phase19-3-test.sh
```

## Casos probados

1. Crear reporte 606 y cargar líneas en pantalla
2. Validar período
3. Excluir documento con motivo obligatorio
4. Actividad / chatter supervisor
5. Chatter en documento y reporte
6. Bloqueo generación Excel sin aprobación
7. Aprobación supervisor
8. Generación Excel con hash
9. Rechazo y re-inclusión (unit tests)
10. Permisos fiscal vs supervisor (unit tests)

## Evidencia

`evidence/phase19-3-review-test.json`

## Resultado

| Campo | Valor |
|-------|-------|
| TEST PASS/FAIL | _(actualizar tras VPS)_ |
