from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    fastmcp_transport: str = "http"
    fastmcp_host: str = "127.0.0.1"
    fastmcp_port: int = 8000
    mcp_dev_mode: bool = False
    log_level: str = "INFO"

    # Storage
    canvas_db_path: Path = Path("./data/canvas.db")

    # Auth — comma-separated list of "tenant_id:api_key" pairs.
    # Example: DELIVERABLE_CANVAS_TENANTS="dukestrategies:abc123,amaris:def456"
    # Empty value disables auth (dev only) and resolves all calls to tenant "default".
    deliverable_canvas_tenants: str = ""


settings = Settings()
