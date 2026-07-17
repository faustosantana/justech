# 07 — Contabilidad y reconciliación fiscal

## GL

| Métrica | Valor |
|---|---|
| AML count | 9042 |
| Débito | 93,180,628.15 |
| Crédito | 93,180,628.15 |
| Diff | **0.00** |

## Documentos

Posted invoices/refunds por compañía presentes (JUSTECH dominante).  
Drafts no modificados en auditoría.

## Inconsistencias observadas (solo lectura)

| Caso | Observado | Impacto |
|---|---|---|
| Posted sin `justech_do_document_type_id` | 1539 | Alto para motor Justech; LATAM type sí presente |
| NCF en LATAM vs Justech | 1540 vs 1 | Fuente dual |
| Prefijo ≠ tipo | 20 | Riesgo DGII / compliance |
| NCF en no-posted (`justech_do_ncf`) | no material | OK relativo |

## Retenciones / ITBIS

Módulo payments_withholding instalado; no se ejecutó asiento nuevo.  
Reconciliación detallada asiento↔606/623 queda como **paquete P1** con SAVEPOINT.

## Veredicto

Contabilidad **balanceada**. Fiscalidad documental **parcialmente alineada** con motor Justech (depende de LATAM).
