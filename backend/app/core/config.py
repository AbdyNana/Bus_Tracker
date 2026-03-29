import os
from pathlib import Path
from dotenv import load_dotenv

# Absolute path to .env in the backend/ directory
# backend/app/core/config.py -> core -> app -> backend (.env)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / ".env"

load_dotenv(dotenv_path=env_path)

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

# System date for AI context (Bishkek, GMT+6)
SYSTEM_DATE = "27 марта 2026 года (2026-03-27)"
TIMEZONE = "Asia/Bishkek"
