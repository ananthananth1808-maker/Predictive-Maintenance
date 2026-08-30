import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./maintenai.db")
ML_MODEL_PATH = os.getenv("ML_MODEL_PATH", str(Path(__file__).resolve().parents[2] / "ml" / "models" / "predictive_maintenance_model.pkl"))
PREPROCESSOR_PATH = os.getenv("PREPROCESSOR_PATH", str(Path(__file__).resolve().parents[2] / "ml" / "models" / "preprocessor.pkl"))
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

MODEL_THRESHOLDS = {
    "normal": 0.30,
    "warning": 0.70,
}
