# Fase 18.8 — Certificación final ciclo retenciones

**Ambiente:** `hellenia_test` @ `test.hellenia.cloud`  
**Módulo:** `hellenia_account` **19.0.1.0.12**  
**Fecha:** 2026-07-01 UTC  
**Resultado:** **TEST PASS — 26/26**

## Resumen ejecutivo

| Pregunta | Respuesta |
|----------|-----------|
| TEST PASS/FAIL | **PASS** |
| Causa total retenido RD$0 | Modelo transitorio/persistente homónimo + sin fallback post-create + pagos sin wizard |
| Causa 623 vacío | No leía líneas persistentes; solo tax lines en factura |
| Modelo persistente | `hellenia.payment.withholding.line` |
| Listo para pedir aprobación | **Sí** (requiere aprobación explícita) |

## Ciclo cerrado certificado

```
Wizard → Pago → Líneas persistentes → Asiento → Conciliación → Factura → 606/607/623 → Recibo PDF
```

## Pruebas (26)

Todas PASS incluyendo: sin retención, Gobierno 5%, ITBIS 100%, dual, parcial, multi-factura, reapertura pago/factura, 606, 607, 623, GL, conciliación, recibo PDF, vistas.

## Comando revalidación

```bash
bash scripts/run-odoo-shell-env.sh test phase18-8-retention-final-certification.py PHASE188 evidence/phase18-8-retention-final-certification.json
```

## Evidencia

`evidence/phase18-8-retention-final-certification.json`
