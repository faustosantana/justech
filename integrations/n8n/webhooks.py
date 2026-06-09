"""n8n webhook URL builders."""

from integrations.n8n.config import N8nConfig


def build_webhook_url(config: N8nConfig, webhook_path: str) -> str:
    return f"{config.base_url.rstrip('/')}/webhook/{webhook_path}"
