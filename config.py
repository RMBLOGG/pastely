import os
from dotenv import load_dotenv

# Muat environment variables dari file .env
load_dotenv()

class Config:
    # Flask secret key untuk session
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-ganti-di-production")

    # Konfigurasi Supabase
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

    # Nama aplikasi
    APP_NAME = "Pastely"
