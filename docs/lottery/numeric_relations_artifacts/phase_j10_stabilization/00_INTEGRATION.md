# J-10S.0 — Integración selectiva de J-10P

**Base:** `3ccfff3` (J-10.5 GO CONDICIONADO)  
**Rama:** `feature/nr-j10-final-stabilization`

## Cherry-picks aplicados (en orden)

| SHA origen | Tema |
|------------|------|
| `7616894` | J-10P.0 auditoría / plan |
| `4727906` | J-10P.1 SignalCard + orden visual + empty states |
| `8d6b96e` | J-10P.2 cinco gráficas + campos aditivos backend |
| `5b38fcb` | J-10P.4 tests / a11y |
| `37c0396` | J-10P.5 informe |
| `eb5e785` | SHAs del delivery |

## Excluido de cherry-pick automático

`4a2e03a` — modifica `historial-numero/page.tsx`. Se porta manualmente en J-10S.4
(solo cableado de SignalCard, gráficas primarias y WhyStrengthenedPanel sin
reemplazar la página validada).

## Reglas respetadas

- Sin cambios a fórmulas / Tabla 1–2 matemáticas / metodología / histórico / `/analyze` v1.
- Sin despliegue a Producción.
