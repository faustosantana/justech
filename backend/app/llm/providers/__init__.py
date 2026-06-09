from app.llm.providers.claude_provider import ClaudeProvider
from app.llm.providers.deepseek_huawei_provider import DeepSeekHuaweiProvider
from app.llm.providers.hermes_local_provider import HermesLocalProvider
from app.llm.providers.openai_provider import OpenAIProvider

PROVIDER_REGISTRY = {
    "openai": OpenAIProvider,
    "claude": ClaudeProvider,
    "deepseek_huawei": DeepSeekHuaweiProvider,
    "hermes_local": HermesLocalProvider,
}
