"""Prompt package for Lottery IA."""

from app.lottery.ai.prompts.lottery_assistant_system_v1 import (
    PROMPT_NAME,
    activate_prompt_version,
    get_active_prompt,
    get_system_prompt_text,
    list_prompt_versions,
)

__all__ = [
    "PROMPT_NAME",
    "activate_prompt_version",
    "get_active_prompt",
    "get_system_prompt_text",
    "list_prompt_versions",
]
