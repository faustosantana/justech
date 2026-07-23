# Lottery IA — Clasificación de configuración (A–E)

Cada ajuste del Centro de Administración de Lottery IA pertenece a una clase.
La UI solo permite editar A/B; C es informativa; D/E no se cambian desde el panel.

| Clase | Significado | Ejemplos |
|-------|-------------|----------|
| **A** | Editable y publicable desde UI | `understanding_mode`, `analysis_depth`, `max_insights`, `max_lotteries`, loterías predeterminadas, tono preferido |
| **B** | Editable con benchmark y aprobación | Prompt drafts, temperatura, max tokens, packs, tools no críticas |
| **C** | Solo visible | Health, latencias, tokens/costo, provider used, last success/error |
| **D** | Requiere código/despliegue | Nuevas tools Python, cambios de contratos, sync worker |
| **E** | Nunca editable por seguridad | Dominio estricto, bloqueo predicción/apuestas, SQL/credenciales/prompt interno, aislamiento tenant, Hermes como orquestador |

## Prohibido desde UI

- Editar Python / introducir SQL
- Cambiar credenciales en texto plano
- Crear tools arbitrarias
- Desactivar aislamiento tenant
- Revelar system prompt activo a no autorizados
- Eliminar auditoría
- Desactivar protecciones E vía plantilla de tono

## Flujo de publicación

```
Borrador → Validación → Playground → Benchmark → Revisión de impacto → Publicación → Activo
```

**Publicar** queda bloqueado si:

- Existen P0/P1 en el último benchmark
- Proveedor no saludable (ModelArts sin endpoint/credenciales)
- Prompt inválido / gates v3 no aprobados
- Tool crítica desactivada
- Configuración incompleta
- Safety gate fallido

Ver también: [LOTTERY_AI_RELEASE_GATES.md](./LOTTERY_AI_RELEASE_GATES.md)
