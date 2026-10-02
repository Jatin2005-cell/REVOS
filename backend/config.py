import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "RevOS"
    DEBUG: bool = True

    # Database — SQLite for local dev/hackathon fallback, Supabase Postgres URI for prod
    DATABASE_URL: str = "sqlite:///./revos.db"

    # LLM — Gemini
    GEMINI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    LLM_MODEL: str = "gemini-3.5-flash-lite"
    LLM_TEMPERATURE: float = 0.3

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./chroma_store"

    # ML model paths
    MODEL_DIR: str = "./ml_models"

    # Data paths
    DATA_DIR: str = "./data"


settings = Settings()

BASE_DIR = Path(__file__).resolve().parent
os.makedirs(settings.MODEL_DIR, exist_ok=True)
os.makedirs(settings.DATA_DIR, exist_ok=True)
os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
