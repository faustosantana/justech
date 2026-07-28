# ROLLBACK — Analyst 2.0

## Punto seguro

- Commit base certificado: `65da5c7`
- Tag: `lottery-analyst-continuity-beta-2026.1.1`

## Revertir código

```bash
git checkout lottery-analyst-continuity-beta-2026.1.1
# o
git revert <analyst-2.0-commit>
```

## Revertir imagen DEV

```bash
docker tag jaios-app-backend:lottery-ia-ux-v2.4.5.5-cont jaios-app-backend:rollback-target
# redeploy contenedor DEV a la imagen continuity
```

## Qué NO hace falta revertir

- Banco cert200 / semilla / evaluador (no se modifican)
- Motor matemático / Prompt Maestro / Huawei credentials (no se tocaron)

## Señales de rollback

- Cert200 < 200 PASS
- Manual30 < 30 PASS
- Agent50 < 50 PASS
- Pérdida de sujetos compuestos en follow-ups
- Fallback genérico injustificado dominante
