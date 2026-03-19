import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017").strip()
DB_NAME = os.getenv("DB_NAME", "life_quest").strip()
DEEPSEEK_API_KEY = (os.getenv("DEEPSEEK_API_KEY", os.getenv("GENAI_API_KEY", "")) or "").strip()
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", os.getenv("GENAI_MODEL", "deepseek-chat")).strip()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-in-production").strip()
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256").strip()
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440").strip())