# backend/app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict # Install pydantic-settings
from openai import OpenAI
import os

# Install pydantic-settings: pip install pydantic-settings

class Settings(BaseSettings):
    # LLM Settings
    DEEPSEEK_API_KEY: str = "" # Default to empty string
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-reasoner" # Ensure this is correct

    OPENAI_API_KEY: str = "" # For embeddings if Deepseek doesn't have one
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-ada-002" # Your chosen OpenAI embedding model

    # Common LLM settings
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS_FIRST_CALL: int = 750
    LLM_MAX_TOKENS_SUBSEQUENT_CALLS: int = 500
    MAX_TOOL_CALL_ITERATIONS: int = 3
    MAX_CONVERSATION_MESSAGES: int = 25 # Keep this consistent with chat.py

    # Database Settings
    PG_DB_NAME: str
    PG_DB_USER: str
    PG_DB_PASSWORD: str
    PG_DB_HOST: str
    PG_DB_PORT: str

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

settings = Settings()

# Centralized OpenAI/Deepseek Client Initialization
openai_client = None
if settings.DEEPSEEK_API_KEY:
    openai_client = OpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
    )
elif settings.OPENAI_API_KEY: # Fallback to OpenAI if Deepseek not used for chat
     openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
else:
    raise RuntimeError("Neither DEEPSEEK_API_KEY nor OPENAI_API_KEY environment variables are set.")

# Centralized Embedding Client Initialization
embedding_client = None
if settings.OPENAI_API_KEY:
    embedding_client = OpenAI(api_key=settings.OPENAI_API_KEY)
else:
    raise RuntimeError("OPENAI_API_KEY must be set for embeddings.")