from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    fastmcp_transport: str = "http"
    fastmcp_host: str = "127.0.0.1"
    fastmcp_port: int = 8000
    mcp_dev_mode: bool = False
    log_level: str = "INFO"

    # OAuth (Microsoft Entra ID) — see infra-docs/ai/deliverable-canvas.md
    # OAUTH_REQUIRED_SCOPES is whitespace-delimited per OAuth 2.0 (RFC 6749).
    # `offline_access` is required for refresh-token issuance.
    oauth_enable: bool = False
    oauth_client_id: str = ""
    oauth_client_secret: str = ""
    oauth_tenant_id: str = ""
    oauth_base_url: str = ""
    oauth_required_scopes: str = "mcp.access offline_access"


settings = Settings()
