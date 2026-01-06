"""
Application Settings
應用程式設定
"""

from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class Settings:
    """應用程式設定"""
    
    # Application
    APP_NAME: str = "SBD Management System"
    APP_VERSION: str = "6.45.0"
    APP_ENVIRONMENT: str = os.getenv("ENV", "production")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Cache
    CACHE_TTL: int = 300  # 5 minutes
    ENABLE_CACHE: bool = True
    
    # API Retry
    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_DELAY_SECONDS: int = 1
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # DSG Limits
    DSG_MIN_MEMBERS: int = 2
    DSG_MAX_MEMBERS: int = 10000
    DSG_MAX_GROUPS: int = 15
    
    # IMEI Validation
    IMEI_LENGTH: int = 15
    
    # Session
    SESSION_TIMEOUT_MINUTES: int = 30


# Global settings instance
settings = Settings()
