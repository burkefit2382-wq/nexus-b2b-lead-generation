"""
NEXUS Configuration Management
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True
    API_WORKERS: int = 1

    # Database Settings
    DATABASE_URL: str = "sqlite:///nexus.db"
    DATABASE_ECHO: bool = False

    # AI/LLM Settings
    LLM_MODEL_PATH: str = "D:/models/Llama-3.2-1B-Instruct-Q4_K_M.gguf"
    LLM_CONTEXT_SIZE: int = 4096
    LLM_THREADS: int = 3
    LLM_TEMPERATURE: float = 0.7

    # Scraper Settings
    PLAYWRIGHT_HEADLESS: bool = True
    PLAYWRIGHT_TIMEOUT: int = 30000
    TOR_ENABLED: bool = False
    TOR_PORT: int = 9050

    # OSINT Settings
    WHOIS_TIMEOUT: int = 10
    DNS_TIMEOUT: int = 5
    EMAIL_VERIFICATION_API: Optional[str] = None

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/nexus.log"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()