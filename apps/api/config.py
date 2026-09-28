import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "VARUNA — AI-Powered Maritime Oil Spill Investigation & Attribution Platform"
    API_V1_STR: str = "/api/v1"
    
    # Environment & Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./varuna_investigation.db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Groq LLM API Configuration
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    
    # Storage Paths
    DATA_ROOT: Path = BASE_DIR / "data"
    MODEL_CHECKPOINTS_DIR: Path = BASE_DIR / "ml" / "checkpoints"
    
    # Attribution Weights Config
    WEIGHT_PROXIMITY: float = 0.30
    WEIGHT_TIMING: float = 0.25
    WEIGHT_TRAJECTORY: float = 0.20
    WEIGHT_AIS_GAP: float = 0.15
    WEIGHT_BEHAVIOUR_ANOMALY: float = 0.10
    
    # Security / CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "*"]

    class Config:
        case_sensitive = True

settings = Settings()
