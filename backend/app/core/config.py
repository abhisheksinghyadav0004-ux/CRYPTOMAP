from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parents[2]
DATABASE_URL = os.getenv("CRYPTOMAP_DATABASE_URL", f"sqlite:///{BASE_DIR / 'cryptomap.db'}")
MAX_UPLOAD_BYTES = int(os.getenv("CRYPTOMAP_MAX_UPLOAD_BYTES", "2097152"))
ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("CRYPTOMAP_CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173").split(",")]
