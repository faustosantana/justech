from pydantic import BaseModel, Field


class OdooConfig(BaseModel):
    url: str = Field(description="Odoo instance URL")
    database: str = Field(description="Odoo database name")
    username: str = Field(description="Odoo API user")
    api_key: str = Field(description="Odoo API key or password")
