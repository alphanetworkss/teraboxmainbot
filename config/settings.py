"""
Configuration settings loader using pydantic-settings.
Loads and validates all environment variables.
"""
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Telegram Bot Configuration
    main_bot_token: str = Field(..., env='MAIN_BOT_TOKEN')
    api_id: int = Field(123, env='API_ID')
    api_hash: str = Field("xxx", env='API_HASH')
    upload_bot_tokens: str = Field(..., env='UPLOAD_BOT_TOKENS')
    log_channel_id: int = Field(..., env='LOG_CHANNEL_ID')
    force_subscribe_channel_id: str | int = Field('0', env='FORCE_SUBSCRIBE_CHANNEL_ID')  # Can be username (@channel) or ID (-100xxx)
    
    # Database Configuration
    mongodb_uri: str = Field('mongodb://localhost:27017', env='MONGODB_URI')
    mongodb_db_name: str = Field('terabox_bot', env='MONGODB_DB_NAME')
    
    # Redis Configuration
    redis_host: str = Field('localhost', env='REDIS_HOST')
    redis_port: int = Field(6379, env='REDIS_PORT')
    redis_db: int = Field(0, env='REDIS_DB')
    redis_password: str = Field('', env='REDIS_PASSWORD')
    
    # TeraBox API Configuration
    terabox_api_url: str = Field(..., env='TERABOX_API_URL')
    
    # Worker Configuration
    max_concurrent_downloads: int = Field(3, env='MAX_CONCURRENT_DOWNLOADS')
    download_dir: str = Field('./downloads', env='DOWNLOAD_DIR')
    
    # Logging
    log_level: str = Field('INFO', env='LOG_LEVEL')
    log_file_max_size: str = Field('100MB', env='LOG_FILE_MAX_SIZE')
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = False
    
    @validator('upload_bot_tokens')
    def parse_upload_tokens(cls, v):
        """Parse comma-separated bot tokens into a list."""
        if isinstance(v, str):
            return [token.strip() for token in v.split(',') if token.strip()]
        return v
    
    @property
    def upload_tokens_list(self) -> List[str]:
        """Get upload bot tokens as a list."""
        if isinstance(self.upload_bot_tokens, list):
            return self.upload_bot_tokens
        return [token.strip() for token in self.upload_bot_tokens.split(',') if token.strip()]
    
    @property
    def redis_url(self) -> str:
        """Construct Redis URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


# Global settings instance
settings = Settings()
