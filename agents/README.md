# Agents

Framework de agentes IA para JAIOS. Fase 1 incluye únicamente la base arquitectónica.

## Estructura

```
agents/
├── core/
│   ├── base_agent.py    # Clase abstracta
│   └── context.py       # Contexto multi-tenant
└── registry.py          # Registro central
```

## Uso (Fase 2+)

```python
from agents.core.base_agent import BaseAgent
from agents.core.context import AgentContext
from agents.registry import AgentRegistry

@AgentRegistry.register
class MyAgent(BaseAgent):
    name = "my-agent"
    description = "Example agent"

    async def run(self, input_data, context: AgentContext):
        return {"status": "ok"}
```
