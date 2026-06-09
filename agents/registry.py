from typing import Type

from agents.core.base_agent import BaseAgent


class AgentRegistry:
    """Central registry for agent discovery and instantiation."""

    _agents: dict[str, Type[BaseAgent]] = {}

    @classmethod
    def register(cls, agent_cls: Type[BaseAgent]) -> Type[BaseAgent]:
        cls._agents[agent_cls.name] = agent_cls
        return agent_cls

    @classmethod
    def get(cls, name: str) -> Type[BaseAgent] | None:
        return cls._agents.get(name)

    @classmethod
    def list_agents(cls) -> list[dict[str, str]]:
        return [
            {"name": a.name, "description": a.description}
            for a in cls._agents.values()
        ]
