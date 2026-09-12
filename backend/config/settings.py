# backend/config/settings.py

"""
Application Settings - Environment Configuration
Uses pydantic-settings for type-safe configuration management
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_env: str = "development"
    debug: bool = True
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Database
    database_url: str = "postgresql://localhost:5432/interview_assistant"
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    
    # Ollama (Local LLM)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_embedding_model: str = "nomic-embed-text"
    # Ollama defaults to a small context (2048 for most models) unless asked.
    # Grounded prompts plus a full OA question with test cases and starter code
    # in three languages get close to that ceiling, and anything past it is
    # silently dropped mid-JSON.
    ollama_num_ctx: int = 8192
    
    # Whisper (Speech-to-Text)
    whisper_model_size: str = "base"  # tiny, base, small, medium, large
    whisper_device: str = "cpu"  # cpu or cuda
    
    # AWS
    aws_region: str = "us-east-1"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    s3_bucket_name: str = "interview-assistant-artifacts"
    
    # ✅ NEW: Judge0 Configuration
    judge0_api_key: str = Field(default="", description="Judge0 RapidAPI key for hosted service")
    judge0_use_hosted: bool = Field(default=True, description="Use hosted Judge0 API vs local Docker")
    judge0_base_url: str = Field(default="http://localhost:2358", description="Base URL for local Judge0 instance")

    # ✅ NEW: Hugging Face Configuration
    hf_token: str = Field(default="", description="Hugging Face API token for Vision-LLM", env="HF_TOKEN")
        
    # Feature Flags
    enable_hallucination_check: bool = True
    enable_body_language: bool = True
    enable_code_execution: bool = True

    # ✅ Platform (Phase 9+) - auth & multi-tenancy
    storage_backend: str = Field(default="json", description="Platform storage: json | sql")
    jwt_secret: str = Field(
        default="dev-insecure-secret-change-in-production",
        description="HMAC secret for signing JWTs",
    )
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # ✅ Platform - email (Phase 13D). If unset, emails are logged not sent.
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None

    # ─────────────────────────────────────────────────────────────────────
    # Phase 14 — pluggable providers
    #
    # The same commit deploys two ways:
    #   "fast"  hosted, $0, no card: gemini + groq + render + supabase
    #   "owned" self-hosted on your own box: ollama + local whisper + judge0
    # Nothing below changes application code — only which adapter is loaded.
    # ─────────────────────────────────────────────────────────────────────

    # gemini | ollama | fake   ("fake" is deterministic; used by CI)
    llm_provider: str = "ollama"
    # groq | whisper_local
    stt_provider: str = "whisper_local"
    # judge0 | disabled   (hosted tier runs "disabled" until a Piston key lands)
    exec_provider: str = "judge0"

    # Google AI Studio — free tier, no credit card, 1M context.
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "text-embedding-004"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"

    # Groq — free Whisper STT (and optional chat), no credit card.
    groq_api_key: Optional[str] = None
    groq_stt_model: str = "whisper-large-v3-turbo"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # Shared request budget for hosted providers.
    llm_request_timeout_seconds: int = 120

    # ✅ Platform - candidate workspace base URL (for invite/assessment links)
    app_base_url: str = "http://localhost:5173"
    
    # ✅ UPDATED: Use SettingsConfigDict for Pydantic v2
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # ✅ CRITICAL: Allows extra env vars without validation errors
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()