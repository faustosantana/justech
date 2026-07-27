"""Prompt package for Lottery IA."""

from app.lottery.ai.prompts.lottery_assistant_system_v1 import (
    PROMPT_NAME,
    activate_prompt_version,
    get_active_prompt,
    get_motor_prompt,
    get_system_prompt_text,
    list_prompt_versions,
)
from app.lottery.ai.prompts.lottery_analyst_system_v6 import (
    ANALYST_PROMPT_NAME,
    ANALYST_PROMPT_VERSION,
    analyst_prompt_manifest,
    build_analyst_llm_messages,
    get_analyst_prompt,
    get_analyst_system_prompt_text,
)

__all__ = [
    "PROMPT_NAME",
    "ANALYST_PROMPT_NAME",
    "ANALYST_PROMPT_VERSION",
    "activate_prompt_version",
    "analyst_prompt_manifest",
    "build_analyst_llm_messages",
    "get_active_prompt",
    "get_analyst_prompt",
    "get_analyst_system_prompt_text",
    "get_motor_prompt",
    "get_system_prompt_text",
    "list_prompt_versions",
]
