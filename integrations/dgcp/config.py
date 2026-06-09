from pydantic import BaseModel, Field


class DGCPConfig(BaseModel):
    base_url: str = Field(default="https://datosabiertos.dgcp.gob.do/api-dgcp/v1")
    api_key: str = ""
    timeout_seconds: float = 30.0
    rate_limit_per_minute: int = 55
