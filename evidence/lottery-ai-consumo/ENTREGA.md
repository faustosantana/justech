# Lottery IA — Consumo de tokens y costos (§14–15)

Fecha: 2026-08-03

## Entrega

- [x] **Dashboard de consumo implementado** — UI en `/lottery/admin/ai/consumo` (nav «Consumo IA»).
- [x] **Histórico de tokens implementado** — filas en `jaios.lottery_ai_usage` con tokens reales del proveedor por turno de chat; migración `065_lottery_ai_usage_lottery_key` (+ `lottery_key` para filtro licitación/lotería).
- [x] **Costos por modelo implementados** — tarifas estimadas por modelo (Huawei DeepSeek / OpenAI GPT) en `app/lottery/ai/usage.py`; agregación por proveedor/modelo en `GET /lottery/admin/ai/consumo`.

## Capacidad

| Requisito | Estado |
|-----------|--------|
| Por proveedor/modelo: solicitudes, tokens in/out/total, costo, último uso, promedio | Sí |
| Filtros: hoy / semana / mes / rango / usuario / licitación | Sí |
| Gráficos: diario, por modelo, por proveedor, costos acumulados | Sí |
| Modelo activo, % uso, costo total, promedio/licitación, promedio/conversación | Sí |
| Datos reales (no simulados) | Sí — solo lecturas de `lottery_ai_usage` |
| Tokens reales del proveedor | Sí — `complete_with_lottery_provider` / reasoning layer → `record_ai_usage` |

## Notas

- Costos son **estimados** (observabilidad), no facturación del proveedor.
- Filas históricas previas a este cambio pueden tener tokens en 0 hasta que haya tráfico nuevo.
- Comparación Huawei (`deepseek-v4-flash`, `deepseek-v3`) vs OpenAI (`gpt-5`, `gpt-5-mini`, `gpt-4.1`, `gpt-4o`, `gpt-4o-mini`) aparece en la tabla cuando existen usos registrados con esos modelos.
