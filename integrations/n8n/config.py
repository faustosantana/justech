from pydantic import BaseModel


class N8nConfig(BaseModel):
    base_url: str
    api_key: str = ""
