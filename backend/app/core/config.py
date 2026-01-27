from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and configuration"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Application settings
    APP_NAME: str = "Loris API"
    APP_VERSION: str = Field(default="0.1.0", alias="VERSION")
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")
    DEBUG: bool = Field(default=True, description="Debug mode")
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")

    # API settings
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = Field(default="dev-secret-key", description="Secret key for JWT token generation")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    JWT_SECRET_KEY: str = Field(default="jwt-secret-key", description="JWT secret key")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="JWT access token expiry")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="JWT refresh token expiry")

    # CORS settings
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3005", "http://localhost:8005"],
        description="Allowed CORS origins"
    )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    # Database settings
    DATABASE_HOST: str = Field(default="localhost", description="Database host")
    DATABASE_PORT: int = Field(default=5435, description="Database port")
    DATABASE_NAME: str = Field(default="loris", description="Database name")
    DATABASE_USER: str = Field(default="loris", description="Database user")
    DATABASE_PASSWORD: str = Field(default="password", description="Database password")
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://loris:password@localhost:5435/loris",
        description="PostgreSQL database URL"
    )
    DATABASE_ECHO: bool = Field(default=False, description="Echo SQL queries")

    # Redis settings
    REDIS_HOST: str = Field(default="localhost", description="Redis host")
    REDIS_PORT: int = Field(default=6385, description="Redis port")
    REDIS_PASSWORD: str = Field(default="", description="Redis password")
    REDIS_URL: str = Field(default="redis://localhost:6385", description="Redis cache URL")

    # AI Provider Configuration
    AI_PROVIDER: str = Field(
        default="local_ollama",
        description="AI provider: local_ollama, cloud_anthropic, cloud_bedrock, cloud_azure"
    )
    AI_MODEL: Optional[str] = Field(default=None, description="AI model override")
    AI_BASE_URL: Optional[str] = Field(default=None, description="Base URL for AI provider")
    AI_MAX_TOKENS: int = Field(default=4096, description="Maximum tokens for AI responses")
    AI_TEMPERATURE: float = Field(default=0.7, description="Temperature for AI responses")
    AI_LOG_PROMPTS: bool = Field(default=False, description="Log AI prompts (disable for privacy)")
    AI_LOG_RESPONSES: bool = Field(default=False, description="Log AI responses (disable for privacy)")

    # Ollama Settings
    OLLAMA_URL: str = Field(default="http://host.docker.internal:11434", description="Ollama server URL")
    OLLAMA_MODEL: str = Field(default="llama3.2", description="Ollama model for inference")

    # Anthropic Settings
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic Claude API key")

    # AWS Bedrock Settings
    AWS_REGION: str = Field(default="us-east-1", description="AWS region for Bedrock")
    AWS_BEDROCK_MODEL: str = Field(
        default="anthropic.claude-3-sonnet-20240229-v1:0",
        description="Bedrock model ID"
    )

    # Azure OpenAI Settings
    AZURE_OPENAI_ENDPOINT: Optional[str] = Field(default=None, description="Azure OpenAI endpoint")
    AZURE_OPENAI_KEY: Optional[str] = Field(default=None, description="Azure OpenAI API key")
    AZURE_OPENAI_DEPLOYMENT: Optional[str] = Field(default=None, description="Azure OpenAI deployment name")

    # Email settings
    SMTP_HOST: str = Field(default="smtp.gmail.com", description="SMTP host")
    SMTP_PORT: int = Field(default=587, description="SMTP port")
    SMTP_USERNAME: str = Field(default="", description="SMTP username")
    SMTP_PASSWORD: str = Field(default="", description="SMTP password")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    # Vector settings
    VECTOR_DIMENSION: int = Field(default=768, description="Vector dimension (768 for nomic-embed-text)")
    VECTOR_SIMILARITY_THRESHOLD: float = Field(default=0.85, description="Vector similarity threshold for automation")

    # File upload settings
    MAX_UPLOAD_SIZE: int = Field(default=10 * 1024 * 1024, description="Max file upload size in bytes (10MB)")
    UPLOAD_DIR: str = Field(default="uploads", description="Directory for file uploads")

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100, description="Requests per minute per IP")

    # Pagination
    DEFAULT_PAGE_SIZE: int = Field(default=20, description="Default pagination page size")
    MAX_PAGE_SIZE: int = Field(default=100, description="Maximum pagination page size")

    @property
    def database_url_async(self) -> str:
        """Convert sync database URL to async version for SQLAlchemy"""
        if self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.DATABASE_URL


# Global settings instance
settings = Settings()
