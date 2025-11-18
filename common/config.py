from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    # REST Service URLs
    ORDER_SERVICE_URL: str
    PAYMENT_SERVICE_URL: str
    NOTIFICATION_SERVICE_URL: str

    # JSON-RPC Service URLs
    ORDER_SERVICE_JSONRPC_URL: str
    PAYMENT_SERVICE_JSONRPC_URL: str
    NOTIFICATION_SERVICE_JSONRPC_URL: str

    # gRPC Service URLs
    ORDER_SERVICE_GRPC_URL: str
    PAYMENT_SERVICE_GRPC_URL: str
    NOTIFICATION_SERVICE_GRPC_URL: str

    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_ORDER_TOPIC: str
    KAFKA_PAYMENT_TOPIC: str
    KAFKA_NOTIFICATION_TOPIC: str

    # RabbitMQ Configuration
    RABBITMQ_URL: str
    RABBITMQ_ORDER_QUEUE: str
    RABBITMQ_PAYMENT_QUEUE: str
    RABBITMQ_NOTIFICATION_QUEUE: str

    # Database Configuration
    DATABASE_URL: str

    # Redis Configuration
    REDIS_URL: str

    # Logging
    LOG_LEVEL: str

    # Service Configuration
    SERVICE_HOST: str
    SERVICE_WORKERS: int

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        case_sensitive=True,
    )


settings = Settings()
