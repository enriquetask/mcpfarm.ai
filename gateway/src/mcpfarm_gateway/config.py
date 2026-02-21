"""Gateway configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "", "env_file": ".env", "extra": "ignore"}

    # Gateway
    gateway_host: str = "0.0.0.0"
    gateway_port: int = 8000
    gateway_log_level: str = "info"

    # Database
    database_url: str = (
        "postgresql+asyncpg://mcpfarm:mcpfarm_dev@postgres:5432/mcpfarm"
    )

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Auth
    api_key_secret: str = "change-me-in-production"
    admin_api_key: str = ""
    rate_limit_per_minute: int = 60

    # Observability
    gateway_log_format: str = "console"  # "console" or "json"
    enable_metrics: bool = True

    # Docker
    docker_network_internal: str = "mcpfarm_internal"
    docker_network_shared: str = "mcpfarm_shared"


settings = Settings()
