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
    ollama_model: str = "llama3.2"
    ollama_embedding_model: str = "nomic-embed-text"
    
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