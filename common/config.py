"""
Configuration management using Pydantic Settings.
All environment variables and settings for the microservices.
"""

from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Application
    SERVICE_NAME: str = Field(default="service", description="Name of the microservice")
    SERVICE_PORT: int = Field(default=8000, description="Port where the service runs")
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://clinico:clinico_secret@postgres:5432/default_db",
        description="PostgreSQL database connection URL"
    )
    DB_POOL_SIZE: int = Field(default=20, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Max overflow connections")

    # Redis
    REDIS_URL: str = Field(default="redis://redis:6379", description="Redis connection URL")
    REDIS_CACHE_TTL: int = Field(default=300, description="Cache TTL in seconds")

    # RabbitMQ
    RABBITMQ_URL: str = Field(
        default="amqp://clinico:clinico_secret@rabbitmq:5672",
        description="RabbitMQ connection URL"
    )
    RABBITMQ_EXCHANGE: str = Field(default="clinico_events", description="RabbitMQ exchange name")
    RABBITMQ_QUEUE_PREFIX: str = Field(default="clinico", description="Queue name prefix")

    # JWT Authentication
    JWT_SECRET: str = Field(
        default="super_secret_key_change_in_production",
        description="JWT signing secret key"
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    JWT_EXPIRATION_MINUTES: int = Field(default=60, description="Token expiration in minutes")

    # External Services
    IDENTITY_SERVICE_URL: str = Field(default="http://identity-service:8001", description="Identity service URL")
    SCHEDULING_SERVICE_URL: str = Field(default="http://scheduling-service:8002", description="Scheduling service URL")
    MEDICAL_SERVICE_URL: str = Field(default="http://medical-record-service:8003", description="Medical record service URL")
    BILLING_SERVICE_URL: str = Field(default="http://billing-service:8004", description="Billing service URL")

    # CORS
    CORS_ORIGINS: list[str] = Field(default=["*"], description="Allowed CORS origins")

    # OpenTelemetry
    OTEL_ENABLED: bool = Field(default=True, description="Enable OpenTelemetry tracing")
    OTEL_SERVICE_NAME: Optional[str] = None
    OTEL_EXPORTER_OTLP_ENDPOINT: str = Field(default="http://jaeger:4317", description="OTLP endpoint")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Log level")
    LOG_FORMAT: str = Field(default="json", description="Log format: json, text")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()